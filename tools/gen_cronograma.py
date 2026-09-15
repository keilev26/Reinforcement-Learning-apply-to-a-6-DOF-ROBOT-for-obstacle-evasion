"""Genera el cronograma Gantt de 15 semanas a partir de la EDT y calcula la ruta critica.

Regenerar tras cada avance:  python3 tools/gen_cronograma.py
Para actualizar el avance, cambiar el estado en TAREAS (R = realizado, P = programado).

La ruta critica se calcula por el metodo CPM sobre las dependencias declaradas en PRED.
Si una dependencia esta mal, la ruta critica sale mal: revisar PRED antes de confiar en ella.
"""
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

SALIDA = "Cronograma RL Manipulador 6GDL.xlsx"
N_SEM  = 15
COL_S1 = 8                      # columna H = semana 1
COL_LINEA = COL_S1 + 4          # columna L = semana 5: la linea roja va a su izquierda

CALEB = "Caleb Camargo"
LEO   = "Leonardo Vásquez"
AMBOS = "Ambos"

# (codigo, actividad, entregable, responsable, sem_ini, sem_fin, estado, costo_soles)
TAREAS = [
    ("FASE", "FASE 1 — DISEÑO MECÁNICO (E1)", "", "", 0, 0, "", 0),
    ("1.1", "Celda base de machine tending de CNC: layout general, pedestal del robot, envolvente de seguridad", "Layout de celda", LEO, 5, 5, "P", 0),
    ("1.2", "Biblioteca de componentes CAD individuales: centro CNC, mesa, utillaje, prensa, carro, pieza, primitivos", "Biblioteca CAD", LEO, 5, 6, "P", 0),
    ("1.3", "Geometría de colisión simplificada por componente, separada de la visual", "Mallas de colisión", LEO, 6, 6, "P", 0),
    ("1.4", "Exportación a URDF/SDF con convención de anclaje para componer escenarios", "Componentes URDF/SDF", LEO, 6, 7, "P", 0),
    ("1.5", "Parámetros de Denavit-Hartenberg del manipulador de 6 GDL; cinemática directa e inversa", "Tabla DH + ecuaciones", LEO, 4, 4, "R", 0),
    ("1.6", "Envolvente de trabajo y análisis de alcanzabilidad de las poses de recogida y depósito", "Mapa de alcanzabilidad", LEO, 6, 7, "P", 0),
    ("1.7", "Análisis de singularidades de muñeca; justificación del espacio de acción Δq", "Análisis de singularidades", LEO, 7, 7, "P", 0),

    ("FASE", "FASE 2 — DISEÑO ELECTRÓNICO (E2)", "", "", 0, 0, "", 0),
    ("2.1", "Dimensionamiento de actuadores para reproducir la envolvente: 150 N·m hombro y codo, 28 N·m muñeca, π rad/s", "Cálculo de actuadores", LEO, 9, 9, "P", 0),
    ("2.2", "Selección de reductores y transmisión; relación de reducción por articulación", "Selección de reductores", LEO, 9, 9, "P", 0),
    ("2.3", "Etapa de potencia: drivers de motor, fuente de alimentación, protecciones", "Esquema de potencia", LEO, 10, 10, "P", 0),
    ("2.4", "Unidad de cómputo y microcontrolador: debe ejecutar la inferencia de la política dentro del período de control", "Selección de cómputo", LEO, 10, 10, "P", 0),
    ("2.5", "Sensado: encoders por articulación e instrumentación del vector de observación", "Selección de sensores", LEO, 11, 11, "P", 0),
    ("2.6", "Arquitectura de comunicación: bus entre articulaciones y con el controlador de celda", "Diagrama de comunicación", LEO, 11, 11, "P", 0),
    ("2.7", "Cadena de seguridad: paro de emergencia, enclavamientos, categoría de seguridad", "Esquema de seguridad", LEO, 12, 12, "P", 0),
    ("2.8", "Presupuesto de latencia del lazo: sensado + inferencia + actuación vs. período de control", "Análisis de latencia", LEO, 12, 12, "P", 0),

    ("FASE", "FASE 3 — ALGORITMO (E3)", "", "", 0, 0, "", 0),
    ("3.1", "Contrato de escenarios y definición formal de las 5 métricas (antes de codificar)", "Contrato de escenarios", AMBOS, 4, 4, "R", 0),
    ("3.2", "Entorno Gymnasium sobre PyBullet con el manipulador de 6 GDL", "Entorno Gym", CALEB, 6, 7, "P", 0),
    ("3.3", "Formulación del MDP: acción Δq acotada, observación por descriptores geométricos", "Especificación del MDP", CALEB, 7, 7, "P", 0),
    ("3.4", "Función de recompensa multiobjetivo: colisión, autocolisión, alcance de meta, suavidad", "Función de recompensa", CALEB, 8, 8, "P", 0),
    ("3.5", "Entrenamiento SAC desde cero — escenarios 1 y 2", "Política entrenada v1", CALEB, 9, 9, "P", 0),
    ("3.6", "Aleatorización de dominio (posición, escala, forma) e integración de escenarios 4-5-6", "Dominio aleatorizado", CALEB, 10, 10, "P", 0),
    ("3.7", "Entrenamiento completo: 5 semillas × escenarios núcleo", "Políticas + logs", CALEB, 10, 11, "P", 0),
    ("3.8", "Workspace ROS 2: ur_simulation_gz, manipulador de 6 GDL, ros2_control, MoveIt 2", "Workspace ROS 2", LEO, 1, 3, "R", 0),
    ("3.9", "Configuración de OMPL: RRT-Connect y RRT* con parámetros documentados", "ompl_planning.yaml", LEO, 4, 4, "R", 0),
    ("3.10", "moveit_ros_benchmarks para tiempo, longitud y tasa de éxito", "Banco de pruebas OMPL", LEO, 6, 7, "P", 0),
    ("3.11", "Módulo de distancia mínima eslabón-obstáculo, validado contra FCL", "Módulo de distancias", LEO, 7, 8, "P", 0),
    ("3.12", "Generador de escenarios: compone los 8 escenarios desde la biblioteca CAD de E1", "Generador de escenarios", LEO, 8, 8, "P", 0),
    ("3.13", "Verificación de equivalencia PyBullet ↔ Gazebo: URDF, límites, geometría y escala", "Informe de equivalencia", AMBOS, 8, 9, "P", 0),
    ("3.14", "Ejecución batch de la línea base clásica sobre escenarios núcleo", "Corridas de línea base", LEO, 10, 11, "P", 0),
    ("3.15", "Subprueba PPO bajo la misma recompensa (extensión)", "Comparativa SAC/PPO", CALEB, 12, 12, "P", 0),

    ("FASE", "FASE 4 — INTEGRACIÓN (E4)", "", "", 0, 0, "", 0),
    ("4.1", "Cálculo de las 5 métricas para ambos métodos", "Tablas de métricas", AMBOS, 12, 12, "P", 0),
    ("4.2", "Protocolo estadístico: medias, desviaciones, prueba de Wilcoxon", "Análisis estadístico", AMBOS, 12, 12, "P", 0),
    ("4.3", "Análisis de generalización — escenario 8, fuera de distribución", "Análisis de generalización", CALEB, 12, 12, "P", 0),
    ("4.4", "Tablero comparativo y demo en vivo", "Demo + tablero", LEO, 13, 13, "P", 0),
    ("4.5", "Informe final", "Informe", AMBOS, 13, 14, "P", 0),
    ("4.6", "Slides y ensayo de sustentación", "Diapositivas", AMBOS, 14, 14, "P", 0),

    ("FASE", "FASE 5 — DOCUMENTACIÓN (E5)", "", "", 0, 0, "", 0),
    ("5.1", "Definición del área de desarrollo y planteamiento del problema", "Ficha del curso", AMBOS, 1, 2, "R", 0),
    ("5.2", "Estado del arte: papers, tesis, productos comerciales y patentes", "Estado del arte", AMBOS, 2, 3, "R", 0),
    ("5.3", "Estructura de desglose del trabajo (EDT), diccionario y cronograma", "EDT + Gantt", AMBOS, 3, 4, "R", 0),
    ("5.4", "Actas de reunión con el asesor", "Actas", AMBOS, 5, 14, "P", 0),
    ("5.5", "Redacción del paper en formato IEEE", "Paper IEEE", AMBOS, 12, 14, "P", 0),
    ("5.6", "Sustentación del proyecto", "Presentación final", AMBOS, 15, 15, "P", 0),
]

