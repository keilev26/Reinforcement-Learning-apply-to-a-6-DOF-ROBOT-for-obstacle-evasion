import numpy as np


def recta_con_frenado(env, q_objetivo, q, dq_prev) -> np.ndarray:
    e = np.asarray(q_objetivo, float) - np.asarray(q, float)
    dist = float(np.max(np.abs(e)))
    if dist < 1e-9:
        return np.zeros(6)
    direccion = e / dist
    v_prev = float(np.max(np.abs(dq_prev)))
    v = min(env.dq_max, np.sqrt(2 * env.ddq_max * dist), dist, v_prev + env.ddq_max)
    return np.clip(direccion * v / env.dq_max, -1.0, 1.0)
