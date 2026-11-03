import argparse
import sys
from pathlib import Path

import numpy as np
import pybullet as p
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.robot_e6 import cargar_e6, fijar_q
from gym_env.kit import COMBINACIONES, COMBINACIONES_2, COMBINACIONES_3
from shared_scenarios import contrato

FONDO, TINTA, TENUE = (252, 252, 251), (11, 11, 11), (82, 81, 78)
GRIS_MESA, MADERA = (0.62, 0.62, 0.64, 1.0), (0.78, 0.66, 0.46, 1.0)
AZUL, NARANJA, MORADO = (0.22, 0.45, 0.80, 1.0), (0.90, 0.45, 0.15, 1.0), (0.55, 0.25, 0.70, 1.0)

PIEZAS = {
    "P01": ("P01_Cubo_75", "Cubo 75", AZUL), "P02": ("P02_Columna_75x150", "Columna 75x150", AZUL),
    "P03": ("P03_Caja_baja_125x75x50", "Caja baja 125x75x50", AZUL), "P04": ("P04_Muro_175x25x150", "Muro 175x25x150", AZUL),
    "P05": ("P05_Angulo_L_125x75x150", "Ángulo L 125x75x150", AZUL), "P06": ("P06_Escalera_175x75", "Escalera 175x75", AZUL),
    "P07": ("P07_Cruz_125x125x100", "Cruz 125x125x100", AZUL), "P08": ("P08_Viga_portal_275x75x20", "Viga portal 275x75x20", AZUL),
    "R01": ("R01_Cilindro_D60x100", "Cilindro D60x100", NARANJA), "R02": ("R02_Poste_D30x220", "Poste D30x220", NARANJA),
    "R03": ("R03_Cono_D100x120", "Cono D100x120", NARANJA), "R04": ("R04_Tronco_cono_D100_D40x100", "Tronco de cono D100/D40x100", NARANJA),
    "R05": ("R05_Esfera_D100_pedestal", "Esfera D100 con pedestal", NARANJA), "R06": ("R06_Domo_D120", "Domo D120", NARANJA),
    "T01": ("T01_Muro_alto_175x25x350", "Muro alto 175x25x350", MORADO),
    "T02": ("T02_Columna_alta_75x75x350", "Columna alta 75x75x350", MORADO),
    "T03": ("T03_Poste_alto_D30x450", "Poste alto D30x450", MORADO),
    "T04": ("T04_Tabique_largo_275x25x300", "Tabique largo 275x25x300", MORADO),
    "T05": ("T05_Cilindro_alto_D60x300", "Cilindro alto D60x300", MORADO),
    "R07": ("R07_Prisma_hexagonal_80x120", "Prisma hexagonal 80x120", NARANJA),
    "R08": ("R08_Prisma_triangular_100x100", "Prisma triangular 100x100", NARANJA),
    "R09": ("R09_Piramide_cuadrada_100x120", "Pirámide cuadrada 100x120", NARANJA),
}

def fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    ruta = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold" if negrita else "normal"))
    return ImageFont.truetype(ruta, tam)


