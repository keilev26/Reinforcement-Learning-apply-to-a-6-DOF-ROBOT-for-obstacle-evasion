import argparse
import math
import sys
from pathlib import Path

import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6
from shared_scenarios.contrato import _semialtura

DIAG = -45.0

DISPERSOS = {
    "D1 dos obstaculos separados": [
        dict(forma="cilindro", k=1.0, x=0.17, y=-0.20), dict(forma="prisma", k=0.9, x=0.27, y=-0.10)],
    "D2 tres obstaculos dispersos": [
        dict(forma="esfera", k=1.0, x=0.10, y=-0.22), dict(forma="cilindro", k=0.9, x=0.23, y=-0.23),
        dict(forma="prisma", k=0.8, x=0.28, y=-0.09)],
    "D3 cuatro obstaculos": [
        dict(forma="esfera", k=0.9, x=0.08, y=-0.17), dict(forma="cilindro", k=1.0, x=0.20, y=-0.25),
        dict(forma="prisma", k=0.9, x=0.22, y=-0.12), dict(forma="esfera", k=0.8, x=0.30, y=-0.18)],
    "D4 pasillo estrecho": [
        dict(forma="prisma", k=1.0, x=0.16, y=-0.12), dict(forma="cilindro", k=1.0, x=0.25, y=-0.25)],
    "D5 cinco obstaculos": [
        dict(forma="esfera", k=0.8, x=0.07, y=-0.20), dict(forma="cilindro", k=0.8, x=0.15, y=-0.26),
        dict(forma="prisma", k=0.8, x=0.20, y=-0.16), dict(forma="esfera", k=0.8, x=0.28, y=-0.22),
        dict(forma="cilindro", k=0.8, x=0.27, y=-0.08)],
    "D6 barrera con un hueco": [
        dict(forma="cilindro", k=1.2, x=0.14, y=-0.19), dict(forma="prisma", k=1.0, x=0.19, y=-0.14),
        dict(forma="esfera", k=1.0, x=0.23, y=-0.09)],
    "D7 barrera y obstaculos sueltos": [
        dict(forma="cilindro", k=1.3, x=0.15, y=-0.18), dict(forma="prisma", k=1.2, x=0.21, y=-0.12),
        dict(forma="esfera", k=0.8, x=0.27, y=-0.23)],
}

VARILLA = [0.35, 0.35, 3.0]
MURO = [3.0, 0.6, 2.0]
BARRA = [0.4, 0.4, 2.5]


def varilla(x, y, **kw):
    return dict(forma="cilindro", k=VARILLA, x=x, y=y, **kw)


def reja(centro, paso, n, k=VARILLA):
    cx, cy = centro
    d = (math.cos(math.radians(DIAG)), math.sin(math.radians(DIAG)))
    return [dict(forma="cilindro", k=k, x=cx + (i - (n - 1) / 2) * paso * d[0],
                 y=cy + (i - (n - 1) / 2) * paso * d[1]) for i in range(n)]


def desplazar(lista, dx, dy):
    return [{**o, "x": o["x"] + dx, "y": o["y"] + dy} for o in lista]


DIFICILES = {
    "R1 tres varillas verticales": [varilla(0.13, -0.19), varilla(0.19, -0.13), varilla(0.25, -0.07)],
    "R2 reja de varillas": desplazar(reja((0.15, -0.15), 0.065, 5), 0.04, -0.04),
    "R3 reja ancha de varillas": desplazar(reja((0.15, -0.15), 0.06, 7), 0.04, -0.02),
    "R4 muro largo": [dict(forma="prisma", k=MURO, x=0.19, y=-0.19, yaw=DIAG)],
    "R5 dos muros con hueco": [
        dict(forma="prisma", k=[2.0, 0.6, 2.0], x=0.16, y=-0.22, yaw=DIAG),
        dict(forma="prisma", k=[2.0, 0.6, 2.0], x=0.23, y=-0.15, yaw=DIAG)],
    "R6 barra horizontal baja": [
        dict(forma="cilindro", k=BARRA, x=0.17, y=-0.21, yaw=DIAG, horizontal=True, elevacion=0.04)],
    "R7 esfera gigante": [dict(forma="esfera", k=2.0, x=0.19, y=-0.21)],
    "R8 esfera gigante y varillas": desplazar([
        dict(forma="esfera", k=1.8, x=0.18, y=-0.18), varilla(0.08, -0.13), varilla(0.27, -0.24)], 0.0, -0.06),
    "R9 zigzag de muros": desplazar([
        dict(forma="prisma", k=[2.0, 0.6, 2.0], x=0.09, y=-0.18, yaw=DIAG),
        dict(forma="prisma", k=[2.0, 0.6, 2.0], x=0.20, y=-0.09, yaw=DIAG),
        dict(forma="prisma", k=[2.0, 0.6, 2.0], x=0.25, y=-0.24, yaw=DIAG)], 0.06, -0.06),
}

