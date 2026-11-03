import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pybullet as p

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6

PASO = 0.05


def arista_libre(esc, a, b):
    n = max(2, int(np.ceil(np.linalg.norm(b - a) / PASO)))
    return not any(esc.en_colision(a + (b - a) * t) for t in np.linspace(0, 1, n + 1)[1:])


def extender(esc, arbol, destino):
    qs = np.array([n[0] for n in arbol])
    i = int(np.argmin(np.linalg.norm(qs - destino, axis=1)))
    d = destino - qs[i]
    nuevo = destino if np.linalg.norm(d) <= 0.3 else qs[i] + d / np.linalg.norm(d) * 0.3
    if arista_libre(esc, qs[i], nuevo):
        arbol.append((nuevo, i))
        return len(arbol) - 1
    return None


def camino(arbol, i):
    out = []
    while i is not None:
        out.append(arbol[i][0])
        i = arbol[i][1]
    return out


def suavizar(esc, ruta, rng, intentos=200):
    ruta = list(ruta)
    for _ in range(intentos):
        if len(ruta) < 3:
            break
        i, j = sorted(rng.choice(len(ruta), 2, replace=False))
        if j - i > 1 and arista_libre(esc, ruta[i], ruta[j]):
            ruta = ruta[:i + 1] + ruta[j:]
    return ruta


def rrt_connect(esc, q0, q1, limite_s, rng):
    A, B = [(q0, None)], [(q1, None)]
    invertido = False
    t0 = time.time()
    while time.time() - t0 < limite_s:
        q = rng.uniform(esc.m.q_min, esc.m.q_max)
        i = extender(esc, A, q)
        if i is not None:
            j = extender(esc, B, A[i][0])
            while j is not None and np.linalg.norm(B[j][0] - A[i][0]) > 1e-9:
                j = extender(esc, B, A[i][0])
            if j is not None:
                ruta = (camino(B, j)[::-1] + camino(A, i)) if invertido else (camino(A, i)[::-1] + camino(B, j))
                return suavizar(esc, ruta, rng), time.time() - t0
        A, B, invertido = B, A, not invertido
    return None, time.time() - t0


def main():
    ap = argparse.ArgumentParser(description="Comprueba con RRT-Connect que cada escena tiene solución")
    ap.add_argument("archivo", type=Path)
    ap.add_argument("--limite", type=float, default=60.0)
    a = ap.parse_args()
    C = contrato.cargar()
    T = C["tarea_nominal"]
    esc = Escena(cargar_e6(p.connect(p.DIRECT)), C)
    rng = np.random.default_rng(0)
    for etiqueta, obst, par in contrato.escenas_con_par(a.archivo):
        esc.poner_obstaculos(obst)
        pick = par["pick"] if par else T["p_pick"]["pos"]
        place = par["place"] if par else T["p_place"]["pos"]
        q0 = esc.ik_tcp(pick, T["p_pick"]["rpy"], T["q_inicial_rad"])
        q1 = esc.ik_tcp(place, T["p_place"]["rpy"], T["q_inicial_rad"])
        if q0 is None or q1 is None:
            print(f"{etiqueta:<34}sin cinemática inversa libre en pick o place")
            continue
        ruta, t = rrt_connect(esc, np.asarray(q0), np.asarray(q1), a.limite, rng)
        print(f"{etiqueta:<34}{'RESUELTA' if ruta else 'sin solución en ' + str(int(a.limite)) + ' s':<24}"
              f"{'' if ruta is None else str(len(ruta)) + ' puntos, '}{t:.1f} s", flush=True)


if __name__ == "__main__":
    main()