# Precedencias para el calculo de ruta critica (CPM).
# REVISAR: la ruta critica solo es tan buena como estas dependencias.
PRED = {
    "1.1": ["3.1"], "1.2": ["1.1"], "1.3": ["1.1"], "1.4": ["1.3"],
    "1.5": [],      "1.6": ["1.5"], "1.7": ["1.6"],

    "2.1": ["1.5"], "2.2": ["2.1"], "2.3": ["2.2"], "2.4": ["3.5"],
    "2.5": ["2.4"], "2.6": ["2.5"], "2.7": ["2.6"], "2.8": ["2.4", "2.7"],

    "3.1": [],      "3.2": ["3.1"], "3.3": ["3.2", "3.11"], "3.4": ["3.3"],
    "3.5": ["3.4"], "3.6": ["3.5", "3.12"], "3.7": ["3.6"],
    "3.8": [],      "3.9": ["3.8"], "3.10": ["3.9"], "3.11": ["3.1"],
    "3.12": ["1.4", "3.11"], "3.13": ["3.2", "3.10", "3.12"],
    "3.14": ["3.10", "3.12"], "3.15": ["3.7"],

    "4.1": ["3.7", "3.14"], "4.2": ["4.1"], "4.3": ["4.1"],
    "4.4": ["4.2"], "4.5": ["4.2", "4.3"], "4.6": ["4.5"],

    "5.1": [], "5.2": ["5.1"], "5.3": ["5.2"], "5.4": [],
    "5.5": ["4.2"], "5.6": ["4.6", "5.5"],
}