class Mundo:
    def __init__(self, mallas: Path):
        self.mallas = mallas
        self.cl = p.connect(p.DIRECT)

    def malla(self, nombre, pos, yaw_deg=0.0, color=GRIS_MESA, escala=(1, 1, 1)):
        v = p.createVisualShape(p.GEOM_MESH, fileName=str(self.mallas / f"{nombre}.stl"), meshScale=escala,
                                rgbaColor=color, physicsClientId=self.cl)
        return p.createMultiBody(0, baseVisualShapeIndex=v, basePosition=pos,
                                 baseOrientation=p.getQuaternionFromEuler([0, 0, np.radians(yaw_deg)]),
                                 physicsClientId=self.cl)

    def caja(self, dims, centro, color):
        v = p.createVisualShape(p.GEOM_BOX, halfExtents=[d / 2 for d in dims], rgbaColor=color, physicsClientId=self.cl)
        return p.createMultiBody(0, baseVisualShapeIndex=v, basePosition=centro, physicsClientId=self.cl)

    def mesa(self):
        self.malla("MESA_01_Tablero", (0, 0, 0), color=MADERA)
        for sx in (-1, 1):
            for sy in (-1, 1):
                self.malla("MESA_02_Pata", (sx * 0.565, sy * 0.465, -0.750))
            self.malla("MESA_03_Faldon_largo", (0, sx * 0.4775, -0.105))
            self.malla("MESA_04_Faldon_corto", (sx * 0.4775, 0, -0.105))
            self.malla("MESA_05_Travesano_largo", (0, sx * 0.4775, -0.640))
            self.malla("MESA_06_Travesano_corto", (sx * 0.4775, 0, -0.640))
        self.malla("MESA_07_Repisa", (0, 0, -0.600))

    def robot(self):
        C = contrato.cargar()
        m = cargar_e6(self.cl)
        fijar_q(m, C["tarea_nominal"]["q_inicial_rad"])

    def celda(self):
        self.caja((0.30, 0.50, 0.40), (0.53, 0.0, 0.195), (0.35, 0.40, 0.50, 0.55))
        self.caja((0.20, 0.25, 0.02), (0.0, -0.30, 0.005), (0.20, 0.60, 0.30, 0.9))

    def obstaculo(self, codigo, x_mm, y_mm, yaw, z=0.0):
        nombre, _, color = PIEZAS[codigo]
        self.malla(nombre, (x_mm / 1000, y_mm / 1000, z), yaw, color)

    def vista(self, ojo, objetivo, ancho, alto, fov=40, arriba=(0, 0, 1)):
        V = p.computeViewMatrix(ojo, objetivo, arriba, physicsClientId=self.cl)
        P = p.computeProjectionMatrixFOV(fov, ancho / alto, 0.05, 6, physicsClientId=self.cl)
        w, h, rgb, *_ = p.getCameraImage(ancho, alto, V, P, renderer=p.ER_TINY_RENDERER, physicsClientId=self.cl)
        img = Image.fromarray(np.reshape(rgb, (h, w, 4))[:, :, :3].astype(np.uint8))
        M = np.array(P).reshape(4, 4).T @ np.array(V).reshape(4, 4).T

        def proyectar(punto):
            c = M @ np.array([punto[0], punto[1], punto[2], 1.0])
            return (c[0] / c[3] * 0.5 + 0.5) * ancho, (1 - (c[1] / c[3] * 0.5 + 0.5)) * alto

        return img, proyectar

    def cerrar(self):
        p.disconnect(self.cl)


def etiquetas(img, proyectar, items):
    d = ImageDraw.Draw(img)
    for texto, punto, color in items:
        x, y = proyectar(punto)
        d.text((x + 6, y - 26), texto, fill=color, font=fuente(22, True))
    return img


def marcas(img, proyectar):
    T = contrato.cargar()["tarea_nominal"]
    d = ImageDraw.Draw(img)
    for nombre, pos, color in (("RECOGER", T["p_pick"]["pos"], (42, 120, 214)), ("DEPOSITAR", T["p_place"]["pos"], (26, 140, 60))):
        x, y = proyectar(pos)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=color, width=4)
        d.text((x + 12, y - 12), nombre, fill=color, font=fuente(22, True))
    x, y = proyectar((0.53, 0, 0.40))
    d.text((x - 40, y - 28), "CNC (contrato)", fill=(53, 64, 80), font=fuente(22, True))
    x, y = proyectar((0.0, 0.0, 0.0))
    d.text((x - 36, y + 14), "robot E6", fill=TINTA, font=fuente(22, True))


