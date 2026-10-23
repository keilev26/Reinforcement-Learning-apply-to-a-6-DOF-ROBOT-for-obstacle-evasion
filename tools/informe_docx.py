import argparse
import copy
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pypandoc
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
INFORME = RAIZ / "docs" / "informe"
GRANATE, PIZARRA = RGBColor(0x8A, 0x00, 0x00), RGBColor(0x2B, 0x3A, 0x55)
FUENTE = "Times New Roman"
ROMANOS = ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV"]
ANCHO_UTIL = 15.5
TITULO = ("Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo "
          "para un manipulador industrial de 6 grados de libertad")
MARCA_TOC, MARCA_L0, MARCA_L1 = "[[TOC]]", "[[LAND0]]", "[[LAND1]]"


def fuente_ttf(tam, negrita=False):
    nombre = "DejaVuSerif-Bold.ttf" if negrita else "DejaVuSerif.ttf"
    for base in ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu"):
        if (Path(base) / nombre).exists():
            return ImageFont.truetype(str(Path(base) / nombre), tam)
    return ImageFont.load_default()


def compuesta(rutas_y_pies, destino):
    imgs = [(Image.open(r).convert("RGB"), p) for r, p in rutas_y_pies]
    w = 1000
    celdas = []
    f = fuente_ttf(26)
    for im, pie in imgs:
        h = int(im.height * w / im.width)
        celda = Image.new("RGB", (w, h + 56), "white")
        celda.paste(im.resize((w, h)), (0, 0))
        d = ImageDraw.Draw(celda)
        d.text((w // 2, h + 28), pie, fill=(30, 36, 51), font=f, anchor="mm")
        celdas.append(celda)
    filas = [celdas[i:i + 2] for i in range(0, len(celdas), 2)]
    alto = sum(max(c.height for c in fila) for fila in filas) + 16 * (len(filas) - 1)
    lienzo = Image.new("RGB", (2 * w + 16, alto), "white")
    y = 0
    for fila in filas:
        for j, c in enumerate(fila):
            lienzo.paste(c, (j * (w + 16), y))
        y += max(c.height for c in fila) + 16
    lienzo.save(destino)


def preparar_tex(build):
    t = (INFORME / "informe_p1.tex").read_text()
    (build / "figuras").mkdir(parents=True, exist_ok=True)
    for pdf in (INFORME / "figuras").glob("*.pdf"):
        destino = build / "figuras" / (pdf.stem + ".png")
        if not destino.exists():
            subprocess.run(["pdftoppm", "-png", "-r", "200", "-singlefile", str(pdf), str(destino.with_suffix(""))],
                           check=True)
    t = re.sub(r"figuras/([a-z_]+)\.pdf", r"figuras/\1.png", t)
    t = t.replace("<<", "«").replace(">>", "»").replace("\\checkmark", "✓")
    t = t.replace("a\\in[-1,1]^6", "a\\in\\mathbb{R}^{6},\\ |a_i|\\le 1").replace("\\mathrm{clip}", "\\operatorname{clip}")
    while "\\begin{landscape}" in t:
        i = t.index("\\begin{landscape}")
        j = t.rfind("\\section{", 0, i)
        destino = j if 0 <= j and i - j < 900 else i
        t = t[:i] + t[i + len("\\begin{landscape}"):]
        t = t[:destino] + "\n\n" + MARCA_L0 + "\n\n" + t[destino:]
    t = t.replace("\\end{landscape}", "\n\n" + MARCA_L1 + "\n\n")

    a, b = t.index("\\begin{titlepage}"), t.index("\\end{titlepage}") + len("\\end{titlepage}")
    t = t[:a] + t[b:]
    t = t.replace("\\tableofcontents", "\n\n" + MARCA_TOC + "\n\n").replace("\\clearpage", "")

    refs, cont = {}, {"tab": 0, "fig": 0}
    pat = re.compile(r"\\begin\{(table|figure)\}.*?\\end\{\1\}", re.S)

    def entorno(m):
        bloque, tipo = m.group(0), m.group(1)
        clave = "tab" if tipo == "table" else "fig"
        cont[clave] += 1
        n = cont[clave]
        for lab in re.findall(r"\\label\{([^}]+)\}", bloque):
            refs[lab] = str(n)
        if "subfigure" in bloque:
            subs = re.findall(r"\\includegraphics\[[^\]]*\]\{([^}]+)\}\\caption\{([^}]+)\}", bloque)
            pies = [(INFORME / ruta, f"({chr(97 + i)}) {pie}") for i, (ruta, pie) in enumerate(subs)]
            destino = build / "img" / f"compuesta_{n}.png"
            destino.parent.mkdir(exist_ok=True)
            compuesta(pies, destino)
            general = re.findall(r"\\caption\{([^}]+)\}", bloque)[-1]
            return ("\\begin{figure}\n\\includegraphics[width=\\textwidth]{img/compuesta_%d.png}\n"
                    "\\caption{Figura %d. %s}\n\\end{figure}" % (n, n, general))
        idx = bloque.index("\\caption{") if tipo == "table" else bloque.rindex("\\caption{")
        etiqueta = "Tabla" if tipo == "table" else "Figura"
        return bloque[:idx] + "\\caption{%s %d. " % (etiqueta, n) + bloque[idx + len("\\caption{"):]

    t = pat.sub(entorno, t)

    refs["sec:presupuesto"] = "X"
    refs["sec:avances"] = "XI.4"

    claves = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", t)
    num = {k: i + 1 for i, k in enumerate(claves)}
    t = re.sub(r"\\cite\{([^}]+)\}",
               lambda m: "[" + ", ".join(str(num[k.strip()]) for k in m.group(1).split(",")) + "]", t)
    t = re.sub(r"\\ref\{([^}]+)\}", lambda m: refs.get(m.group(1), "?"), t)
    t = re.sub(r"\\label\{[^}]*\}", "", t)

    i0, i1 = t.index("\\begin{thebibliography}"), t.index("\\end{thebibliography}")
    cuerpo = t[i0:i1].split("\n", 1)[1].replace("\\small", "")
    items = re.split(r"\\bibitem(?:\[[^\]]*\])?\{[^}]+\}", cuerpo)[1:]
    biblio = "\n\n".join("[%d]\\quad %s" % (i + 1, it.strip()) for i, it in enumerate(items))
    t = t[:i0] + "\n\n" + biblio + "\n\n" + t[i1 + len("\\end{thebibliography}"):]
    t = re.sub(r"\\makeatletter.*?\\makeatother", "", t, flags=re.S)
    (build / "informe.tex").write_text(t)
    for carpeta in ("img",):
        for f in (INFORME / carpeta).glob("*"):
            destino = build / carpeta / f.name
            destino.parent.mkdir(exist_ok=True)
            if not destino.exists():
                destino.write_bytes(f.read_bytes())
    return build / "informe.tex"


def estilo_fuente(estilo, tam=None, negrita=None, cursiva=None, color=None):
    f = estilo.font
    f.name = FUENTE
    rpr = estilo.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for atributo in ("ascii", "hAnsi", "cs", "eastAsia"):
        rf.set(qn("w:" + atributo), FUENTE)
    for atributo in ("asciiTheme", "hAnsiTheme", "cstheme", "eastAsiaTheme"):
        if rf.get(qn("w:" + atributo)) is not None:
            del rf.attrib[qn("w:" + atributo)]
    if tam:
        f.size = Pt(tam)
    if negrita is not None:
        f.bold = negrita
    if cursiva is not None:
        f.italic = cursiva
    if color is not None:
        f.color.rgb = color


def crear_referencia(destino):
    base = pypandoc.get_pandoc_path()
    datos = subprocess.run([base, "--print-default-data-file", "reference.docx"], capture_output=True, check=True).stdout
    destino.write_bytes(datos)
    d = Document(str(destino))
    for nombre in ("Normal", "Body Text", "First Paragraph", "Compact"):
        if nombre in [s.name for s in d.styles]:
            e = d.styles[nombre]
            estilo_fuente(e, 11)
            pf = e.paragraph_format
            pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY if nombre != "Compact" else WD_ALIGN_PARAGRAPH.LEFT
            pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(6), 1.12
    for nombre, tam, color, antes, despues in (("Heading 1", 15, GRANATE, 20, 8), ("Heading 2", 12.5, PIZARRA, 14, 5),
                                               ("Heading 3", 11.5, PIZARRA, 10, 4)):
        e = d.styles[nombre]
        estilo_fuente(e, tam, True, False, color)
        e.paragraph_format.space_before, e.paragraph_format.space_after = Pt(antes), Pt(despues)
        e.paragraph_format.keep_with_next = True
        e.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for nombre in ("Image Caption", "Table Caption", "Caption"):
        if nombre in [s.name for s in d.styles]:
            e = d.styles[nombre]
            estilo_fuente(e, 9.5, False, False, RGBColor(0x1E, 0x24, 0x33))
            e.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            e.paragraph_format.space_before, e.paragraph_format.space_after = Pt(4), Pt(8)
    d.save(str(destino))


def poner_borde(celda_o_parrafo_pr, lados, tam=8, color="1E2433"):
    bordes = celda_o_parrafo_pr.find(qn("w:tcBorders"))
    if bordes is None:
        bordes = OxmlElement("w:tcBorders")
        celda_o_parrafo_pr.append(bordes)
    for lado in lados:
        e = OxmlElement("w:" + lado)
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(tam))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        bordes.append(e)


def pesos_columnas(tabla):
    n = len(tabla.columns)
    medias, maximos = [0.0] * n, [0] * n
    for fila in tabla.rows:
        for j, c in enumerate(fila.cells[:n]):
            largo = len(c.text.strip())
            medias[j] += largo / len(tabla.rows)
            maximos[j] = max(maximos[j], largo)
    w = [0.6 * medias[j] + 0.4 * min(maximos[j], 110) + 6 for j in range(n)]
    minimos = [min(2.3, 0.5 + 0.22 * maximos[j]) / ANCHO_UTIL for j in range(n)]
    suma = sum(w)
    p = [x / suma for x in w]
    for _ in range(5):
        fijos = [j for j in range(n) if p[j] < minimos[j]]
        if not fijos:
            break
        resto = 1.0 - sum(minimos[j] for j in fijos)
        libres = [j for j in range(n) if j not in fijos]
        base = sum(p[j] for j in libres)
        for j in fijos:
            p[j] = minimos[j]
        for j in libres:
            p[j] = p[j] / base * resto
    return p


def dar_formato_tabla(tabla):
    tbl = tabla._tbl
    pr = tbl.tblPr
    for tag in ("w:tblW", "w:tblLayout", "w:tblBorders", "w:tblCellMar", "w:tblLook"):
        for e in pr.findall(qn(tag)):
            pr.remove(e)
    ancho = OxmlElement("w:tblW")
    ancho.set(qn("w:w"), str(int(ANCHO_UTIL / 2.54 * 1440)))
    ancho.set(qn("w:type"), "dxa")
    pr.append(ancho)
    lay = OxmlElement("w:tblLayout")
    lay.set(qn("w:type"), "fixed")
    pr.append(lay)
    jc = pr.find(qn("w:jc"))
    if jc is None:
        jc = OxmlElement("w:jc")
        pr.append(jc)
    jc.set(qn("w:val"), "center")
    mar = OxmlElement("w:tblCellMar")
    for lado, v in (("top", 50), ("left", 80), ("bottom", 50), ("right", 80)):
        e = OxmlElement("w:" + lado)
        e.set(qn("w:w"), str(v))
        e.set(qn("w:type"), "dxa")
        mar.append(e)
    pr.append(mar)
    pesos = pesos_columnas(tabla)
    total = int(ANCHO_UTIL / 2.54 * 1440)
    cuadricula = tbl.find(qn("w:tblGrid"))
    if cuadricula is not None:
        for g, p in zip(cuadricula.findall(qn("w:gridCol")), pesos):
            g.set(qn("w:w"), str(int(total * p)))
    ultima = len(tabla.rows) - 1
    for i, fila in enumerate(tabla.rows):
        trpr = fila._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))
        if i == 0:
            trpr.append(OxmlElement("w:tblHeader"))
        for j, celda in enumerate(fila.cells):
            tcpr = celda._tc.get_or_add_tcPr()
            for e in tcpr.findall(qn("w:tcW")):
                tcpr.remove(e)
            w = OxmlElement("w:tcW")
            w.set(qn("w:w"), str(int(total * pesos[min(j, len(pesos) - 1)])))
            w.set(qn("w:type"), "dxa")
            tcpr.insert(0, w)
            lados = []
            if i == 0:
                lados += ["top", "bottom"]
            if i == ultima:
                lados += ["bottom"]
            if i not in (0, ultima):
                lados += ["bottom"]
            poner_borde(tcpr, lados, 10 if i in (0, ultima) else 2, "1E2433" if i in (0, ultima) else "C9C4BA")
            if i == 0:
                sh = OxmlElement("w:shd")
                sh.set(qn("w:val"), "clear")
                sh.set(qn("w:color"), "auto")
                sh.set(qn("w:fill"), "F1ECE4")
                tcpr.append(sh)
            for p in celda.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.0
                for r in p.runs:
                    r.font.size = Pt(9.5)
                    if i == 0:
                        r.font.bold = True