ACT = [t for t in TAREAS if t[0] != "FASE"]
DUR = {t[0]: t[5] - t[4] + 1 for t in ACT}

# ---------- CPM: pasada hacia adelante y hacia atras ----------
def cpm():
    ES, EF = {}, {}
    pendientes = list(DUR)
    while pendientes:
        avance = False
        for k in list(pendientes):
            ps = PRED.get(k, [])
            if all(p in EF for p in ps):
                ES[k] = max([EF[p] for p in ps], default=0)
                EF[k] = ES[k] + DUR[k]
                pendientes.remove(k); avance = True
        if not avance:
            raise SystemExit(f"ciclo o dependencia inexistente en: {pendientes}")

    fin = max(EF.values())
    SUC = {k: [] for k in DUR}
    for k, ps in PRED.items():
        for p in ps:
            SUC[p].append(k)

    LF, LS = {}, {}
    pendientes = list(DUR)
    while pendientes:
        avance = False
        for k in list(pendientes):
            ss = SUC[k]
            if all(s in LS for s in ss):
                LF[k] = min([LS[s] for s in ss], default=fin)
                LS[k] = LF[k] - DUR[k]
                pendientes.remove(k); avance = True
        if not avance:
            raise SystemExit(f"ciclo en pasada inversa: {pendientes}")

    holgura = {k: LS[k] - ES[k] for k in DUR}
    return ES, EF, LS, LF, holgura, fin

ES, EF, LS, LF, HOLGURA, DURACION = cpm()
CRITICAS = {k for k, h in HOLGURA.items() if h == 0}

# ---------- porcentajes por duracion ----------
total_dur = sum(DUR.values())
PCT = {k: DUR[k] / total_dur for k in DUR}

# ---------- estilos ----------
AZUL, AZUL_MED = "1F3864", "2E5A9C"
VERDE, GRIS_AZUL = "70AD47", "9DC3E6"
AMBAR = "FFE699"
BORDE = Side(style="thin", color="BFBFBF")
ROJO  = Side(style="medium", color="FF0000")

wb = Workbook(); ws = wb.active; ws.title = "Cronograma"
anchos = {"A": 7, "B": 58, "C": 24, "D": 17, "E": 6, "F": 7, "G": 11}
for col, w in anchos.items():
    ws.column_dimensions[col].width = w
for i in range(N_SEM):
    ws.column_dimensions[get_column_letter(COL_S1 + i)].width = 4.3

ultima_col = COL_S1 + N_SEM - 1
LC = get_column_letter(ultima_col)

