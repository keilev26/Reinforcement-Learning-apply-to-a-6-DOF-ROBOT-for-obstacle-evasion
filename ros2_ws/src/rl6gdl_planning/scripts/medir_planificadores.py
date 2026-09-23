#!/usr/bin/env python3
"""Paquete 3.9 con el Magician E6: compara planificadores y barre parámetros sobre el contrato v2.0.

Para cada variante elegida del contrato, planifica pick -> place n veces con cada planificador y
reporta éxito, trayectorias que chocan en la validación independiente (0.02 rad), tiempo de
planificación y longitud articular. Las configuraciones de pick y place se calculan una vez por
variante, así que todos los planificadores resuelven exactamente la misma consulta.

Requiere planning_e6.launch.py corriendo. Los planificadores deben estar declarados en
config/ompl_planning_e6.yaml.

Uso:
  medir_planificadores.py --planners RRTConnect,RRTstar,LazyPRMstar,RRT --n 10
  medir_planificadores.py --planners RRTConnect --set range=1.0 --etiqueta "range 1.0"
  medir_planificadores.py --variantes "2;5 k=2.0;8"
"""
import argparse, os, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from p6_contrato import P6, contrato

VARIANTES = "2;5 k=2.0;8"   # obstáculo nominal, el más grande del núcleo, y el fuera de distribución


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planners", default="RRTConnect,RRTstar,LazyPRMstar,RRT")
    ap.add_argument("--variantes", default=VARIANTES, help="etiquetas separadas por ';'")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tiempo", type=float, default=5.0)
    ap.add_argument("--set", action="append", default=[], metavar="CLAVE=VALOR",
                    help="parámetro de OMPL aplicado a cada planificador listado (repetible)")
    ap.add_argument("--etiqueta", default="")
    a = ap.parse_args()

    C = contrato.cargar()
    todas = {et: obst for n in C["escenarios"] for et, obst in contrato.variantes(C, n)}
    elegidas = [v.strip() for v in a.variantes.split(";")]
    faltan = [v for v in elegidas if v not in todas]
    if faltan:
        sys.exit(f"variantes inexistentes: {faltan}. Disponibles: {list(todas)}")

    rclpy.init(); d = P6(C)
    planners = a.planners.split(",")
    if a.set:
        claves = [kv.split("=", 1)[0] for kv in a.set]
        valores = [kv.split("=", 1)[1] for kv in a.set]
        for pl in planners:
            d.fijar(pl, claves, valores)

    T = C["tarea_nominal"]
    d.cargar([])
    ref = (d.ik("p_pick", T["q_inicial_rad"]), d.ik("p_place", T["q_inicial_rad"]))
    print(f"\n### {a.etiqueta} | contrato {C['version']} | n={a.n} | {a.tiempo} s"
          + (f" | {' '.join(a.set)}" if a.set else ""))
    print(f"{'variante':<14}{'planner':<13}{'exito':>8}{'chocan':>8}{'t_med ms':>10}"
          f"{'long med':>10}{'long min':>10}   fallos")
    for et in elegidas:
        d.cargar(todas[et])
        qa, qb = d.ik("p_pick", ref[0]), d.ik("p_place", ref[1])
        if not (qa and qb):
            print(f"{et:<14}INFACTIBLE"); continue
        for pl in planners:
            ok, choca, tm, fallos, L = d.planificar_n(qa, qb, a.n, pl, a.tiempo)
            lm = statistics.mean(L) if L else float("nan")
            lmin = min(L) if L else float("nan")
            print(f"{et:<14}{pl:<13}{ok:>4}/{a.n:<3}{choca:>6}  {tm:>10.0f}{lm:>10.2f}{lmin:>10.2f}   "
                  + (", ".join(f"{k}={v}" for k, v in fallos.items()) or "-"))
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