def campo(parrafo, instruccion):
    for tipo, texto in (("begin", None), (None, instruccion), ("separate", None)):
        r = parrafo.add_run()
        if tipo:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r._r.append(f)
        else:
            t = OxmlElement("w:instrText")
            t.set(qn("xml:space"), "preserve")
            t.text = texto
            r._r.append(t)


def cierre_campo(parrafo):
    r = parrafo.add_run()
    f = OxmlElement("w:fldChar")
    f.set(qn("w:fldCharType"), "end")
    r._r.append(f)


def tabulador_derecho(parrafo, cm, relleno="dot"):
    ppr = parrafo._p.get_or_add_pPr()
    tabs = OxmlElement("w:tabs")
    t = OxmlElement("w:tab")
    t.set(qn("w:val"), "right")
    t.set(qn("w:leader"), relleno)
    t.set(qn("w:pos"), str(int(cm / 2.54 * 1440)))
    tabs.append(t)
    ppr.append(tabs)


def borde_parrafo(parrafo, lado, tam=12, color="8A0000"):
    ppr = parrafo._p.get_or_add_pPr()
    b = OxmlElement("w:pBdr")
    e = OxmlElement("w:" + lado)
    e.set(qn("w:val"), "single")
    e.set(qn("w:sz"), str(tam))
    e.set(qn("w:space"), "8")
    e.set(qn("w:color"), color)
    b.append(e)
    ppr.append(b)


