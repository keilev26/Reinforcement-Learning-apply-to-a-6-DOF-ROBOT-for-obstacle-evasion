import xml.etree.ElementTree as ET
from pathlib import Path

import fcl
import numpy as np
import pybullet as p
import trimesh


def _transformacion(pos, quat_xyzw) -> fcl.Transform:
    x, y, z, w = quat_xyzw
    return fcl.Transform(np.array([w, x, y, z]), np.asarray(pos, dtype=float))


def _bvh(malla: trimesh.Trimesh) -> fcl.BVHModel:
    m = fcl.BVHModel()
    m.beginModel(len(malla.vertices), len(malla.faces))
    m.addSubModel(np.asarray(malla.vertices, dtype=float), np.asarray(malla.faces, dtype=np.int32))
    m.endModel()
    return m


def geometria_primitiva(o: dict):
    if o["forma"] == "caja":
        return fcl.Box(*o["dims"])
    if o["forma"] == "cilindro":
        altura, radio = o["dims"]
        return fcl.Cylinder(radio, altura)
    return fcl.Sphere(o["dims"][0])


class ReferenciaFCL:
    def __init__(self, ruta_urdf: Path):
        raiz = ET.parse(ruta_urdf).getroot()
        paquete = Path(ruta_urdf).resolve().parents[1]
        self.piezas: dict[str, list[fcl.BVHModel]] = {}
        for link in raiz.findall("link"):
            piezas = []
            for col in link.findall("collision"):
                uri = col.find("geometry/mesh").get("filename")
                ruta = paquete / uri.split("/", 3)[3]
                piezas.append(_bvh(trimesh.load(ruta)))
            if piezas:
                self.piezas[link.get("name")] = piezas

    def objetos_eslabon(self, nombre: str, pos, quat) -> list[fcl.CollisionObject]:
        tf = _transformacion(pos, quat)
        return [fcl.CollisionObject(g, tf) for g in self.piezas[nombre]]

    @staticmethod
    def objeto_primitivo(o: dict, pos=None, quat=None) -> fcl.CollisionObject:
        if pos is None:
            pos, quat = o["pose"][:3], p.getQuaternionFromEuler(o["pose"][3:6])
        return fcl.CollisionObject(geometria_primitiva(o), _transformacion(pos, quat))

    @staticmethod
    def distancia(a: list[fcl.CollisionObject], b: list[fcl.CollisionObject]) -> tuple[float, bool]:
        d, contacto = np.inf, False
        for oa in a:
            for ob in b:
                if fcl.collide(oa, ob, fcl.CollisionRequest(), fcl.CollisionResult()):
                    contacto = True
                r = fcl.DistanceResult()
                d = min(d, fcl.distance(oa, ob, fcl.DistanceRequest(), r))
        return d, contacto
