"""Controladores de referencia para probar el entorno (no son métodos del experimento).

`recta_con_frenado` sigue la recta articular hacia una configuración con perfil trapezoidal:
acelera y frena dentro de los mismos límites que el entorno (velocidad y aceleración), de modo que
llega sin pasarse. Todas las articulaciones escalan juntas, así el camino es la recta en el
espacio articular.
"""
import numpy as np


def recta_con_frenado(env, q_objetivo, q, dq_prev) -> np.ndarray:
    """Acción en [-1, 1]^6 para avanzar por la recta articular de q a q_objetivo."""
    e = np.asarray(q_objetivo, float) - np.asarray(q, float)
    dist = float(np.max(np.abs(e)))
    if dist < 1e-9:
        return np.zeros(6)
    direccion = e / dist                          # la articulación más lejana avanza 1 por unidad
    v_prev = float(np.max(np.abs(dq_prev)))
    # Velocidad (rad/paso de la articulación más lejana): tope, frenado a tiempo y rampa de subida
    v = min(env.dq_max, np.sqrt(2 * env.ddq_max * dist), dist, v_prev + env.ddq_max)
    return np.clip(direccion * v / env.dq_max, -1.0, 1.0)