def construir_caratula(doc):
    cuerpo = doc.element.body
    ancla = cuerpo[0]
    creados = []

    def p(texto="", tam=12, negrita=False, color=None, espacio=6, alinea=WD_ALIGN_PARAGRAPH.CENTER):
        par = doc.add_paragraph()
        par.alignment = alinea
        par.paragraph_format.space_after = Pt(espacio)
        par.paragraph_format.space_before = Pt(0)
        if texto:
            r = par.add_run(texto)
            r.font.size, r.font.bold, r.font.name = Pt(tam), negrita, FUENTE
            if color is not None:
                r.font.color.rgb = color
        creados.append(par)
        return par

    logo = p(espacio=10)
    logo.add_run().add_picture(str(INFORME / "img" / "logo_uni.png"), height=Cm(4.2))
    p("UNIVERSIDAD NACIONAL DE INGENIERÍA", 17, True, GRANATE, 4)
    p("Facultad de Ingeniería Mecánica", 13, espacio=2)
    p("Escuela Profesional de Ingeniería Mecatrónica", 13, espacio=34)
    p("Curso: MT818 Proyecto Mecatrónico · Sección A · 10.º ciclo · 2026-2", 12, espacio=4)
    p("Evaluación: Presentación 1 (Informe técnico)", 12, espacio=30)
    arriba = p(espacio=0)
    borde_parrafo(arriba, "top")
    p(TITULO, 19, True, GRANATE, 6)
    abajo = p(espacio=30)
    borde_parrafo(abajo, "bottom")
    p("Autores", 12, True, PIZARRA, 4)
    p("Caleb Camargo Saavedra (20210011C)", 12, espacio=2)
    ln = p("Luis Leonardo Tupac Vásquez Cabrera (", 12, espacio=26)
    r = ln.add_run("[por completar: código]")
    r.font.bold, r.font.color.rgb, r.font.size, r.font.name = True, RGBColor(0xC0, 0x00, 0x00), Pt(12), FUENTE
    ln.add_run(")").font.size = Pt(12)
    p("Profesor del curso", 12, True, PIZARRA, 4)
    p("Ing. José Oliden Martínez", 12, espacio=14)
    p("Asesor especializado", 12, True, PIZARRA, 4)
    p("Sin asesor especializado", 12, espacio=34)
    cierre = p("Lima, Perú · Octubre de 2026", 12, espacio=0)
    salto = cierre.add_run()
    quiebre = OxmlElement("w:br")
    quiebre.set(qn("w:type"), "page")
    salto._r.append(quiebre)
    for par in creados:
        ancla.addprevious(par._p)