def catalogo(mallas: Path, salida: Path, codigos=None, titulo="Kit de obstáculos (17 piezas, mm)", sub=None, lejos=1.0):
    codigos = codigos or [c for c in PIEZAS if not c.startswith("T")]
    columnas, ancho, alto = 6, 300, 330
    filas = -(-len(codigos) // columnas)
    hoja = Image.new("RGB", (columnas * ancho, filas * alto + 110), FONDO)
    d = ImageDraw.Draw(hoja)
    d.text((30, 20), titulo, fill=TINTA, font=fuente(44, True))
    d.text((30, 76), sub or "azul: prismáticas P01-P08 · naranja: redondas R01-R09 · se atornillan en la rejilla M6 de paso 50", fill=TENUE, font=fuente(22))
    for i, codigo in enumerate(codigos):
        nombre, texto, _ = PIEZAS[codigo]
        m = Mundo(mallas)
        m.malla("MESA_01_Tablero", (0, 0, 0), color=MADERA)
        m.obstaculo(codigo, 0, 0, 0)
        img, _ = m.vista((0.30 * lejos, -0.36 * lejos, 0.22 * lejos), (0, 0, 0.07 * lejos), ancho, alto - 70, fov=38)
        m.cerrar()
        x0, y0 = (i % columnas) * ancho, 110 + (i // columnas) * alto
        hoja.paste(img, (x0, y0))
        d.text((x0 + 10, y0 + alto - 66), codigo, fill=TINTA, font=fuente(26, True))
        d.text((x0 + 10, y0 + alto - 34), texto, fill=TENUE, font=fuente(18))
    hoja.save(salida)


def vista_mesa(mallas: Path, salida: Path):
    m = Mundo(mallas)
    m.mesa()
    m.robot()
    m.celda()
    img, proy = m.vista((1.8, -1.9, 1.25), (0.1, 0.0, -0.2), 1500, 900, fov=40)
    m.cerrar()
    marcas(img, proy)
    hoja = Image.new("RGB", (1500, 1020), FONDO)
    d = ImageDraw.Draw(hoja)
    d.text((30, 18), "Mesa de trabajo, robot y celda base", fill=TINTA, font=fuente(44, True))
    d.text((30, 74), "Tablero 1200x1000x25 con rejilla M6 paso 50 · 4 patas 70x70 · 2 faldones largos y 2 cortos · 2 travesaños + 2 cortos · repisa 1060x980x18",
           fill=TENUE, font=fuente(20))
    hoja.paste(img, (0, 120))
    hoja.save(salida)


def combinacion(mallas: Path, salida: Path, letra, titulo, piezas, amplio=False):
    anchos = (1100, 700)
    hoja = Image.new("RGB", (sum(anchos), 860), FONDO)
    d = ImageDraw.Draw(hoja)
    d.text((30, 14), f"Combinación {letra}: {titulo} ({len(piezas)} piezas)", fill=TINTA, font=fuente(40, True))
    if amplio:
        camaras = (((1.45, -1.55, 1.25), (0.05, 0.0, 0.05), (0, 0, 1)), ((0.0, 0.0, 2.3), (0.0, 0.0, 0.0), (0, 1, 0)))
    else:
        camaras = (((1.05, -1.05, 0.85), (0.20, -0.10, 0.04), (0, 0, 1)), ((0.20, -0.10, 1.35), (0.20, -0.10, 0.0), (0, 1, 0)))
    vistas = []
    for k, (ojo, objetivo, arriba) in enumerate(camaras):
        m = Mundo(mallas)
        m.mesa()
        m.robot()
        m.celda()
        rotulos = []
        for pieza in piezas:
            codigo, x, y, yaw = pieza[:4]
            z = pieza[4] if len(pieza) > 4 else 0.0
            m.obstaculo(codigo, x, y, yaw, z)
            if not amplio:
                rotulos.append((codigo, (x / 1000, y / 1000, 0.17 if codigo != "R02" else 0.24), TINTA))
        img, proy = m.vista(ojo, objetivo, anchos[k], 760, fov=42 if not amplio else 40, arriba=arriba)
        m.cerrar()
        marcas(img, proy)
        etiquetas(img, proy, rotulos)
        if amplio and k == 1:
            ImageDraw.Draw(img).line([proy((0.45 * np.cos(t), 0.45 * np.sin(t), 0.0)) for t in np.linspace(0, 2 * np.pi, 90)],
                                     fill=(204, 38, 38), width=3)
            ImageDraw.Draw(img).text((12, 12), "círculo rojo: alcance del robot (450 mm)", fill=(204, 38, 38), font=fuente(22, True))
        vistas.append(img)
    hoja.paste(vistas[0], (0, 100))
    hoja.paste(vistas[1], (anchos[0], 100))
    hoja.save(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mallas", type=Path, required=True)
    ap.add_argument("--salida", type=Path, default=RAIZ / "docs" / "semana-10" / "kit-obstaculos")
    ap.add_argument("--solo-nuevas", action="store_true")
    ap.add_argument("--solo-altas", action="store_true")
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    if not a.solo_nuevas and not a.solo_altas:
        catalogo(a.mallas, a.salida / "01_catalogo_obstaculos.png")
        vista_mesa(a.mallas, a.salida / "02_mesa_robot_celda.png")
        for letra, titulo, piezas in COMBINACIONES:
            combinacion(a.mallas, a.salida / f"03_combinacion_{letra}.png", letra, titulo, piezas)
            print(letra, flush=True)
    for letra, titulo, piezas in COMBINACIONES_2 if not a.solo_altas else []:
        combinacion(a.mallas, a.salida / f"04_combinacion_{letra}.png", letra, titulo, piezas, amplio=True)
        print(letra, flush=True)
    catalogo(a.mallas, a.salida / "05_catalogo_piezas_altas.png", ["T01", "T02", "T03", "T04", "T05"],
             "Piezas altas propuestas (a modelar, mm)", "moradas: no están en la carpeta STEP; alturas de 300 a 450 mm", lejos=1.9)
    for letra, titulo, piezas in COMBINACIONES_3:
        combinacion(a.mallas, a.salida / f"06_combinacion_{letra}.png", letra, titulo, piezas, amplio=True)
        print(letra, flush=True)


if __name__ == "__main__":
    main()
