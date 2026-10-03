from dataclasses import dataclass

import numpy as np
import pybullet as p

ESLABONES_OBSERVADOS = ("Link2", "Link3", "Link4", "Link5", "Link6", "efector")

D_MAX = 0.20


@dataclass
class Medida:
    distancia: np.ndarray
    direccion: np.ndarray
    d_min: float
    par_min: tuple


class MedidorDistancias:

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
                        dire[i] = -np.asarray(x[7])
                        if par is None or dist[i] < par[0]:
                            par = (dist[i], (nombre, b))
        d_min = float(dist.min())
        return Medida(dist, dire, d_min, None if par is None else par[1])


def distancia_minima(cliente: int, eslabones: dict[str, tuple[int, int]], cuerpos: list[int],
                     d_max: float = 1.0) -> float:
    return MedidorDistancias(cliente, eslabones, tuple(eslabones), d_max).medir(cuerpos).d_min