def numerar_encabezados(doc):
    a = b = c = 0
    lista = []
    for par in doc.paragraphs:
        nombre = par.style.name
        if nombre == "Heading 1":
            a, b, c = a + 1, 0, 0
            pre = ROMANOS[a] + ". "
            nivel = 1
        elif nombre == "Heading 2":
            b, c = b + 1, 0
            pre = f"{ROMANOS[a]}.{b} "
            nivel = 2
        elif nombre == "Heading 3":
            c += 1
            pre = f"{ROMANOS[a]}.{b}.{c} "
            nivel = 3
        else:
            continue
        if par.runs:
            par.runs[0].text = pre + par.runs[0].text
        lista.append((nivel, par.text))
    return lista


def paginas_de_encabezados(pdf, encabezados, desde=3):
    n = int(subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout.split("Pages:")[1].split()[0])
    textos = []
    for i in range(1, n + 1):
        salida = subprocess.run(["pdftotext", "-f", str(i), "-l", str(i), "-layout", str(pdf), "-"],
                                capture_output=True, text=True).stdout
        textos.append(re.sub(r"\s+", " ", salida))
    paginas, actual = [], desde
    for nivel, texto in encabezados:
        clave = re.sub(r"\s+", " ", texto)[:38]
        pag = actual
        for k in range(actual, n + 1):
            if clave in textos[k - 1]:
                pag = k
                break
        paginas.append(pag)
        actual = pag
    return paginas


