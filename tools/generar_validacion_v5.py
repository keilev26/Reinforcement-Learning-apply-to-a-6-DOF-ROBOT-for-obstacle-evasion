import argparse
import sys
from pathlib import Path

import numpy as np
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env import kit
from gym_env.escena import contrato
from tools.generar_set_kit import PARES_VISTOS, Verificador, clave, escena


def main():
    ap = argparse.ArgumentParser(description="Validación v5: sorteos con pares vistos y estructuradas de las familias de entrenamiento")
    ap.add_argument("--cantidad", type=int, default=100)
    ap.add_argument("--limite", type=float, default=5.0)
    a = ap.parse_args()
    dir_sc = RAIZ / "shared_scenarios"
    ver = Verificador(a.limite)
    todos = {q["id"]: q for q in contrato.pares_kit(dir_sc / "pares_kit.yaml")}
    vistos = [todos[i] for i in PARES_VISTOS]
    ev = yaml.safe_load((dir_sc / "kit_evaluacion.yaml").read_text())
    prohibidas = {clave(e) for e in ev["escenas"]}
    base = yaml.safe_load((dir_sc / "kit_validacion_pares.yaml").read_text())["escenas"]
    rng = np.random.default_rng(5000)
    est = []
    while len(est) < a.cantidad:
        par = vistos[int(rng.integers(len(vistos)))]
        etiqueta, obst = kit.muestrear_estructurada(rng, np.array(par["pick"]), np.array(par["place"]))
        if len(obst) < 2 or not ver.resuelve(obst, par["pick"], par["place"]):
            continue
        e = escena(f"VE{len(est) + 1:03d} {etiqueta} par={par['id']}", obst, par)
        if clave(e) not in prohibidas:
            est.append(e)
    datos = {"descripcion": "Validación v5: 199 sorteos con pares vistos más escenas estructuradas de las familias de "
                            "entrenamiento (sin familias de prueba). Generado por tools/generar_validacion_v5.py. "
                            "Nunca se usa para evaluar.",
             "contrato": ver.C["version"], "semilla": 5000, "familias_prueba": list(kit.FAMILIAS_PRUEBA),
             "escenas": base + est}
    (dir_sc / "kit_validacion_v5.yaml").write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False))
    print("kit_validacion_v5.yaml", len(base), "+", len(est))


if __name__ == "__main__":
    main()
