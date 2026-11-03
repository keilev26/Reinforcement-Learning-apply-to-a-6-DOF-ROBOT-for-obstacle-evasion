import numpy as np

PIEZAS_KIT = {
    "P01": ("caja", [0.075, 0.075, 0.075], (0.0, 0.0)), "P02": ("caja", [0.075, 0.075, 0.150], (0.0, 0.0)),
    "P03": ("caja", [0.125, 0.075, 0.050], (0.0, 0.0)), "P04": ("caja", [0.175, 0.025, 0.150], (0.0, 0.0)),
    "P05": ("caja", [0.125, 0.075, 0.150], (0.0, 0.0)), "P06": ("caja", [0.175, 0.075, 0.120], (0.0, 0.0)),
    "P07": ("caja", [0.125, 0.125, 0.100], (0.0, 0.0)), "P08": ("caja", [0.275, 0.075, 0.020], (0.0, 0.0)),
    "R01": ("cilindro", [0.100, 0.030], (0.0, 0.0)), "R02": ("cilindro", [0.220, 0.015], (0.0, 0.0)),
    "R03": ("cilindro", [0.120, 0.050], (0.0, 0.0)), "R04": ("cilindro", [0.100, 0.050], (0.0, 0.0)),
    "R05": ("cilindro", [0.170, 0.050], (0.0, 0.0)), "R06": ("cilindro", [0.060, 0.060], (0.0, 0.0)),
    "R07": ("cilindro", [0.120, 0.040], (0.0, 0.0)), "R08": ("caja", [0.0866, 0.075, 0.100], (0.0, -0.0125)),
    "R09": ("caja", [0.100, 0.100, 0.120], (0.0, 0.0)),
    "T01": ("caja", [0.175, 0.025, 0.350], (0.0, 0.0)), "T02": ("caja", [0.075, 0.075, 0.350], (0.0, 0.0)),
    "T03": ("cilindro", [0.450, 0.015], (0.0, 0.0)), "T04": ("caja", [0.275, 0.025, 0.300], (0.0, 0.0)),
    "T05": ("cilindro", [0.300, 0.030], (0.0, 0.0)),
}

ZONAS = {"CNC": (0.38, 0.68, -0.25, 0.25), "bandeja": (-0.10, 0.10, -0.425, -0.175),
         "base del robot": (-0.09, 0.09, -0.09, 0.09)}
ALTURA_PASILLO_M, ANCHO_PASILLO_M = 0.20, 0.11
N_OBSTACULOS = (1, 2, 3, 4, 5, 6)
P_OBSTACULOS = (0.20, 0.20, 0.20, 0.15, 0.15, 0.10)
RADIO_MAX_M = 0.52


def altura(pieza) -> float:
    forma, dims, _ = PIEZAS_KIT[pieza[0]]
    return (dims[2] if forma == "caja" else dims[0]) + (pieza[4] if len(pieza) > 4 else 0.0)


def objeto_kit(i: int, pieza) -> dict:
    codigo, x, y, yaw = pieza[:4]
    z0 = pieza[4] if len(pieza) > 4 else 0.0
    forma, dims, (dx, dy) = PIEZAS_KIT[codigo]
    alto = dims[2] if forma == "caja" else dims[0]
    a = np.radians(yaw)
    cx = x / 1000 + dx * np.cos(a) - dy * np.sin(a)
    cy = y / 1000 + dx * np.sin(a) + dy * np.cos(a)
    return dict(id=f"o{i}_{codigo}", forma=forma, dims=list(dims),
                pose=[round(float(cx), 4), round(float(cy), 4), round(float(z0 + alto / 2), 4), 0.0, 0.0,
                      round(float(a), 4)])


def caja_xy(pieza):
    codigo, x, y, yaw = pieza[:4]
    forma, dims, _ = PIEZAS_KIT[codigo]
    hx, hy = (dims[0] / 2, dims[1] / 2) if forma == "caja" else (dims[1], dims[1])
    if yaw % 180 == 90:
        hx, hy = hy, hx
    return x / 1000 - hx, x / 1000 + hx, y / 1000 - hy, y / 1000 + hy


def _se_cruzan(a, b, margen: float = 0.0) -> bool:
    return a[0] < b[1] + margen and a[1] > b[0] - margen and a[2] < b[3] + margen and a[3] > b[2] - margen


