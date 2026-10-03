import argparse
import gzip
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from evaluation.metricas import remuestrear
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato
from gym_env.robot_e6 import RUTA_URDF

ARTICULACIONES = [f"joint{i}" for i in range(1, 7)]


def limites_urdf() -> np.ndarray:
    raiz = ET.parse(RUTA_URDF).getroot()
    por_nombre = {j.get("name"): float(j.find("limit").get("effort")) for j in raiz.findall("joint")
                  if j.find("limit") is not None}
    return np.array([por_nombre[n] for n in ARTICULACIONES])


class Dinamica:
    def __init__(self, carga_kg: float, dt: float):
        self.cl = p.connect(p.DIRECT)
        self.dt = dt
        self.cuerpo = p.loadURDF(str(RUTA_URDF), useFixedBase=True, physicsClientId=self.cl)
        self.art = [j for j in range(p.getNumJoints(self.cuerpo, physicsClientId=self.cl))
                    if p.getJointInfo(self.cuerpo, j, physicsClientId=self.cl)[2] == p.JOINT_REVOLUTE]
        masa = p.getDynamicsInfo(self.cuerpo, self.art[-1], physicsClientId=self.cl)[0]
        p.changeDynamics(self.cuerpo, self.art[-1], mass=masa + carga_kg, physicsClientId=self.cl)
        p.setGravity(0, 0, -9.81, physicsClientId=self.cl)

    def pares(self, qs) -> tuple[np.ndarray, np.ndarray]:
        qs = np.asarray(qs)
        qd = np.gradient(qs, self.dt, axis=0)
        qdd = np.gradient(qd, self.dt, axis=0)
        tau = np.array([p.calculateInverseDynamics(self.cuerpo, list(q), list(v), list(a), physicsClientId=self.cl)
                        for q, v, a in zip(qs, qd, qdd)])
        return np.abs(tau), np.abs(qdd)

    def estatico(self, q) -> np.ndarray:
        return np.abs(p.calculateInverseDynamics(self.cuerpo, list(q), [0.0] * 6, [0.0] * 6,
                                                 physicsClientId=self.cl))


def trayectorias_politica(modelo_ruta: Path):
    from stable_baselines3 import SAC
    C = contrato.cargar()
    modelo = SAC.load(modelo_ruta, device="cpu")
    env = EntornoE6()
    salida = []
    for n in C["escenarios"]:
        for etiqueta, _ in contrato.variantes(C, n):
            obs, info = env.reset(options={"escenario": n, "variante": etiqueta})
            qs, fin = [info["q"]], False
            while not fin:
                a, _ = modelo.predict(obs, deterministic=True)
                obs, _, te, tr, info = env.step(a)
                qs.append(info["q"])
                fin = te or tr
            salida.append(np.array(qs))
    return salida, env


def trayectorias_linea_base(ruta: Path, dt: float):
    salida = []
    with gzip.open(ruta, "rt") as f:
        for linea in f:
            r = json.loads(linea)
            if r["planner"] == "RRTConnect" and r["codigo"] == 1 and r["trayectoria"]:
                tr = np.array(r["trayectoria"])
                salida.append(remuestrear(tr[:, 0], tr[:, 1:], dt))
    return salida


def resumir(dinamica: Dinamica, trayectorias, limite: np.ndarray) -> dict:
    taus, accs = zip(*(dinamica.pares(t) for t in trayectorias))
    pico = np.max(np.concatenate(taus), axis=0)
    return {"trayectorias": len(trayectorias),
            "par_max_Nm": [round(float(x), 2) for x in pico],
            "fraccion_del_limite": [round(float(x), 2) for x in pico / limite],
            "aceleracion_max_rad_s2": round(float(np.max(np.concatenate(accs))), 2)}


def main():
    ap = argparse.ArgumentParser(description="Par articular que exigen las trayectorias, por dinámica inversa")
    candidatos = sorted((RAIZ / "training" / "runs").glob("sac_v1_s0_*/modelo_final.zip"))
    ap.add_argument("--modelo", type=Path, default=candidatos[-1] if candidatos else None)
    ap.add_argument("--linea-base", type=Path, default=RAIZ / "results" / "raw" / "linea_base_20260929_0025.jsonl.gz")
    ap.add_argument("--carga", type=float, default=0.75, help="masa añadida en Link6 (kg)")
    a = ap.parse_args()

    dt = contrato.cargar_metricas()["terminacion"]["periodo_control_s"]
    limite = limites_urdf()
    dinamica = Dinamica(a.carga, dt)

    politica, env = trayectorias_politica(a.modelo)
    q_pick = env.q_pick_ref
    T = env.C["tarea_nominal"]
    env.esc.poner_obstaculos([])
    q_place = env.esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], T["q_inicial_rad"])
    estatico = np.max([dinamica.estatico(q) for q in (np.zeros(6), q_pick, q_place)], axis=0)

    resultado = {
        "carga_kg": a.carga,
        "periodo_control_s": dt,
        "limite_urdf_Nm": [float(x) for x in limite],
        "politica_sac": resumir(dinamica, politica, limite),
        "rrt_connect": resumir(dinamica, trayectorias_linea_base(a.linea_base, dt), limite),
        "solo_gravedad_Nm": [round(float(x), 2) for x in estatico],
    }
    salida = RAIZ / "results" / "analisis_pares_e6.yaml"
    salida.write_text(yaml.safe_dump(resultado, allow_unicode=True, sort_keys=False))
    print(f"{'':<28}" + "".join(f"{n:>8}" for n in ("J1", "J2", "J3", "J4", "J5", "J6")))
    print(f"{'límite del URDF (N·m)':<28}" + "".join(f"{x:>8.1f}" for x in limite))
    for nombre, clave in (("política SAC, par máx", "politica_sac"), ("RRT-Connect, par máx", "rrt_connect")):
        print(f"{nombre:<28}" + "".join(f"{x:>8.2f}" for x in resultado[clave]["par_max_Nm"]))
        print(f"{'  fracción del límite':<28}" + "".join(f"{x:>8.0%}" for x in resultado[clave]["fraccion_del_limite"]))
    print(f"{'solo gravedad (N·m)':<28}" + "".join(f"{x:>8.2f}" for x in estatico))
    print(f"-> {salida}")


if __name__ == "__main__":
    main()