ws.merge_cells(f"A1:{LC}1")
c = ws["A1"]
c.value = "Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de 6 GDL"
c.font = Font(bold=True, size=12, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL)
c.alignment = Alignment(horizontal="center", vertical="center")
ws.row_dimensions[1].height = 30

ws.merge_cells(f"A2:{LC}2")
c = ws["A2"]
c.value = ("Cronograma de actividades — 15 semanas (14 de desarrollo + sustentación)   ·   "
           "Caleb Tomás Camargo Saavedra   ·   Leonardo Túpac Vásquez Cabrera")
c.font = Font(bold=True, size=10, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL_MED)
c.alignment = Alignment(horizontal="center", vertical="center")

FILA_H = 4
encabezados = [(1, "Cod."), (2, "Actividad"), (3, "Entregable"),
               (4, "Responsable"), (5, "Sem."), (6, "%"), (7, "Costo S/")]
for col, txt in encabezados:
    c = ws.cell(row=FILA_H, column=col, value=txt)
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL_MED)
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)
for i in range(N_SEM):
    c = ws.cell(row=FILA_H, column=COL_S1 + i, value=i + 1)
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL_MED)
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)

fila = FILA_H + 1
for cod, act, ent, resp, s_ini, s_fin, estado, costo in TAREAS:
    if cod == "FASE":
        ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
        c = ws.cell(row=fila, column=1, value=act)
        c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL)
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        for col in range(2, ultima_col + 1):
            ws.cell(row=fila, column=col).fill = PatternFill("solid", fgColor=AZUL)
        fila += 1
        continue

    critica = cod in CRITICAS
    ws.cell(row=fila, column=1, value=cod).alignment = Alignment(horizontal="center", vertical="center")
    cb = ws.cell(row=fila, column=2, value=act)
    cb.alignment = Alignment(vertical="center", wrap_text=True)
    if critica:
        cb.font = Font(bold=True, color="C00000")
        ws.cell(row=fila, column=1).font = Font(bold=True, color="C00000")
    ws.cell(row=fila, column=3, value=ent).alignment = Alignment(vertical="center", wrap_text=True)
    ws.cell(row=fila, column=4, value=resp).alignment = Alignment(vertical="center", wrap_text=True)
    ws.cell(row=fila, column=5, value=DUR[cod]).alignment = Alignment(horizontal="center", vertical="center")
    cp = ws.cell(row=fila, column=6, value=PCT[cod]); cp.number_format = "0.0%"
    cp.alignment = Alignment(horizontal="center", vertical="center")
    cc = ws.cell(row=fila, column=7, value=costo); cc.number_format = '"S/ "#,##0.00'
    cc.alignment = Alignment(horizontal="right", vertical="center")
    for col in range(1, 8):
        ws.cell(row=fila, column=col).border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)

    relleno = PatternFill("solid", fgColor=VERDE if estado == "R" else GRIS_AZUL)
    for i in range(N_SEM):
        c = ws.cell(row=fila, column=COL_S1 + i)
        c.border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)
        if s_ini <= i + 1 <= s_fin:
            c.value = estado; c.fill = relleno
            c.font = Font(bold=True, size=9, color="FFFFFF" if estado == "R" else "1F3864")
            c.alignment = Alignment(horizontal="center", vertical="center")
    fila += 1

fila_fin = fila - 1

# total de costo y porcentaje
ws.cell(row=fila, column=2, value="TOTAL").font = Font(bold=True)
ct = ws.cell(row=fila, column=6, value=sum(PCT.values())); ct.number_format = "0.0%"
ct.font = Font(bold=True); ct.alignment = Alignment(horizontal="center")
ct2 = ws.cell(row=fila, column=7, value=sum(t[7] for t in ACT))
ct2.number_format = '"S/ "#,##0.00'; ct2.font = Font(bold=True)
ct2.alignment = Alignment(horizontal="right")
for col in range(1, 8):
    ws.cell(row=fila, column=col).fill = PatternFill("solid", fgColor=AMBAR)
    ws.cell(row=fila, column=col).border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)
fila_total = fila
fila += 2

# linea roja vertical entre semana 4 y 5
for r in range(FILA_H, fila_total + 1):
    c = ws.cell(row=r, column=COL_LINEA); b = c.border
    c.border = Border(left=ROJO, right=b.right, top=b.top, bottom=b.bottom)