def _toca_pasillo(caja, punto) -> bool:
    for t in np.linspace(0.0, 1.0, 25):
        c = (punto[0] * t, punto[1] * t)
        if _se_cruzan(caja, (c[0], c[0], c[1], c[1]), ANCHO_PASILLO_M):
            return True
    return False


def conflictos(piezas, pick=None, place=None) -> list[str]:
    cajas = [caja_xy(pz) for pz in piezas]
    malos = []
    for i, a in enumerate(cajas):
        nombre = f"{piezas[i][0]} en ({piezas[i][1]},{piezas[i][2]})"
        for zona, z in ZONAS.items():
            if _se_cruzan(a, z):
                malos.append(f"{nombre} pisa {zona}")
        if altura(piezas[i]) > ALTURA_PASILLO_M:
            for destino, punto in (("recoger", pick), ("depositar", place)):
                if punto is not None and _toca_pasillo(a, punto):
                    malos.append(f"{nombre} tapa el pasillo a {destino}")
        for j in range(i + 1, len(cajas)):
            if _se_cruzan(a, cajas[j]) and piezas[i][4:5] == piezas[j][4:5]:
                malos.append(f"{nombre} y {piezas[j][0]} en ({piezas[j][1]},{piezas[j][2]}) se solapan")
    return malos


def muestrear(rng, pick, place, intentos: int = 40) -> tuple[str, list[dict]]:
    n = int(rng.choice(N_OBSTACULOS, p=P_OBSTACULOS))
    codigos = list(PIEZAS_KIT)
    piezas = []
    for _ in range(intentos * n):
        if len(piezas) == n:
            break
        x, y = (int(rng.integers(-9, 7)) * 50 + 25, int(rng.integers(-9, 9)) * 50 + 25)
        if np.hypot(x, y) / 1000 > RADIO_MAX_M:
            continue
        cand = (codigos[int(rng.integers(len(codigos)))], x, y, 90 * int(rng.integers(4)))
        if not conflictos(piezas + [cand], pick, place):
            piezas.append(cand)
    etiqueta = f"kit n={len(piezas)} " + ";".join(f"{c}({x},{y},{yaw})" for c, x, y, yaw, *_ in piezas)
    return etiqueta, [objeto_kit(i, pz) for i, pz in enumerate(piezas)]


COMBINACIONES = [
    ("A", "Un obstáculo (como el entrenamiento)", [("R01", 225, -225, 0)]),
    ("B", "Dos obstáculos separados", [("P01", 175, -225, 0), ("R05", 275, -125, 0)]),
    ("C", "Portal: dos columnas y una viga", [("P02", 225, -275, 0), ("P02", 225, -75, 0), ("P08", 225, -175, 90, 0.15)]),
    ("D", "Pasillo entre dos muros", [("P04", 125, -175, 90), ("P04", 275, -175, 90)]),
    ("E", "Bosque de cinco", [("R01", 125, -125, 0), ("R02", 225, -175, 0), ("R03", 175, -275, 0), ("P01", 275, -75, 0),
                              ("R07", 75, 175, 0)]),
    ("F", "Escalera y ángulo", [("P06", 225, -225, 0), ("P05", 175, -125, 0)]),
    ("G", "Cruz y postes", [("P07", 225, -175, 0), ("R02", 125, -275, 0), ("R02", 325, -75, 0)]),
    ("H", "Barrera de tres muros y una cruz", [("P04", 225, -275, 0), ("P04", 425, -275, 0), ("P04", 225, -125, 90),
                                                   ("P07", 175, 25, 0)]),
]


def _campo_denso():
    tipos = ["R01", "P01", "R03", "R04", "R06", "P03", "R07", "R09"]
    piezas, k = [], 0
    for x in (-375, -225, -75, 75, 225):
        for y in (-375, -225, -75, 75, 225, 375):
            if abs(x) < 120 and abs(y) < 120:
                continue
            if np.hypot(x - 0, y + 300) < 130 or np.hypot(x - 300, y) < 130 or (abs(x) < 120 and -425 < y < -175):
                continue
            piezas.append((tipos[k % len(tipos)], x, y, 0))
            k += 1
    return piezas