def insertar_toc(doc, encabezados, paginas):
    marca = next(p for p in doc.paragraphs if p.text.strip() == MARCA_TOC)
    nuevos = []

    def p(texto, tam, negrita, color, antes, despues):
        par = doc.add_paragraph()
        par.paragraph_format.space_before, par.paragraph_format.space_after = Pt(antes), Pt(despues)
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = par.add_run(texto)
        r.font.size, r.font.bold, r.font.name = Pt(tam), negrita, FUENTE
        if color is not None:
            r.font.color.rgb = color
        nuevos.append(par)
        return par

    p("Índice", 15, True, GRANATE, 0, 10)
    for k, ((nivel, texto), pag) in enumerate(zip(encabezados, paginas)):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        par.paragraph_format.left_indent = Cm(0.7 * (nivel - 1))
        par.paragraph_format.space_before = Pt(5 if nivel == 1 else 0)
        par.paragraph_format.space_after = Pt(1)
        par.paragraph_format.line_spacing = 1.0
        tabulador_derecho(par, ANCHO_UTIL)
        if k == 0:
            campo(par, 'TOC \\o "1-3" \\h \\z \\u')
        r = par.add_run(f"{texto}\t{pag}")
        r.font.size = Pt(10.5 if nivel == 1 else 10)
        r.font.bold = nivel == 1
        r.font.name = FUENTE
        if k == len(encabezados) - 1:
            cierre_campo(par)
        nuevos.append(par)
    quiebre = doc.add_paragraph()
    q = OxmlElement("w:br")
    q.set(qn("w:type"), "page")
    quiebre.add_run()._r.append(q)
    nuevos.append(quiebre)
    for par in nuevos:
        marca._p.addprevious(par._p)
    marca._p.getparent().remove(marca._p)


