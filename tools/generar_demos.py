import argparse
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.entorno import EntornoE6
from training.entrenar_sac import cargar_config
from tools.verificar_resolubilidad import rrt_connect

CAMPOS = ("obs", "acciones", "recompensas", "obs_sig", "terminados")
ANTICIPO_RAD = 0.15


def proyectar(ruta, longitudes, q):
    mejor, avance = np.inf, 0.0
    for k in range(len(ruta) - 1):
        seg = ruta[k + 1] - ruta[k]
        largo = float(np.dot(seg, seg))
        t = 0.0 if largo < 1e-12 else float(np.clip(np.dot(q - ruta[k], seg) / largo, 0.0, 1.0))
        d = float(np.linalg.norm(q - (ruta[k] + t * seg)))
        if d < mejor:
            mejor, avance = d, longitudes[k] + t * np.sqrt(largo)
    return avance


def punto_adelante(ruta, longitudes, q, anticipo):
    objetivo = proyectar(ruta, longitudes, q) + anticipo
    k = int(np.searchsorted(longitudes, objetivo))
    if k >= len(ruta):
        return ruta[-1]
    if k == 0:
        return ruta[0]
    t = (objetivo - longitudes[k - 1]) / max(1e-9, longitudes[k] - longitudes[k - 1])
    return ruta[k - 1] + t * (ruta[k] - ruta[k - 1])


def accion(env, ruta, longitudes):
    q = env.q
    objetivo = punto_adelante(ruta, longitudes, q, ANTICIPO_RAD)
    limite = np.sqrt(2 * env.ddq_max * np.maximum(np.abs(ruta[-1] - q), 1e-6)) + 1e-4
    dq = np.clip(objetivo - q, -limite, limite)
    return np.clip(dq / env.dq_max, -1.0, 1.0)


def episodio(env, semilla, limite_rrt):
    obs, _ = env.reset(seed=semilla)
    esc, q0 = env.esc, env.q.copy()
    q1 = esc.ik_tcp(env.p_meta, env.rpy_meta, q0)
    if q1 is None:
        return None
    ruta, _ = rrt_connect(esc, q0, np.asarray(q1), limite_rrt, np.random.default_rng(semilla))
    if ruta is None:
        return None
    ruta = np.array(ruta)
    longitudes = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ruta, axis=0), axis=1))])
    filas, fin, info = [], False, {}
    while not fin:
        a = accion(env, ruta, longitudes)
        sig, r, te, tr, info = env.step(a)
        filas.append((obs, a, r, sig, float(te)))
        obs, fin = sig, te or tr
    if not info["exito"] or info["colisiones"] > 0:
        return None
    return filas


def trabajo(args):
    semillas, recompensa, limite_rrt = args
    env = EntornoE6(muestreo="kit", recompensa=recompensa)
    buenas, intentos = [], 0
    for s in semillas:
        intentos += 1
        filas = episodio(env, s, limite_rrt)
        if filas:
            buenas.append(filas)
    env.close()
    return buenas, intentos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="sac_v3")
    ap.add_argument("--episodios", type=int, default=800, help="intentos totales")
    ap.add_argument("--procesos", type=int, default=4)
    ap.add_argument("--semilla", type=int, default=100000)
    ap.add_argument("--limite-rrt", type=float, default=5.0)
    ap.add_argument("--salida", type=Path, default=RAIZ / "training" / "demos" / "kit_rrt.npz")
    a = ap.parse_args()
    recompensa = cargar_config(a.config)["entorno"]["recompensa"]
    semillas = list(range(a.semilla, a.semilla + a.episodios))
    trozos = [(semillas[i::a.procesos], recompensa, a.limite_rrt) for i in range(a.procesos)]
    t0 = time.time()
    with mp.get_context("spawn").Pool(a.procesos) as pool:
        resultados = pool.map(trabajo, trozos)
    episodios = [e for buenas, _ in resultados for e in buenas]
    intentos = sum(n for _, n in resultados)
    if not episodios:
        sys.exit("ningún episodio útil")
    filas = [f for e in episodios for f in e]
    datos = {c: np.array([f[i] for f in filas], dtype=np.float32) for i, c in enumerate(CAMPOS)}
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(a.salida, **datos)
    print(f"{len(episodios)}/{intentos} episodios útiles ({100 * len(episodios) / intentos:.0f} %), "
          f"{len(filas)} transiciones, {len(filas) / len(episodios):.0f} pasos por episodio, "
          f"{time.time() - t0:.0f} s -> {a.salida}")


if __name__ == "__main__":
    main()
