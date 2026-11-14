import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env import kit
from gym_env.escena import contrato
from tools.generar_set_kit import Verificador, clave, escena


def main():
    ap = argparse.ArgumentParser(description="Conjunto de prueba grande: familias de prueba con pares vistos y no vistos")
    ap.add_argument("--cantidad", type=int, default=200)
    ap.add_argument("--limite", type=float, default=5.0)
    a = ap.parse_args()
    dir_sc = RAIZ / "shared_scenarios"
    ver = Verificador(a.limite)
    todos = {q["id"]: q for q in contrato.pares_kit(dir_sc / "pares_kit.yaml")}
    ids = list(kit.PARES_VISTOS) + list(kit.PARES_NO_VISTOS)
    prohibidas = {clave(e) for e in yaml.safe_load((dir_sc / "kit_evaluacion.yaml").read_text())["escenas"]}
    rng = np.random.default_rng(6000)
    letras = list(kit.FAMILIAS_PRUEBA)
    escenas, vistas = [], set()
    while len(escenas) < a.cantidad:
        par = todos[ids[len(escenas) % len(ids)]]
        etiqueta, obst = kit.muestrear_de_familias(rng, np.array(par["pick"]), np.array(par["place"]), letras)
        letra = etiqueta.split()[1]
        if len(obst) < 2 or not ver.resuelve(obst, par["pick"], par["place"]):
            continue
        e = escena(f"PG-{letra} {etiqueta} par={par['id']}", obst, par)
        if clave(e) in prohibidas or clave(e) in vistas:
            continue
        vistas.add(clave(e))
        escenas.append(e)
    datos = {"descripcion": "Prueba grande: escenas de las familias de prueba (nunca usadas en entrenamiento ni validación), "
                            "con pares vistos y no vistos, resolubles por RRT-Connect. Generado por "
                            "tools/generar_prueba_grande.py. Nunca se usa para elegir el mejor punto.",
             "contrato": ver.C["version"], "semilla": 6000, "familias": letras, "escenas": escenas}
    (dir_sc / "kit_prueba_grande.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False))
    print("kit_prueba_grande.yaml", len(escenas))


if __name__ == "__main__":
    main()