def propiedades_seccion(doc, apaisada):
    base = doc.element.body.find(qn("w:sectPr"))
    sp = copy.deepcopy(base)
    for tag in ("w:headerReference", "w:footerReference", "w:titlePg"):
        for e in sp.findall(qn(tag)):
            sp.remove(e)
    pg = sp.find(qn("w:pgSz"))
    mar = sp.find(qn("w:pgMar"))
    if apaisada:
        pg.set(qn("w:w"), "16838")
        pg.set(qn("w:h"), "11906")
        pg.set(qn("w:orient"), "landscape")
        for k, v in (("top", 1134), ("bottom", 1134), ("left", 1134), ("right", 1134)):
            mar.set(qn("w:" + k), str(v))
    return sp


def secciones_apaisadas(doc):
    parrafos = list(doc.paragraphs)
    marcas = [p for p in parrafos if p.text.strip() in (MARCA_L0, MARCA_L1)]
    for p in marcas:
        apaisada = p.text.strip() == MARCA_L1
        for r in p.runs:
            r.text = ""
        sp = propiedades_seccion(doc, apaisada)
        p._p.get_or_add_pPr().append(sp)
        p.paragraph_format.space_after = Pt(0)
    dentro = False
    for el in doc.element.body.iterchildren():
        if el.tag != qn("w:p"):
            continue
        sp = el.find(qn("w:pPr") + "/" + qn("w:sectPr"))
        if sp is not None and sp.find(qn("w:pgSz")).get(qn("w:orient")) != "landscape":
            dentro = True
            continue
        if sp is not None:
            dentro = False
            continue
        if dentro:
            for dib in el.iter(qn("w:drawing")):
                ext = dib.find(".//" + qn("wp:extent"))
                if ext is None:
                    continue
                w, h = int(ext.get("cx")), int(ext.get("cy"))
                k = min(Cm(23.5) / w, Cm(12.6) / h)
                nw, nh = int(w * k), int(h * k)
                ext.set("cx", str(nw))
                ext.set("cy", str(nh))
                for e in dib.iter(qn("a:ext")):
                    if e.get("cx") is not None:
                        e.set("cx", str(nw))
                        e.set("cy", str(nh))


def limitar_imagenes(doc):
    tope = Cm(ANCHO_UTIL)
    cuerpo = doc.element.body
    dentro = False
    for el in cuerpo.iterchildren():
        sp = el.find(qn("w:pPr") + "/" + qn("w:sectPr")) if el.tag == qn("w:p") else None
        if sp is not None:
            dentro = sp.find(qn("w:pgSz")).get(qn("w:orient")) != "landscape" and dentro
            if sp.find(qn("w:pgSz")).get(qn("w:orient")) == "landscape":
                dentro = False
            continue
        if el.tag != qn("w:p"):
            continue
        for dib in el.iter(qn("w:drawing")):
            ext = dib.find(".//" + qn("wp:extent"))
            if ext is None:
                continue
            w, h = int(ext.get("cx")), int(ext.get("cy"))
            if w > tope:
                k = tope / w
                nw, nh = int(w * k), int(h * k)
                ext.set("cx", str(nw))
                ext.set("cy", str(nh))
                for e in dib.iter(qn("a:ext")):
                    if e.get("cx") is not None:
                        e.set("cx", str(nw))
                        e.set("cy", str(nh))


