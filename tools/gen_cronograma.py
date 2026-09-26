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
COL_LINEA = COL_S1 + 5          # columna M = semana 6: la linea roja va a su izquierda

CALEB = "Caleb Camargo"
LEO   = "Leonardo Vásquez"
AMBOS = "Ambos"

# (codigo, actividad, entregable, responsable, sem_ini, sem_fin, estado, costo_soles)
TAREAS = [
    ("FASE", "FASE 1 — DISEÑO MECÁNICO (E1)", "", "", 0, 0, "", 0),
    ("1.1", "Celda de machine tending de escritorio para el Magician E6: layout, robot sobre la mesa, envolvente de seguridad", "Layout de celda", LEO, 5, 5, "P", 0),
    ("1.2", "Biblioteca de componentes CAD a escala de escritorio: centro CNC, mesa, utillaje, prensa, carro, pieza, primitivos", "Biblioteca CAD", LEO, 5, 6, "P", 0),
    ("1.3", "Geometría de colisión simplificada por componente de celda (la del robot: 3.16)", "Mallas de colisión", LEO, 6, 6, "P", 0),
    ("1.4", "Exportación a URDF/SDF con convención de anclaje para componer escenarios", "Componentes URDF/SDF", LEO, 6, 7, "P", 0),
    ("1.5", "Parámetros de Denavit-Hartenberg; cinemática directa e inversa (UR5e en sem. 4; se rehace para el E6 en sem. 5)", "Tabla DH + ecuaciones", LEO, 4, 4, "R", 0),
    ("1.6", "Envolvente de trabajo del E6 y alcanzabilidad de las poses de recogida y depósito", "Mapa de alcanzabilidad", LEO, 6, 7, "P", 0),
    ("1.7", "Análisis de singularidades de muñeca del E6; justificación del espacio de acción Δq", "Análisis de singularidades", LEO, 7, 7, "P", 0),

    ("FASE", "FASE 2 — DISEÑO ELECTRÓNICO (E2)", "", "", 0, 0, "", 0),
    ("2.1", "Análisis dinámico: par demandado por las trayectorias (dinámica inversa) frente al par estimado del E6", "Análisis dinámico", LEO, 9, 9, "P", 0),
    ("2.2", "Arquitectura de control del E6: controlador, TCP/IP (puertos 29999 y 30004), lazo ServoJ de 33 Hz", "Diagrama de control", LEO, 9, 9, "P", 0),
    ("2.3", "Efector final: ventosa o pinza, E/S de la brida, presupuesto de carga útil (0.75 kg)", "Selección de efector", LEO, 10, 10, "P", 0),
    ("2.4", "Unidad de cómputo: la inferencia de la política debe caber en el período de control de 30 ms", "Selección de cómputo", LEO, 10, 10, "P", 0),
    ("2.5", "Sensado: pose de los obstáculos en la celda real e instrumentación del vector de observación", "Esquema de sensado", LEO, 11, 11, "P", 0),
    ("2.6", "Comunicación PC ↔ controlador del E6: protocolo, frecuencia y jitter admisible", "Diagrama de comunicación", LEO, 11, 11, "P", 0),
    ("2.7", "Cadena de seguridad: paro de emergencia, detección de colisión del E6, filtro de seguridad por software", "Esquema de seguridad", LEO, 12, 12, "P", 0),
    ("2.8", "Presupuesto de latencia del lazo: lectura de q + inferencia + ServoJ vs. período de 30 ms", "Análisis de latencia", LEO, 12, 12, "P", 0),

    ("FASE", "FASE 3 — ALGORITMO (E3)", "", "", 0, 0, "", 0),
    ("3.1", "Contrato de escenarios y definición formal de las 5 métricas (v1.1 UR5e en sem. 4; v2.0 del E6 en sem. 5)", "Contrato de escenarios", AMBOS, 4, 4, "R", 0),
    ("3.2", "Entorno Gymnasium sobre PyBullet con el Magician E6 (Δt = 30 ms, transición cinemática)", "Entorno Gym", CALEB, 6, 7, "P", 0),
    ("3.3", "Formulación del MDP: acción Δq ≤ 0.05 rad, observación de 43 descriptores", "Especificación del MDP", CALEB, 7, 7, "P", 0),
    ("3.4", "Función de recompensa multiobjetivo: colisión, autocolisión, alcance de meta, suavidad", "Función de recompensa", CALEB, 8, 8, "P", 0),
    ("3.5", "Entrenamiento SAC desde cero — escenarios 1 y 2", "Política entrenada v1", CALEB, 9, 9, "P", 0),
    ("3.6", "Aleatorización de dominio (posición, escala, forma) e integración de escenarios 4-5-6", "Dominio aleatorizado", CALEB, 10, 10, "P", 0),
    ("3.7", "Entrenamiento completo: 5 semillas × escenarios núcleo", "Políticas + logs", CALEB, 10, 11, "P", 0),
    ("3.8", "Workspace ROS 2: ros2_control, MoveIt 2, Gazebo (UR5e en sem. 1-3; E6 y Gazebo Harmonic en sem. 5)", "Workspace ROS 2", LEO, 1, 3, "R", 0),
    ("3.9", "Configuración de OMPL: RRT-Connect y RRT* (UR5e en sem. 4; se vuelve a medir con el E6 en sem. 5)", "ompl_planning.yaml", LEO, 4, 4, "R", 0),
    ("3.10", "moveit_ros_benchmarks para tiempo, longitud y tasa de éxito", "Banco de pruebas OMPL", LEO, 6, 7, "P", 0),
    ("3.11", "Módulo de distancia mínima eslabón-obstáculo, validado contra FCL", "Módulo de distancias", LEO, 7, 8, "P", 0),
    ("3.12", "Generador de escenarios: compone los 8 escenarios desde la biblioteca CAD de E1", "Generador de escenarios", LEO, 8, 8, "P", 0),
    ("3.13", "Verificación de equivalencia PyBullet ↔ Gazebo: URDF, límites, geometría y escala", "Informe de equivalencia", AMBOS, 8, 9, "P", 0),
    ("3.14", "Ejecución batch de la línea base clásica sobre escenarios núcleo", "Corridas de línea base", LEO, 10, 11, "P", 0),
    ("3.15", "Subprueba PPO bajo la misma recompensa (extensión)", "Comparativa SAC/PPO", CALEB, 12, 12, "P", 0),
    ("3.16", "Modelo corregido del Magician E6: fuente única para PyBullet, MoveIt y Gazebo", "rl6gdl_e6_description", CALEB, 5, 5, "R", 0),

    ("FASE", "FASE 4 — INTEGRACIÓN (E4)", "", "", 0, 0, "", 0),
    ("4.1", "Cálculo de las 5 métricas para ambos métodos", "Tablas de métricas", AMBOS, 12, 12, "P", 0),
    ("4.2", "Protocolo estadístico: medias, desviaciones, prueba de Wilcoxon", "Análisis estadístico", AMBOS, 12, 12, "P", 0),
    ("4.3", "Análisis de generalización — escenario 8, fuera de distribución", "Análisis de generalización", CALEB, 12, 12, "P", 0),
    ("4.4", "Tablero comparativo y demo en vivo en simulación", "Demo + tablero", LEO, 13, 13, "P", 0),
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

# Paquetes hechos con el UR5e en las semanas 1-4 que se rehacen con el Magician E6.
# Conservan su barra R de las semanas 1-4 y suman esta segunda barra: (inicio, fin, estado).
REHACER_E6 = {
    "1.5": (5, 5, "P"),   # tabla DH del E6: pendiente
    "3.1": (5, 5, "R"),   # contrato v2.0, verificado en PyBullet y MoveIt
    "3.8": (5, 5, "R"),   # MoveIt con el E6 y Gazebo Harmonic con ejecución
    "3.9": (5, 5, "R"),   # OMPL medido con el E6
}

# Precedencias para el calculo de ruta critica (CPM).
# REVISAR: la ruta critica solo es tan buena como estas dependencias.
PRED = {
    "1.1": ["3.1"], "1.2": ["1.1"], "1.3": ["1.1"], "1.4": ["1.3"],
    "1.5": ["3.16"], "1.6": ["1.5"], "1.7": ["1.6"],

    "2.1": ["1.5"], "2.2": ["2.1"], "2.3": ["2.2"], "2.4": ["3.5"],
    "2.5": ["2.4"], "2.6": ["2.5"], "2.7": ["2.6"], "2.8": ["2.4", "2.7"],

    "3.1": ["3.16"], "3.2": ["3.1", "3.16"], "3.3": ["3.2", "3.11"], "3.4": ["3.3"],
    "3.5": ["3.4"], "3.6": ["3.5", "3.12"], "3.7": ["3.6"],
    "3.8": ["3.16"], "3.9": ["3.8"], "3.10": ["3.9"], "3.11": ["3.1"],
    "3.12": ["1.4", "3.11"], "3.13": ["3.2", "3.10", "3.12"],
    "3.14": ["3.10", "3.12"], "3.15": ["3.7"], "3.16": [],

    "4.1": ["3.7", "3.14"], "4.2": ["4.1"], "4.3": ["4.1"],
    "4.4": ["4.2"], "4.5": ["4.2", "4.3"], "4.6": ["4.5"],

    "5.1": [], "5.2": ["5.1"], "5.3": ["5.2"], "5.4": [],
    "5.5": ["4.2"], "5.6": ["4.6", "5.5"],
}

ACT = [t for t in TAREAS if t[0] != "FASE"]
# DUR: semanas totales de la fila (lo que muestra el Excel). DUR_CPM: lo que cuenta la ruta crítica.
DUR = {t[0]: t[5] - t[4] + 1 for t in ACT}
DUR_CPM = dict(DUR)
for k, (ini, fin, _) in REHACER_E6.items():
    DUR[k] += fin - ini + 1          # la barra del UR5e más la del E6
    DUR_CPM[k] = fin - ini + 1       # para la ruta crítica cuenta el trabajo con el E6
# 3.16 se hizo en un día (2026-09-22), antes que el resto de la semana 5: no ocupa una semana
# de la ruta crítica. Sin esta excepción el método, que solo cuenta semanas enteras, lo suma como 1.
DUR_CPM["3.16"] = 0

# ---------- CPM: pasada hacia adelante y hacia atras ----------
def cpm():
    ES, EF = {}, {}
    pendientes = list(DUR_CPM)
    while pendientes:
        avance = False
        for k in list(pendientes):
            ps = PRED.get(k, [])
            if all(p in EF for p in ps):
                ES[k] = max([EF[p] for p in ps], default=0)
                EF[k] = ES[k] + DUR_CPM[k]
                pendientes.remove(k); avance = True
        if not avance:
            raise SystemExit(f"ciclo o dependencia inexistente en: {pendientes}")

    fin = max(EF.values())
    SUC = {k: [] for k in DUR_CPM}
    for k, ps in PRED.items():
        for p in ps:
            SUC[p].append(k)

    LF, LS = {}, {}
    pendientes = list(DUR_CPM)
    while pendientes:
        avance = False
        for k in list(pendientes):
            ss = SUC[k]
            if all(s in LS for s in ss):
                LF[k] = min([LS[s] for s in ss], default=fin)
                LS[k] = LF[k] - DUR_CPM[k]
                pendientes.remove(k); avance = True
        if not avance:
            raise SystemExit(f"ciclo en pasada inversa: {pendientes}")

    holgura = {k: LS[k] - ES[k] for k in DUR_CPM}
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

    barras = [(s_ini, s_fin, estado)]
    if cod in REHACER_E6:
        barras.append(REHACER_E6[cod])
    for i in range(N_SEM):
        c = ws.cell(row=fila, column=COL_S1 + i)
        c.border = Border(left=BORDE, right=BORDE, top=BORDE, bottom=BORDE)
        for ini, fin, est in barras:
            if ini <= i + 1 <= fin:
                c.value = est
                c.fill = PatternFill("solid", fgColor=VERDE if est == "R" else GRIS_AZUL)
                c.font = Font(bold=True, size=9, color="FFFFFF" if est == "R" else "1F3864")
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

# linea roja vertical entre semana 5 y 6
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
ws.cell(row=fila, column=1, value="La línea vertical roja marca el corte al cierre de la semana 5.")
ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
ws.cell(row=fila, column=1).font = Font(italic=True, size=9)
fila += 1
ws.cell(row=fila, column=1, value=("Desde la semana 5 el robot es el DOBOT Magician E6. Las filas con una barra en las semanas 1-4 "
                                   "y otra en la semana 5 se hicieron con el UR5e y se rehicieron con el E6. La prueba en el E6 "
                                   "real es trabajo adicional fuera de este cronograma (EDT, sección 10)."))
ws.merge_cells(start_row=fila, start_column=1, end_row=fila, end_column=7)
ws.cell(row=fila, column=1).font = Font(italic=True, size=9)
ws.cell(row=fila, column=1).alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[fila].height = 40

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
    for i, v in enumerate([DUR_CPM[cod], ES[cod], EF[cod], LS[cod], LF[cod], HOLGURA[cod]], start=3):
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
        camino.append(max(ant, key=lambda p: DUR_CPM[p]))
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
