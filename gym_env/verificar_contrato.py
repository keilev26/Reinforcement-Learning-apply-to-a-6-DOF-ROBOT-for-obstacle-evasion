import argparse

import numpy as np
import pybullet as p

from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6

PASOS_RECTA = 100


def estados_en_colision(esc: Escena, qa, qb) -> int:
    return sum(bool(esc.en_colision(qa + (qb - qa) * i / PASOS_RECTA)) for i in range(PASOS_RECTA + 1))


def holgura_recta(esc: Escena, qa, qb) -> float:
    d = np.inf
    for i in range(PASOS_RECTA + 1):
        esc.fijar_q(qa + (qb - qa) * i / PASOS_RECTA)
        for b in esc.obstaculos:
            for cuerpo in (esc.m.cuerpo, esc.efector):
                d = min([d] + [x[8] for x in p.getClosestPoints(cuerpo, b, 0.2)])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escenarios", default="1,2,3,4,5,6,7,8")
    a = ap.parse_args()

    C = contrato.cargar()
    m = cargar_e6(p.connect(p.DIRECT))
    esc = Escena(m, C)
    T = C["tarea_nominal"]
    semilla = np.array(T["q_inicial_rad"])

    esc.poner_obstaculos([])
    ref = [esc.ik_tcp(T[k]["pos"], T[k]["rpy"], semilla) for k in ("p_pick", "p_place")]
    if any(r is None for r in ref):
        raise SystemExit("la tarea nominal no tiene solución libre de colisión ni en la celda vacía")
    print(f"Contrato {C['version']} | p_pick {T['p_pick']['pos']} | p_place {T['p_place']['pos']}")
    print(f"q_pick  = {np.round(ref[0], 4).tolist()}\nq_place = {np.round(ref[1], 4).tolist()}\n")
    print(f"{'variante':<24}{'pick':>6}{'place':>7}{'recta obstruida':>18}   veredicto")

    for n in [int(x) for x in a.escenarios.split(",")]:
        for etiqueta, obst in contrato.variantes(C, n):
            esc.poner_obstaculos(obst)
            qa = esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], ref[0])
            qb = esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], ref[1])
            recta = estados_en_colision(esc, *ref)
            paso = C["escenarios"][n].get("prueba") == "paso_estrecho"
            if qa is None or qb is None:
                ver = "INFACTIBLE: pose de la tarea en colisión"
            elif paso and recta == 0:
                ver = f"factible; la recta cruza el paso con holgura {holgura_recta(esc, *ref) * 1000:.0f} mm"
            elif paso:
                ver = "factible, pero la recta NO cruza el paso: choca con los postes"
            elif n != 1 and recta == 0:
                ver = "factible, pero el obstáculo NO obstruye"
            else:
                ver = "factible"
            print(f"{etiqueta:<24}{'ok' if qa is not None else 'NO':>6}{'ok' if qb is not None else 'NO':>7}"
                  f"{recta:>12}/{PASOS_RECTA + 1:<5}   {ver}")


if __name__ == "__main__":
    main()
