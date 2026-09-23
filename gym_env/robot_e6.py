"""Carga del DOBOT Magician E6 en PyBullet desde la fuente única `rl6gdl_e6_description`.

El URDF, las mallas y la lista de pares excluidos de colisión son los mismos que usarán MoveIt y
Gazebo. Este módulo no define geometría propia: si algo del robot tiene que cambiar, se cambia en
`tools/gen_modelo_e6.py` y se regenera el paquete.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

PAQUETE = Path(__file__).resolve().parents[1] / "ros2_ws" / "src" / "rl6gdl_e6_description"
RUTA_URDF = PAQUETE / "urdf" / "magician_e6.urdf"
RUTA_ACM = PAQUETE / "config" / "colisiones_permitidas.yaml"


@dataclass(frozen=True)
class ModeloE6:
    cuerpo: int
    cliente: int
    articulaciones: tuple[int, ...]     # índices PyBullet de joint1..joint6
    eslabones: dict[str, int]           # nombre -> índice PyBullet (base_link = -1)
    q_min: np.ndarray                   # rad
    q_max: np.ndarray                   # rad
    v_max: np.ndarray                   # rad/s
    pares_autocolision: tuple[tuple[str, str], ...]  # pares que SÍ se evalúan

    @property
    def tool0(self) -> int:
        return self.eslabones["tool0"]


def pares_excluidos() -> set[frozenset[str]]:
    datos = yaml.safe_load(RUTA_ACM.read_text())
    return {frozenset(x["par"]) for x in datos["pares_excluidos"]}


def cargar_e6(cliente: int, posicion_base=(0.0, 0.0, 0.0)) -> ModeloE6:
    """Carga el robot con base fija y aplica la matriz de colisiones permitidas del paquete."""
    cuerpo = p.loadURDF(str(RUTA_URDF), basePosition=posicion_base, useFixedBase=True,
                        flags=p.URDF_USE_SELF_COLLISION, physicsClientId=cliente)
    eslabones, articulaciones = {"base_link": -1}, []
    for j in range(p.getNumJoints(cuerpo, physicsClientId=cliente)):
        info = p.getJointInfo(cuerpo, j, physicsClientId=cliente)
        eslabones[info[12].decode()] = j
        if info[2] == p.JOINT_REVOLUTE:
            articulaciones.append(j)
    info = [p.getJointInfo(cuerpo, j, physicsClientId=cliente) for j in articulaciones]

    excluidos = pares_excluidos()
    con_colision = [n for n in eslabones
                    if p.getCollisionShapeData(cuerpo, eslabones[n], physicsClientId=cliente)]
    pares = []
    for i, a in enumerate(con_colision):
        for b in con_colision[i + 1:]:
            if frozenset((a, b)) in excluidos:
                p.setCollisionFilterPair(cuerpo, cuerpo, eslabones[a], eslabones[b], 0,
                                         physicsClientId=cliente)
            else:
                pares.append((a, b))

    return ModeloE6(cuerpo=cuerpo, cliente=cliente, articulaciones=tuple(articulaciones),
                    eslabones=eslabones,
                    q_min=np.array([x[8] for x in info]), q_max=np.array([x[9] for x in info]),
                    v_max=np.array([x[11] for x in info]),
                    pares_autocolision=tuple(pares))


def fijar_q(modelo: ModeloE6, q) -> None:
    """Coloca el robot en la configuración articular q (rad), sin simular dinámica."""
    for j, v in zip(modelo.articulaciones, q):
        p.resetJointState(modelo.cuerpo, j, float(v), physicsClientId=modelo.cliente)


def autocolisiones(modelo: ModeloE6, margen: float = 0.0) -> list[tuple[str, str]]:
    """Pares de eslabones no excluidos a una distancia <= margen (m) en la configuración actual.

    `getClosestPoints` ignora los filtros de colisión, por eso se recorre la lista explícita de
    pares evaluables en lugar de consultar los contactos del motor.
    """
    return [(a, b) for a, b in modelo.pares_autocolision
            if p.getClosestPoints(modelo.cuerpo, modelo.cuerpo, margen,
                                  modelo.eslabones[a], modelo.eslabones[b],
                                  physicsClientId=modelo.cliente)]