# leyenda
ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=3)
c = ws.cell(row=fila, column=1, value="LEYENDA")
c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL)
fila += 1
for marca, texto, color, fuente in (("R", "Realizado", VERDE, "FFFFFF"),
                                    ("P", "Programado", GRIS_AZUL, "1F3864")):
    c = ws.cell(row=fila, column=1, value=marca)
    c.fill = PatternFill("solid", fgColor=color); c.font = Font(bold=True, color=fuente)
    c.alignment = Alignment(horizontal="center")
    c.border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)
    ws.cell(row=fila, column=2, value=texto).font = Font(bold=True)
    fila += 1
ws.cell(row=fila, column=2, value="Código y actividad en rojo y negrita: paquete en la RUTA CRÍTICA (holgura cero)").font = Font(bold=True, color="C00000")
fila += 2
ws.cell(row=fila, column=1, value="La línea vertical roja marca el corte al cierre de la semana 4, fecha de la presentación de avance.")
ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
ws.cell(row=fila, column=1).font = Font(italic=True, size=9)

ws.freeze_panes = ws.cell(row=FILA_H + 1, column=COL_S1)

# ---------- hoja de ruta critica ----------
w2 = wb.create_sheet("Ruta crítica")
w2.column_dimensions["A"].width = 8
w2.column_dimensions["B"].width = 62
for col in "CDEFGH":
    w2.column_dimensions[col].width = 11
w2.merge_cells("A1:H1")
c = w2["A1"]
c.value = (f"Ruta crítica (CPM) — desarrollo: {max(EF[k] for k in CRITICAS if k != chr(34)+chr(34)) if False else max(EF[k] for k in CRITICAS if k != '5.6')} semanas" f"   ·   sustentación en la semana {DURACION}")
c.font = Font(bold=True, size=12, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL)
c.alignment = Alignment(horizontal="center", vertical="center")

hdr = ["Cod.", "Actividad", "Duración", "Inicio +temp.", "Fin +temp.",
       "Inicio tardío", "Fin tardío", "Holgura"]
for i, h in enumerate(hdr, start=1):
    c = w2.cell(row=3, column=i, value=h)
    c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor=AZUL_MED)
    c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

r = 4
for cod, act, *_ in ACT:
    crit = cod in CRITICAS
    w2.cell(row=r, column=1, value=cod)
    w2.cell(row=r, column=2, value=act).alignment = Alignment(wrap_text=True)
    for i, v in enumerate([DUR[cod], ES[cod], EF[cod], LS[cod], LF[cod], HOLGURA[cod]], start=3):
        w2.cell(row=r, column=i, value=v).alignment = Alignment(horizontal="center")
    if crit:
        for i in range(1, 9):
            w2.cell(row=r, column=i).font = Font(bold=True, color="C00000")
            w2.cell(row=r, column=i).fill = PatternFill("solid", fgColor="FCE4E4")
    r += 1

wb.save(SALIDA)

def cadena_critica():
    """Camino real: desde la actividad que cierra el proyecto, hacia atras
    por predecesoras criticas que encadenan (EF del predecesor == ES del sucesor)."""
    fin_k = max(CRITICAS, key=lambda k: EF[k])
    camino = [fin_k]
    while True:
        k = camino[-1]
        ant = [p for p in PRED.get(k, []) if p in CRITICAS and EF[p] == ES[k]]
        if not ant:
            break
        camino.append(max(ant, key=lambda p: DUR[p]))
    return list(reversed(camino))

orden = cadena_critica()
print(f"generado: {SALIDA}")
DES = max(EF[k] for k in CRITICAS if k != "5.6")
print(f"actividades: {len(ACT)}")
print(f"ruta critica de DESARROLLO: {DES} semanas   (sustentacion en la semana {DURACION})")
print(f"\nRUTA CRITICA ({len(orden)} paquetes):")
print("  " + " -> ".join(orden))
print("\nholgura por paquete no critico (semanas):")
for k in sorted(DUR, key=lambda k: (HOLGURA[k], ES[k])):
    if HOLGURA[k] > 0:
        print(f"  {k:5s} holgura {HOLGURA[k]:2d}")