COMBINACIONES_2 = [
    ("I", "Bosque de 11 postes finos", [("R02", x, y, 0) for x, y in (
        (-375, 225), (-225, 225), (-75, 225), (75, 225), (225, 225), (-375, -175), (-225, -175),
        (125, -175), (225, -225), (175, -75), (275, -125))]),
    ("J", "Muro largo de 700 mm y vigas", [("P04", x, -125, 0) for x in (-375, -175, 25, 225)]
     + [("P08", -325, 225, 0), ("P08", 25, 325, 0), ("P08", 275, 175, 90)]),
    ("K", "Dos filas de muros con puertas de 125 mm", [("P04", x, y, 90) for x in (-175, 175) for y in (-325, -25, 275)]),
    ("L", "Vigas planas sobre toda la mesa", [("P08", 175, -225, 90), ("P08", 425, -375, 0), ("P08", -375, -325, 0),
                                              ("P08", -375, 325, 0), ("P08", 25, 325, 0), ("P08", 175, 125, 90),
                                              ("P08", -225, 0, 90)]),
    ("M", "Cuatro portales", [("P02", 225, -275, 0), ("P02", 225, -75, 0), ("P08", 225, -175, 90, 0.15),
                              ("P02", -375, -225, 0), ("P02", -175, -225, 0), ("P08", -275, -225, 0, 0.15),
                              ("P02", -375, 225, 0), ("P02", -175, 225, 0), ("P08", -275, 225, 0, 0.15),
                              ("P02", 125, 275, 0), ("P02", 325, 275, 0), ("P08", 225, 275, 0, 0.15)]),
    ("N", "Mezcla de grandes y delgados", [("P04", 225, -225, 0), ("R02", 175, 75, 0), ("P07", -275, -175, 0),
                                           ("R05", -375, 75, 0), ("P06", -275, 275, 0), ("R03", -125, 225, 0),
                                           ("P05", 75, 225, 0), ("P08", -325, -375, 0), ("R02", 125, -125, 0),
                                           ("P04", 275, 275, 90), ("R04", 325, -325, 0), ("P02", -175, 25, 0),
                                           ("R02", -475, -75, 0), ("P03", 225, 425, 0)]),
    ("O", "Campo denso de piezas pequeñas", _campo_denso()),
    ("P", "Dos barreras en L", [("P04", -175, -125, 0), ("P04", 25, -125, 0), ("P04", 225, -125, 0),
                                ("P04", -275, 125, 90), ("P04", -275, 325, 90), ("P04", 125, 325, 0), ("P04", 325, 325, 0)]),
]


COMBINACIONES_3 = [
    ("Q", "Bosque de postes de 450 mm", [("T03", x, y, 0) for x, y in (
        (-375, 225), (-225, 225), (-75, 225), (75, 225), (225, 225), (-375, -175), (-225, -175),
        (125, -175), (225, -225), (175, -75), (275, -125))]),
    ("R", "Muros de 350 mm con puertas", [("T01", -175, y, 90) for y in (-325, -25, 275)]
     + [("T01", 175, -325, 90), ("T01", 175, 275, 90), ("T01", 275, -175, 90)]),
    ("S", "Portales altos de 350 mm", [("T02", 275, -375, 0), ("T02", 275, -175, 0), ("P08", 275, -275, 90, 0.35),
                                       ("T02", -375, -225, 0), ("T02", -175, -225, 0), ("P08", -275, -225, 0, 0.35),
                                       ("T02", -375, 225, 0), ("T02", -175, 225, 0), ("P08", -275, 225, 0, 0.35),
                                       ("T02", 125, 275, 0), ("T02", 325, 275, 0), ("P08", 225, 275, 0, 0.35)]),
    ("T", "Muro largo alto de 700 mm", [("T01", x, 175, 0) for x in (-375, -175, 25, 225)]
     + [("T01", 275, -325, 90), ("T04", 225, -275, 90), ("T04", -325, -325, 0), ("T04", -325, 325, 0), ("T04", 325, 325, 0)]),
    ("U", "Mezcla alta", [("T01", 225, -225, 0), ("T03", 175, 75, 0), ("T02", -275, -175, 0), ("R05", -375, 75, 0),
                          ("T05", -275, 275, 0), ("R03", -125, 225, 0), ("T04", 75, 225, 0), ("T03", 125, -125, 0),
                          ("T01", 275, 275, 90), ("T05", 325, -325, 0), ("P02", -175, 25, 0), ("T03", -475, -75, 0)]),
    ("V", "Túnel de muros altos junto a la trayectoria", [("T01", 175, -325, 90), ("T01", 275, -225, 90),
                                                          ("T01", 325, -375, 0), ("T04", -275, -225, 0),
                                                          ("T03", 75, 125, 0), ("T05", 325, -175, 0)]),
]