def llenar_encabezado(seccion, ancho_cm):
    cab = seccion.header
    cab.is_linked_to_previous = False
    for p in list(cab.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    p0 = cab.paragraphs[0]
    for r in list(p0.runs):
        r._r.getparent().remove(r._r)
    tabulador_derecho(p0, ancho_cm, "none")
    ppr = p0._p.get_or_add_pPr()
    borde = OxmlElement("w:pBdr")
    inf = OxmlElement("w:bottom")
    for k, v in (("val", "single"), ("sz", "4"), ("space", "4"), ("color", "8A0000")):
        inf.set(qn("w:" + k), v)
    borde.append(inf)
    ppr.insert(0, borde)
    for texto in ("Planificación de movimiento con aprendizaje por refuerzo", "\tPresentación 1 · Proyecto Mecatrónico"):
        r = p0.add_run(texto)
        r.font.size, r.font.name, r.font.color.rgb = Pt(9), FUENTE, RGBColor(0x55, 0x5B, 0x6B)
    pie = seccion.footer
    pie.is_linked_to_previous = False
    pp = pie.paragraphs[0]
    for r in list(pp.runs):
        r._r.getparent().remove(r._r)
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    campo(pp, "PAGE")
    pp.add_run("1")
    cierre_campo(pp)
    for run in pp.runs:
        run.font.size, run.font.name = Pt(9), FUENTE


def encabezado_y_pie(doc):
    for i, sec in enumerate(doc.sections):
        apaisada = sec.page_width > sec.page_height
        if i == 0:
            sec.different_first_page_header_footer = True
        llenar_encabezado(sec, 25.7 if apaisada else ANCHO_UTIL)


def ajustar(doc):
    for s in doc.sections:
        s.page_width, s.page_height = Cm(21), Cm(29.7)
        if s.orientation == 0:
            s.left_margin, s.right_margin = Cm(3.0), Cm(2.5)
            s.top_margin, s.bottom_margin = Cm(2.6), Cm(2.4)
            s.header_distance, s.footer_distance = Cm(1.2), Cm(1.1)
    for par in doc.paragraphs:
        if re.match(r"^\[\d+\]\s", par.text) and par.style.name != "Heading 1":
            par.paragraph_format.left_indent = Cm(1.0)
            par.paragraph_format.first_line_indent = Cm(-1.0)
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            par.paragraph_format.space_after = Pt(4)
            for r in par.runs:
                r.font.size = Pt(10)
        if par._p.find(".//" + qn("w:drawing")) is not None and par.style.name not in ("Heading 1",):
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            par.paragraph_format.keep_with_next = True
            par.paragraph_format.space_before = Pt(6)
            par.paragraph_format.space_after = Pt(2)
        if par.style.name == "Table Caption":
            par.paragraph_format.keep_with_next = True
    for t in doc.tables:
        dar_formato_tabla(t)


def construir(build, salida):
    build.mkdir(parents=True, exist_ok=True)
    tex = preparar_tex(build)
    ref = build / "referencia.docx"
    crear_referencia(ref)
    bruto = build / "bruto.docx"
    pypandoc.convert_file(str(tex), "docx", format="latex", outputfile=str(bruto),
                          extra_args=["--reference-doc", str(ref), "--resource-path", str(build)])
    paginas = None
    for pasada in range(2):
        doc = Document(str(bruto))
        ajustar(doc)
        encabezados = numerar_encabezados(doc)
        insertar_toc(doc, encabezados, paginas or [0] * len(encabezados))
        limitar_imagenes(doc)
        secciones_apaisadas(doc)
        construir_caratula(doc)
        encabezado_y_pie(doc)
        tmp = build / f"pasada{pasada}.docx"
        doc.save(str(tmp))
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(build), str(tmp)],
                       capture_output=True, check=True)
        paginas = paginas_de_encabezados(build / f"pasada{pasada}.pdf", encabezados)
    shutil.copyfile(tmp, salida)
    print(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", type=Path, default=Path("/data/tmp/informe_docx"))
    ap.add_argument("--salida", type=Path, default=INFORME / "informe_p1.docx")
    a = ap.parse_args()
    construir(a.build, a.salida)


if __name__ == "__main__":
    sys.exit(main())
