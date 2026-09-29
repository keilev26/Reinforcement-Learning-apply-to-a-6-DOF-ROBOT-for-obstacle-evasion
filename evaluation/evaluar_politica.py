"""Las 5 métricas de una política entrenada, en el mismo formato que la línea base (paquete 4.1).

La política determinista se ejecuta en `EntornoE6` sobre variantes del contrato. M2, M3 y M5 salen
del mismo contador que usa el evaluador de la línea base; M4 cómputo es la suma de los tiempos de
inferencia de la política en el episodio (metricas.yaml), y M4 ejecución, pasos × 30 ms.

Uso:
  .venv/bin/python -m evaluation.evaluar_politica training/runs/<corrida>/modelo_final.zip
  .venv/bin/python -m evaluation.evaluar_politica <modelo.zip> --variantes "2;8" --episodios 3
"""
import argparse
import csv
import time
from pathlib import Path

import numpy as np
from stable_baselines3 import SAC

from evaluation.evaluar_linea_base import CAMPOS, resumen
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato


def evaluar(modelo, env, variante: str, consulta: int) -> dict:
    n = int(variante.split()[0])
    obs, info = env.reset(options={"escenario": n, "variante": variante})
    t_inf, fin = 0.0, False
    while not fin:
        t0 = time.perf_counter()
        a, _ = modelo.predict(obs, deterministic=True)
        t_inf += time.perf_counter() - t0
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
    return {"variante": variante, "planner": "SAC", "consulta": consulta, "codigo": None,
            "exito": info["exito"], "colisiones": info["colisiones"], "L_cart_m": info["L_cart_m"],
            "L_art_rad": info["L_art_rad"], "t_computo_ms": t_inf * 1000,
            "t_ejecucion_s": info["t_ejecucion_s"], "d_min_obstaculos_m": info["d_min_obstaculos_m"],
            "error_pos_m": info["error_pos_m"], "error_ori_rad": info["error_ori_rad"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo", type=Path)
    ap.add_argument("--variantes", default="", help="etiquetas separadas por ';' (vacío = las 19)")
    ap.add_argument("--episodios", type=int, default=1,
                    help="episodios por variante. Con política determinista y entorno cinemático "
                         "todos los episodios de una variante son idénticos")
    a = ap.parse_args()
    C = contrato.cargar()
    todas = [et for n in C["escenarios"] for et, _ in contrato.variantes(C, n)]
    elegidas = [v.strip() for v in a.variantes.split(";")] if a.variantes else todas
    modelo = SAC.load(a.modelo, device="cpu")
    env = EntornoE6()
    filas = [evaluar(modelo, env, v, i) for v in elegidas for i in range(a.episodios)]
    env.close()
    salida = a.modelo.parent / f"{a.modelo.stem}_metricas.csv"
    with open(salida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    print(resumen(filas))
    inf = [f["t_computo_ms"] / max(1, round(f["t_ejecucion_s"] / env.dt)) for f in filas]
    print(f"\ninferencia media por paso: {np.mean(inf):.3f} ms  ->  {salida}")


if __name__ == "__main__":
    main()
