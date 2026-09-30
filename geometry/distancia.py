"""Paquete 3.11 — Distancia mínima eslabón-obstáculo.

Es el módulo que alimenta la observación del MDP (distancia y dirección por eslabón) y la métrica
M5. Mide sobre la geometría de colisión de la fuente única (`rl6gdl_e6_description`) y los objetos
del contrato, con PyBullet (GJK sobre las piezas convexas). `geometry/fcl_referencia.py` repite
el cálculo con FCL, el motor de MoveIt, para validarlo (`geometry/validar_fcl.py`).

Convenciones:
    distancia > 0   separación entre superficies (m)
    distancia <= 0  contacto o penetración
    dirección       vector unitario desde el punto más cercano del eslabón hacia el del objeto
"""
from dataclasses import dataclass

import numpy as np
import pybullet as p

# Eslabones que observa la política. Link1 queda fuera: gira sobre la base y no se acerca a los
# obstáculos del contrato (radio >= 0.13 m); base_link no se mueve.
ESLABONES_OBSERVADOS = ("Link2", "Link3", "Link4", "Link5", "Link6", "efector")

# Más allá de este alcance la distancia se satura: la política no necesita saber de obstáculos lejanos.
D_MAX = 0.20


@dataclass
class Medida:
    distancia: np.ndarray    # (n,) por eslabón observado, saturada en d_max
    direccion: np.ndarray    # (n, 3), cero si no hay nada dentro de d_max
    d_min: float             # mínimo global (m), saturado en d_max
    par_min: tuple           # (eslabón, índice del cuerpo) del mínimo, o None


class MedidorDistancias:
    """Distancias entre los eslabones observados y un conjunto de cuerpos de PyBullet.

    `eslabones` mapea nombre -> (cuerpo, índice de eslabón). El efector es un cuerpo aparte, con
    índice -1. `d_max` limita la búsqueda de getClosestPoints: por encima no se calcula nada.
    """

    def __init__(self, cliente: int, eslabones: dict[str, tuple[int, int]],
                 nombres=ESLABONES_OBSERVADOS, d_max: float = D_MAX):
        self.c, self.eslabones, self.nombres, self.d_max = cliente, eslabones, tuple(nombres), d_max

    def medir(self, cuerpos: list[int]) -> Medida:
        n = len(self.nombres)
        dist = np.full(n, self.d_max)
        dire = np.zeros((n, 3))
        par = None
        for i, nombre in enumerate(self.nombres):
            cuerpo, idx = self.eslabones[nombre]
            for b in cuerpos:
                for x in p.getClosestPoints(cuerpo, b, self.d_max, linkIndexA=idx, physicsClientId=self.c):
                    if x[8] < dist[i]:
                        dist[i] = x[8]
                        # La normal de contacto va del objeto (B) al eslabón (A): se invierte.
                        # A diferencia de restar los puntos más cercanos, vale también con
                        # penetración, cuando esa resta cambia de sentido.
                        dire[i] = -np.asarray(x[7])
                        if par is None or dist[i] < par[0]:
                            par = (dist[i], (nombre, b))
        d_min = float(dist.min())
        return Medida(dist, dire, d_min, None if par is None else par[1])


def distancia_minima(cliente: int, eslabones: dict[str, tuple[int, int]], cuerpos: list[int],
                     d_max: float = 1.0) -> float:
    """Distancia mínima entre TODOS los eslabones dados y los cuerpos (métrica M5)."""
    return MedidorDistancias(cliente, eslabones, tuple(eslabones), d_max).medir(cuerpos).d_min
