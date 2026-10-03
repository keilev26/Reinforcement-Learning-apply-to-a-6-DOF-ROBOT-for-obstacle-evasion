from dataclasses import dataclass, field

import numpy as np
import pybullet as p

from geometry.distancia import MedidorDistancias


@dataclass
class ContadorMetricas:
    escena: object
    medidor_obst: MedidorDistancias
    subpasos: int
    histeresis_m: float
    largo_efector_m: float
    colisiones: int = 0
    L_art: float = 0.0
    L_cart: float = 0.0
    d_min_obst: float = np.inf
    choco: bool = False
    _activos: set = field(default_factory=set)
    _pos_tcp: np.ndarray | None = None

    def reiniciar(self, q0) -> None:
        self.colisiones, self.L_art, self.L_cart = 0, 0.0, 0.0
        self.d_min_obst, self.choco, self._activos = np.inf, False, set()
        self.escena.fijar_q(q0)
        self._pos_tcp = self.tcp()[0]

    def tcp(self):
        m = self.escena.m
        pos, quat = p.getLinkState(m.cuerpo, m.tool0, computeForwardKinematics=True,
                                   physicsClientId=m.cliente)[4:6]
        z = np.array(p.getMatrixFromQuaternion(quat)).reshape(3, 3)[:, 2]
        return np.array(pos) + z * self.largo_efector_m, np.array(quat)

    def paso(self, q_ant, q_nuevo) -> bool:
        q_ant, q_nuevo = np.asarray(q_ant, float), np.asarray(q_nuevo, float)
        dq = q_nuevo - q_ant
        hubo = False
        for k in range(1, self.subpasos + 1):
            self.escena.fijar_q(q_ant + dq * k / self.subpasos)
            contactos = set(self.escena.en_colision())
            self.colisiones += len(contactos - self._activos)
            hubo |= bool(contactos)
            if self._activos:
                cerca = set(self.escena.en_colision(margen=self.histeresis_m))
                self._activos = (self._activos | contactos) & cerca
            else:
                self._activos = contactos
            if self.escena.obstaculos:
                self.d_min_obst = min(self.d_min_obst, self.medidor_obst.medir(self.escena.obstaculos).d_min)
        self.choco |= hubo
        self.L_art += float(np.linalg.norm(dq))
        pos = self.tcp()[0]
        self.L_cart += float(np.linalg.norm(pos - self._pos_tcp))
        self._pos_tcp = pos
        return hubo


def remuestrear(tiempos, qs, periodo: float) -> np.ndarray:
    tiempos, qs = np.asarray(tiempos, float), np.asarray(qs, float)
    t = np.arange(0.0, tiempos[-1] + 1e-9, periodo)
    if t[-1] < tiempos[-1]:
        t = np.append(t, tiempos[-1])
    return np.stack([np.interp(t, tiempos, qs[:, j]) for j in range(qs.shape[1])], axis=1)


def error_meta(pos, quat, p_meta, quat_meta) -> tuple[float, float]:
    d = p.getDifferenceQuaternion(quat, quat_meta)
    ang = 2 * np.arctan2(np.linalg.norm(d[:3]), abs(d[3]))
    return float(np.linalg.norm(np.asarray(p_meta) - pos)), float(ang)
