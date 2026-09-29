#!/usr/bin/env python3
"""Paquete 3.10 — Banco de pruebas de la línea base: corre las consultas y guarda las trayectorias.

Este script solo PLANIFICA y guarda datos crudos. Las 5 métricas las calcula
`evaluation/evaluar_linea_base.py` en el `.venv`, reproduciendo cada trayectoria con el mismo
contador que usa el entorno de RL (`evaluation/metricas.py`). Así ambos métodos se miden con el
mismo código, en lugar de confiar en las métricas propias de cada herramienta.

Se prefirió esto a `moveit_ros_benchmarks`: mide tiempo, longitud y éxito, pero no M2 ni M5 con la
definición del contrato, y depende de `warehouse_ros_mongo` (riesgo ya previsto en la EDT).

Salida: una línea JSON por consulta en results/raw/linea_base_<fecha>.jsonl con la variante, el
planificador, el código de resultado, el tiempo de cómputo y la trayectoria [[t, q1..q6], ...].

Uso (con planning_e6.launch.py corriendo):
  benchmark_linea_base.py --n 10
  benchmark_linea_base.py --planners RRTConnect,LazyPRMstar --variantes "2;5 k=2.0;8" --n 20
"""
import argparse, datetime, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rclpy
from p6_contrato import J, MARGEN_PLANIFICACION_M, P6, _raiz_repo, contrato


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--planners", default="RRTConnect,LazyPRMstar")
    ap.add_argument("--variantes", default="", help="etiquetas separadas por ';' (vacío = las 19)")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--tiempo", type=float, default=None,
                    help="presupuesto por consulta (s); por defecto el de metricas.yaml")
    ap.add_argument("--salida", default="")
    a = ap.parse_args()

    C = contrato.cargar()
    M = contrato.cargar_metricas()
    tiempo = a.tiempo or M["terminacion"]["timeout_planificacion_s"]
    todas = {et: obst for n in C["escenarios"] for et, obst in contrato.variantes(C, n)}
    elegidas = [v.strip() for v in a.variantes.split(";")] if a.variantes else list(todas)
    faltan = [v for v in elegidas if v not in todas]
    if faltan:
        sys.exit(f"variantes inexistentes: {faltan}")

    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    salida = a.salida or str(_raiz_repo() / "results" / "raw" / f"linea_base_{fecha}.jsonl")
    rclpy.init(); d = P6(C)
    T = C["tarea_nominal"]
    d.cargar([])
    ref = (d.ik("p_pick", T["q_inicial_rad"]), d.ik("p_place", T["q_inicial_rad"]))

    total = len(elegidas) * len(a.planners.split(",")) * a.n
    hechas = 0
    with open(salida, "w") as f:
        for et in elegidas:
            d.cargar(todas[et])
            qa, qb = d.ik("p_pick", ref[0]), d.ik("p_place", ref[1])
            for pl in a.planners.split(","):
                for i in range(a.n):
                    registro = {"contrato": C["version"], "metricas": M["version"], "variante": et,
                                "planner": pl, "consulta": i, "presupuesto_s": tiempo,
                                "escalado_velocidad": d.escalado, "tolerancia_meta_rad": 0.001,
                                "margen_planificacion_m": MARGEN_PLANIFICACION_M, "q_inicio": qa, "q_meta": qb}
                    if not (qa and qb):
                        registro.update(codigo=-31, t_computo_ms=None, trayectoria=[])
                    else:
                        t0 = time.perf_counter()
                        # Meta articular a 0.001 rad: con 0.01 rad el TCP quedaba a ~3 mm de mediana y
                        # 14 % de los planes excedían los 5 mm de M1 por la propia tolerancia de la meta
                        res = d.planificar_una(qa, qb, pl, tiempo, tolerancia=0.001)
                        registro["t_pared_ms"] = (time.perf_counter() - t0) * 1000
                        jt = res.trajectory.joint_trajectory
                        orden = [list(jt.joint_names).index(j) for j in J] if jt.joint_names else []
                        registro.update(
                            codigo=res.error_code.val, t_computo_ms=res.planning_time * 1000,
                            trayectoria=[[pt.time_from_start.sec + pt.time_from_start.nanosec * 1e-9,
                                          *[pt.positions[k] for k in orden]] for pt in jt.points])
                    f.write(json.dumps(registro) + "\n")
                    hechas += 1
            print(f"[{hechas}/{total}] {et}", flush=True)
    print(f"guardado en {salida}")
    d.destroy_node(); rclpy.shutdown()


if __name__ == "__main__":
    main()