ALTO = [3.0, 0.6, 3.5]


def pared(l, k=ALTO):
    return dict(forma="prisma", k=k, x=0.15 + l * math.sqrt(0.5), y=-0.15 - l * math.sqrt(0.5), yaw=DIAG)


LADOS = {
    "L1 muro alto (0.56 m), extremos a -0.06 y +0.18 m": [pared(0.06)],
    "L2 muro muy alto (0.96 m)": [pared(0.06, [3.0, 0.6, 6.0])],
    "L3 muro altisimo (1.60 m)": [pared(0.06, [3.0, 0.6, 10.0])],
}

CONJUNTOS = {"dispersos": DISPERSOS, "dificiles": DIFICILES, "lados": LADOS}


def objeto(C: dict, i: int, s: dict) -> dict:
    o = contrato.objeto(C, f"o{i}_{s['forma']}", s["forma"], [s["x"], s["y"], 0.0, 0.0, 0.0, 0.0], s["k"])
    yaw = math.radians(s.get("yaw", 0.0))
    if s.get("horizontal"):
        o["pose"][3], o["pose"][5] = math.pi / 2, yaw
        o["pose"][2] = o["dims"][1] - 0.005 + s.get("elevacion", 0.0)
    else:
        o["pose"][5] = yaw
        o["pose"][2] = _semialtura(o) - 0.005 + s.get("elevacion", 0.0)
    return {**o, "dims": [round(float(v), 6) for v in o["dims"]], "pose": [round(float(v), 6) for v in o["pose"]]}


def construir(C: dict, lista: list) -> list[dict]:
    return [objeto(C, i, s) for i, s in enumerate(lista)]


def generar(nombre: str) -> None:
    C = contrato.cargar()
    esc = Escena(cargar_e6(p.connect(p.DIRECT)), C)
    T = C["tarea_nominal"]
    escenas = []
    for etiqueta, lista in CONJUNTOS[nombre].items():
        obst = construir(C, lista)
        esc.poner_obstaculos(obst)
        libre = all(esc.ik_tcp(T[k]["pos"], T[k]["rpy"], T["q_inicial_rad"]) is not None
                    for k in ("p_pick", "p_place"))
        print(f"{etiqueta:<32} {len(obst)} obstaculos  pick y place libres: {libre}")
        if libre:
            escenas.append({"etiqueta": etiqueta, "obstaculos": obst})
    ruta = RAIZ / "tools" / "escenas_demo" / f"{nombre}.yaml"
    ruta.write_text(yaml.safe_dump(
        {"descripcion": f"Escenas de demostracion '{nombre}' con varios obstaculos (fuera de distribucion: el "
                        "entrenamiento usa un solo obstaculo). Generado por tools/generar_escenas_demo.py",
         "contrato": C["version"], "escenas": escenas}, allow_unicode=True, sort_keys=False))


def main():
    ap = argparse.ArgumentParser(description="Genera escenas de demostracion con varios obstaculos")
    ap.add_argument("conjunto", choices=sorted(CONJUNTOS), nargs="?", default=None)
    a = ap.parse_args()
    for nombre in ([a.conjunto] if a.conjunto else sorted(CONJUNTOS)):
        generar(nombre)


if __name__ == "__main__":
    main()
