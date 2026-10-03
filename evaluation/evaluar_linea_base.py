import argparse
import csv
import gzip
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import pybullet as p

from evaluation.metricas import ContadorMetricas, error_meta, remuestrear
from geometry.distancia import MedidorDistancias
from gym_env.escena import ESLABONES_MOVILES, Escena, contrato
from gym_env.robot_e6 import cargar_e6

CAMPOS = ["variante", "planner", "consulta", "codigo", "exito", "colisiones", "L_cart_m", "L_art_rad",
          "t_computo_ms", "t_ejecucion_s", "d_min_obstaculos_m", "error_pos_m", "error_ori_rad"]


class Evaluador:
    def __init__(self):
        self.C, self.M = contrato.cargar(), contrato.cargar_metricas()
        self.m = cargar_e6(p.connect(p.DIRECT))
        self.esc = Escena(self.m, self.C)
        todos = {n: (self.m.cuerpo, self.m.eslabones[n]) for n in ESLABONES_MOVILES}
        todos["efector"] = (self.esc.efector, -1)
        self.cont = ContadorMetricas(
            self.esc, MedidorDistancias(self.m.cliente, todos, tuple(todos), d_max=1.0),
            self.M["accion"]["subpasos_colision"], self.M["m2_colisiones"]["histeresis_m"],
            self.C["efector"]["largo_m"])
        self.variantes = {et: obst for n in self.C["escenarios"] for et, obst in contrato.variantes(self.C, n)}
        if contrato.RUTA_EVALUACION.exists():
            self.variantes.update(dict(contrato.escenas_evaluacion()))
        T = self.C["tarea_nominal"]
        self.p_meta = T["p_place"]["pos"]
        self.quat_meta = p.getQuaternionFromEuler(T["p_place"]["rpy"])
        self._actual = None

    def evaluar(self, r: dict) -> dict:
        term = self.M["terminacion"]
        fila = {k: r.get(k) for k in ("variante", "planner", "consulta", "codigo", "t_computo_ms")}
        if r["codigo"] != 1 or not r["trayectoria"]:
            return {**fila, "exito": False, "colisiones": None, "L_cart_m": None, "L_art_rad": None,
                    "t_ejecucion_s": None, "d_min_obstaculos_m": None, "error_pos_m": None,
                    "error_ori_rad": None}
        if r["variante"] != self._actual:
            self.esc.poner_obstaculos(self.variantes[r["variante"]])
            self._actual = r["variante"]
        tray = np.array(r["trayectoria"])
        qs = remuestrear(tray[:, 0], tray[:, 1:], term["periodo_control_s"])
        self.cont.reiniciar(qs[0])
        for qa, qb in zip(qs, qs[1:]):
            self.cont.paso(qa, qb)
        e_pos, e_ori = error_meta(*self.cont.tcp(), self.p_meta, self.quat_meta)
        exito = (e_pos <= term["tolerancia_posicion_m"] and e_ori <= term["tolerancia_orientacion_rad"]
                 and self.cont.colisiones == 0)
        return {**fila, "exito": exito, "colisiones": self.cont.colisiones, "L_cart_m": self.cont.L_cart,
                "L_art_rad": self.cont.L_art, "t_ejecucion_s": float(tray[-1, 0]),
                "d_min_obstaculos_m": self.cont.d_min_obst, "error_pos_m": e_pos, "error_ori_rad": e_ori}


def resumen(filas: list[dict]) -> str:
    grupos = defaultdict(list)
    for f in filas:
        grupos[(f["variante"], f["planner"])].append(f)
    out = [f"{'variante':<18}{'planner':<13}{'M1 éxito':>10}{'M2 col.':>9}{'M3 cart m':>11}{'M3 art rad':>12}"
           f"{'M4 cómp. ms':>13}{'M4 ejec. s':>12}{'M5 d_min mm':>13}"]
    for (v, pl), fs in grupos.items():
        ok = [f for f in fs if f["colisiones"] is not None]
        med = lambda k: np.mean([f[k] for f in ok]) if ok else math.nan
        dmin = [f["d_min_obstaculos_m"] for f in ok if np.isfinite(f["d_min_obstaculos_m"])]
        out.append(f"{v:<18}{pl:<13}{sum(f['exito'] for f in fs):>5}/{len(fs):<4}"
                   f"{sum(f['colisiones'] or 0 for f in ok):>9}{med('L_cart_m'):>11.3f}{med('L_art_rad'):>12.2f}"
                   f"{np.mean([f['t_computo_ms'] for f in fs if f['t_computo_ms'] is not None]):>13.0f}"
                   f"{med('t_ejecucion_s'):>12.2f}"
                   f"{(np.mean(dmin) * 1000 if dmin else math.nan):>13.1f}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("crudo", type=Path)
    a = ap.parse_args()
    ev = Evaluador()
    abrir = gzip.open if a.crudo.suffix == ".gz" else open
    with abrir(a.crudo, "rt") as f:
        filas = [ev.evaluar(json.loads(l)) for l in f if l.strip()]
    base = a.crudo.name.removesuffix(".gz").removesuffix(".jsonl")
    salida = a.crudo.parent.parent / f"{base}_metricas.csv"
    with open(salida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        w.writeheader()
        w.writerows(filas)
    print(resumen(filas))
    print(f"\n{len(filas)} consultas -> {salida}")


if __name__ == "__main__":
    main()
