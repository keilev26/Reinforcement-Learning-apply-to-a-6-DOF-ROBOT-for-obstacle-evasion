"""Escenas del contrato 3.1 en PyBullet: celda, obstáculos y efector del Magician E6.

La geometría sale de `shared_scenarios/contrato.py`, la misma expansión que usa la línea base
en MoveIt. Aquí solo se traduce cada objeto a un cuerpo de PyBullet.
"""
import sys
from pathlib import Path

import numpy as np
import pybullet as p

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared_scenarios"))
import contrato  # noqa: E402

from gym_env.robot_e6 import ModeloE6, autocolisiones, fijar_q  # noqa: E402

ESLABONES_MOVILES = ["Link1", "Link2", "Link3", "Link4", "Link5", "Link6"]


def crear_objeto(cliente: int, o: dict) -> int:
    """Cuerpo estático de PyBullet para un objeto de escena del contrato."""
    if o["forma"] == "caja":
        forma = p.createCollisionShape(p.GEOM_BOX, halfExtents=[d / 2 for d in o["dims"]],
                                       physicsClientId=cliente)
    elif o["forma"] == "cilindro":
        altura, radio = o["dims"]
        forma = p.createCollisionShape(p.GEOM_CYLINDER, radius=radio, height=altura,
                                       physicsClientId=cliente)
    else:
        forma = p.createCollisionShape(p.GEOM_SPHERE, radius=o["dims"][0], physicsClientId=cliente)
    return p.createMultiBody(0, forma, basePosition=o["pose"][:3],
                             baseOrientation=p.getQuaternionFromEuler(o["pose"][3:6]),
                             physicsClientId=cliente)


class Escena:
    """Celda base + obstáculos de una variante + efector que sigue a tool0."""

    def __init__(self, modelo: ModeloE6, C: dict | None = None):
        self.m, self.C = modelo, C or contrato.cargar()
        self.celda = [crear_objeto(modelo.cliente, o) for o in contrato.celda(self.C)]
        self.obstaculos: list[int] = []
        ef = contrato.objeto_efector(self.C)
        self._ef_offset = ef["pose"][:3]
        self.efector = crear_objeto(modelo.cliente, dict(ef, pose=[0, 0, 0, 0, 0, 0]))

    def poner_obstaculos(self, objetos: list[dict]) -> None:
        for b in self.obstaculos:
            p.removeBody(b, physicsClientId=self.m.cliente)
        self.obstaculos = [crear_objeto(self.m.cliente, o) for o in objetos]

    def fijar_q(self, q) -> None:
        """Coloca el robot y lleva el efector a su sitio sobre tool0."""
        fijar_q(self.m, q)
        pos, ori = p.getLinkState(self.m.cuerpo, self.m.tool0, computeForwardKinematics=True,
                                  physicsClientId=self.m.cliente)[4:6]
        pos_ef, _ = p.multiplyTransforms(pos, ori, self._ef_offset, [0, 0, 0, 1])
        p.resetBasePositionAndOrientation(self.efector, pos_ef, ori, physicsClientId=self.m.cliente)

    def en_colision(self, q, margen: float = 0.0) -> list[str]:
        """Contactos en la configuración q: autocolisión, robot y efector contra la escena."""
        self.fijar_q(q)
        c = self.m.cliente
        choques = [f"{a}-{b}" for a, b in autocolisiones(self.m, margen)]
        entorno = [("celda", b) for b in self.celda] + [("obstaculo", b) for b in self.obstaculos]
        for nombre in ESLABONES_MOVILES:
            idx = self.m.eslabones[nombre]
            for tipo, b in entorno:
                if p.getClosestPoints(self.m.cuerpo, b, margen, linkIndexA=idx, physicsClientId=c):
                    choques.append(f"{nombre}-{tipo}")
        for tipo, b in entorno:
            if p.getClosestPoints(self.efector, b, margen, physicsClientId=c):
                choques.append(f"efector-{tipo}")
        # El efector va pegado a Link6: se revisa contra el resto del brazo
        for nombre in ESLABONES_MOVILES[:-1]:
            if p.getClosestPoints(self.efector, self.m.cuerpo, margen,
                                  linkIndexB=self.m.eslabones[nombre], physicsClientId=c):
                choques.append(f"efector-{nombre}")
        return choques

    def ik_tcp(self, pos, rpy, semilla, intentos: int = 30, rng=None):
        """Configuración libre de colisión con el TCP en (pos, rpy), o None.

        Prueba primero desde la semilla y después desde semillas aleatorias.
        """
        rng = rng or np.random.default_rng(0)
        c = self.m.cliente
        objetivo = contrato.tool0_desde_tcp(self.C, pos, rpy)
        quat = p.getQuaternionFromEuler(rpy)
        for k in range(intentos):
            q0 = np.asarray(semilla) if k == 0 else rng.uniform(self.m.q_min * 0.6, self.m.q_max * 0.6)
            fijar_q(self.m, q0)
            q = np.array(p.calculateInverseKinematics(self.m.cuerpo, self.m.tool0, objetivo, quat,
                                                      maxNumIterations=300, residualThreshold=1e-6,
                                                      physicsClientId=c))
            if np.any(q < self.m.q_min) or np.any(q > self.m.q_max):
                continue
            fijar_q(self.m, q)
            s = p.getLinkState(self.m.cuerpo, self.m.tool0, computeForwardKinematics=True,
                               physicsClientId=c)
            d = p.getDifferenceQuaternion(s[5], quat)
            error_ang = 2 * np.arctan2(np.linalg.norm(d[:3]), abs(d[3]))
            if np.linalg.norm(np.array(s[4]) - objetivo) < 1e-3 and error_ang < 1e-2 \
                    and not self.en_colision(q):
                return q
        return None
