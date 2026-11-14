import argparse
import sys
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env import kit
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6
from tools.verificar_resolubilidad import rrt_connect

PARES_VISTOS = list(kit.PARES_VISTOS)
PARES_NO_VISTOS = list(kit.PARES_NO_VISTOS)


class Verificador:
    def __init__(self, limite_s: float):
        self.C = contrato.cargar()
        self.esc = Escena(cargar_e6(p.connect(p.DIRECT)), self.C)
        self.limite = limite_s

    def resuelve(self, obst, pick, place) -> bool:
        T = self.C["tarea_nominal"]
        self.esc.poner_obstaculos(obst)
        q0 = self.esc.ik_tcp(pick, T["p_pick"]["rpy"], T["q_inicial_rad"])
        q1 = self.esc.ik_tcp(place, T["p_place"]["rpy"], T["q_inicial_rad"])
        if q0 is None or q1 is None:
            return False
        ruta, _ = rrt_connect(self.esc, np.asarray(q0), np.asarray(q1), self.limite, np.random.default_rng(0))
        return ruta is not None


def redondear(obst):
    return [{**o, "dims": [round(float(v), 6) for v in o["dims"]], "pose": [round(float(v), 6) for v in o["pose"]]}
            for o in obst]


def escena(etiqueta, obst, par=None):
    e = {"etiqueta": etiqueta}
    if par:
        e["par"] = {"id": par["id"], "pick": [round(float(v), 5) for v in par["pick"]],
                    "place": [round(float(v), 5) for v in par["place"]]}
    e["obstaculos"] = redondear(obst)
    return e


def clave(e):
    return tuple((o["forma"], tuple(round(d, 4) for d in o["dims"]), tuple(round(v, 3) for v in o["pose"][:3]))
                 for o in e["obstaculos"]) + ((e["par"]["id"],) if "par" in e else ())


def sorteadas(ver, rng, cantidad, prefijo, pares):
    salida = []
    while len(salida) < cantidad:
        par = pares[int(rng.integers(len(pares)))] if pares else None
        pick = par["pick"] if par else contrato.cargar()["tarea_nominal"]["p_pick"]["pos"]
        place = par["place"] if par else contrato.cargar()["tarea_nominal"]["p_place"]["pos"]
        etiqueta, obst = kit.muestrear(rng, np.array(pick), np.array(place))
        if not ver.resuelve(obst, pick, place):
            continue
        n = len(salida) + 1
        sufijo = f" par={par['id']}" if par else ""
        salida.append(escena(f"{prefijo}{n:03d} {etiqueta}{sufijo}", obst, par))
    return salida


def main():
    ap = argparse.ArgumentParser(description="Genera los conjuntos de evaluación y validación con el kit de obstáculos")
    ap.add_argument("--pares", type=Path, default=RAIZ / "shared_scenarios" / "pares_kit.yaml")
    ap.add_argument("--limite", type=float, default=5.0)
    ap.add_argument("--salida", type=Path, default=RAIZ / "shared_scenarios")
    a = ap.parse_args()
    ver = Verificador(a.limite)
    todos = {q["id"]: q for q in contrato.pares_kit(a.pares)}
    vistos = [todos[i] for i in PARES_VISTOS]
    no_vistos = [todos[i] for i in PARES_NO_VISTOS]
    T = ver.C["tarea_nominal"]

    rng = np.random.default_rng(4000)
    escenas = []
    for letra, titulo, piezas in kit.COMBINACIONES + kit.COMBINACIONES_2 + kit.COMBINACIONES_3:
        obst = [kit.objeto_kit(i, pz) for i, pz in enumerate(piezas)]
        if ver.resuelve(obst, T["p_pick"]["pos"], T["p_place"]["pos"]):
            escenas.append(escena(f"S-{letra} {titulo} par=N0", obst, todos["N0"]))
        for grupo in (vistos[1:], no_vistos):
            for k in rng.permutation(len(grupo)):
                par = grupo[int(k)]
                if ver.resuelve(obst, par["pick"], par["place"]):
                    escenas.append(escena(f"SP-{letra} {titulo} par={par['id']}", obst, par))
                    break
    n_estructuradas = len(escenas)
    escenas += sorteadas(ver, rng, 80, "R", None)
    escenas += sorteadas(ver, rng, 25, "RPv", vistos)
    escenas += sorteadas(ver, rng, 25, "RPn", no_vistos)
    evaluacion = {"descripcion": "Conjunto de evaluación del kit de obstáculos: combinaciones estructuradas (S, SP) y "
                  "sorteos (R, RPv con pares vistos en el entrenamiento, RPn con pares no vistos). Generado por "
                  "tools/generar_set_kit.py: no editar a mano. Nunca se usa para elegir el mejor punto.",
                  "contrato": ver.C["version"], "semilla": 4000, "estructuradas": n_estructuradas,
                  "pares_vistos": PARES_VISTOS, "pares_no_vistos": PARES_NO_VISTOS, "escenas": escenas}
    (a.salida / "kit_evaluacion.yaml").write_text(yaml.safe_dump(evaluacion, allow_unicode=True, sort_keys=False))
    claves_eval = {clave(e) for e in escenas}

    for semilla, nombre, pares in ((3000, "kit_validacion.yaml", None), (3001, "kit_validacion_pares.yaml", vistos)):
        rng = np.random.default_rng(semilla)
        val = sorteadas(ver, rng, 200, "V", pares)
        val = [e for e in val if clave(e) not in claves_eval]
        datos = {"descripcion": "Validación del kit de obstáculos para elegir el mejor punto (sorteos"
                 + (" con los pares vistos" if pares else " con el par nominal") + "). Generado por tools/generar_set_kit.py. "
                 "Nunca se usa para evaluar.", "contrato": ver.C["version"], "semilla": semilla, "escenas": val}
        (a.salida / nombre).write_text(yaml.safe_dump(datos, allow_unicode=True, sort_keys=False))
        print(nombre, len(val), flush=True)
    print("kit_evaluacion.yaml", len(escenas), "estructuradas", n_estructuradas)


if __name__ == "__main__":
    main()
