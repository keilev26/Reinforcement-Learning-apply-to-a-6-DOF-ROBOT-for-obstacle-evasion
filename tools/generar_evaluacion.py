"""Protocolo estadístico (metricas.yaml 2.1): genera el conjunto FIJO de escenas de evaluación.

Muestrea escenas de la distribución de entrenamiento (siempre con obstáculo: el espacio libre ya
está entre las variantes fijas del contrato) con una semilla propia, distinta de las de
entrenamiento. Descarta las escenas donde p_pick o p_place no tienen cinemática inversa libre de
colisión: ninguna de los dos métodos podría resolverlas. Escribe shared_scenarios/evaluacion.yaml,
que se versiona: la política y la línea base se evalúan exactamente en las mismas escenas.

Uso: .venv/bin/python tools/generar_evaluacion.py
"""
import sys
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.escena import Escena, contrato  # noqa: E402
from gym_env.robot_e6 import cargar_e6  # noqa: E402


def main():
    C, M = contrato.cargar(), contrato.cargar_metricas()
    P = M["protocolo"]
    rng = np.random.default_rng(P["semilla_conjunto"])
    esc = Escena(cargar_e6(p.connect(p.DIRECT)), C)
    T = C["tarea_nominal"]
    escenas, descartadas = [], 0
    while len(escenas) < P["escenas_evaluacion"]:
        etiqueta, obst = contrato.muestrear_con_obstaculo(C, rng)
        esc.poner_obstaculos(obst)
        if any(esc.ik_tcp(T[k]["pos"], T[k]["rpy"], T["q_inicial_rad"]) is None for k in ("p_pick", "p_place")):
            descartadas += 1
            continue
        n = len(escenas) + 1
        escenas.append({"etiqueta": f"E{n:03d} {etiqueta.removeprefix('entrenamiento ')}",
                        "obstaculos": [{**o, "id": "o0_" + o["forma"],
                                        "dims": [round(float(v), 6) for v in o["dims"]],
                                        "pose": [round(float(v), 6) for v in o["pose"]]} for o in obst]})
    datos = {"descripcion": "Conjunto fijo de evaluación (metricas.yaml, protocolo). Generado por "
                            "tools/generar_evaluacion.py: no editar a mano.",
             "contrato": C["version"], "metricas": M["version"], "semilla": P["semilla_conjunto"],
             "descartadas_por_infactibles": descartadas, "escenas": escenas}
    contrato.RUTA_EVALUACION.write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False))
    formas = [e["etiqueta"].split()[1] for e in escenas]
    print(f"{len(escenas)} escenas ({descartadas} descartadas por infactibles): "
          + ", ".join(f"{f} {formas.count(f)}" for f in sorted(set(formas))))


if __name__ == "__main__":
    main()
