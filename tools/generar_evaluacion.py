import argparse
import sys
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6


def generar(semilla: int, cantidad: int, prefijo: str, ruta: Path, descripcion: str) -> None:
    C, M = contrato.cargar(), contrato.cargar_metricas()
    rng = np.random.default_rng(semilla)
    esc = Escena(cargar_e6(p.connect(p.DIRECT)), C)
    T = C["tarea_nominal"]
    escenas, descartadas = [], 0
    while len(escenas) < cantidad:
        etiqueta, obst = contrato.muestrear_con_obstaculo(C, rng)
        esc.poner_obstaculos(obst)
        if any(esc.ik_tcp(T[k]["pos"], T[k]["rpy"], T["q_inicial_rad"]) is None for k in ("p_pick", "p_place")):
            descartadas += 1
            continue
        n = len(escenas) + 1
        escenas.append({"etiqueta": f"{prefijo}{n:03d} {etiqueta.removeprefix('entrenamiento ')}",
                        "obstaculos": [{**o, "id": "o0_" + o["forma"],
                                        "dims": [round(float(v), 6) for v in o["dims"]],
                                        "pose": [round(float(v), 6) for v in o["pose"]]} for o in obst]})
    datos = {"descripcion": descripcion, "contrato": C["version"], "metricas": M["version"], "semilla": semilla,
             "descartadas_por_infactibles": descartadas, "escenas": escenas}
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False))
    formas = [e["etiqueta"].split()[1] for e in escenas]
    print(f"{len(escenas)} escenas ({descartadas} descartadas por infactibles): "
          + ", ".join(f"{f} {formas.count(f)}" for f in sorted(set(formas))))


def main():
    ap = argparse.ArgumentParser(description="Genera el conjunto fijo de evaluación o el de validación")
    ap.add_argument("--validacion", action="store_true",
                    help="genera shared_scenarios/validacion.yaml (50 escenas, semilla 2000) en vez del de evaluación")
    a = ap.parse_args()
    if a.validacion:
        generar(2000, 50, "V", contrato.RUTA_VALIDACION,
                "Conjunto de validación para elegir el mejor punto de cada entrenamiento. Generado por "
                "tools/generar_evaluacion.py --validacion: no editar a mano. Nunca se usa para evaluar.")
        return
    P = contrato.cargar_metricas()["protocolo"]
    generar(P["semilla_conjunto"], P["escenas_evaluacion"], "E", contrato.RUTA_EVALUACION,
            "Conjunto fijo de evaluación (metricas.yaml, protocolo). Generado por "
            "tools/generar_evaluacion.py: no editar a mano.")


if __name__ == "__main__":
    main()
