import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pybullet as p
import yaml

from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6, fijar_q


def angulo(qa, qb) -> float:
    d = p.getDifferenceQuaternion(qa, qb)
    return float(2 * np.arctan2(np.linalg.norm(d[:3]), abs(d[3])))


def dims_de(o: dict) -> list[float]:
    return list(o["dims"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("datos_ros", type=Path)
    ap.add_argument("mundo_sdf", type=Path)
    a = ap.parse_args()
    R = json.loads(a.datos_ros.read_text())
    C = contrato.cargar()
    variantes = {et: o for n in C["escenarios"] for et, o in contrato.variantes(C, n)}
    objetos = contrato.celda(C) + variantes[R["variante"]]

    m = cargar_e6(p.connect(p.DIRECT))
    esc = Escena(m, C)
    esc.poner_obstaculos(variantes[R["variante"]])
    informe = {"variante": R["variante"]}

    lim = R["limites_velocidad"]
    informe["limites_velocidad_max_dif_rad_s"] = float(max(
        abs(v - lim[f"joint{i + 1}"]) for i, v in enumerate(m.v_max)))

    e_pos, e_ang = [], []
    for reg in R["fk"]:
        fijar_q(m, reg["q"])
        for nombre, (pos, quat) in reg["poses"].items():
            s = p.getLinkState(m.cuerpo, m.eslabones[nombre], computeForwardKinematics=True)
            e_pos.append(np.linalg.norm(np.subtract(s[4], pos)))
            e_ang.append(angulo(s[5], quat))
    informe["fk_moveit"] = {"configuraciones": len(R["fk"]), "err_pos_max_m": float(max(e_pos)),
                            "err_ang_max_rad": float(max(e_ang))}

    e_pos, e_ang, seguim = [], [], []
    for reg in R["gazebo"]:
        fijar_q(m, reg["q_gazebo"])
        seguim.append(float(np.max(np.abs(np.subtract(reg["q_gazebo"], reg["q_objetivo"])))))
        for nombre, (pos, rpy) in reg["poses_gz"].items():
            s = p.getLinkState(m.cuerpo, m.eslabones[nombre], computeForwardKinematics=True)
            e_pos.append(np.linalg.norm(np.subtract(s[4], pos)))
            e_ang.append(angulo(s[5], p.getQuaternionFromEuler(rpy)))
    informe["fk_gazebo"] = {"configuraciones": len(R["gazebo"]), "err_pos_max_m": float(max(e_pos)),
                            "err_ang_max_rad": float(max(e_ang)),
                            "desvio_articular_max_rad": float(max(seguim))}

    margen = R["margen_planificacion_m"]
    por_id = {o["id"]: o for o in objetos}
    difs = {"pybullet": [], "moveit": [], "gazebo_sdf": []}
    for o, b in zip(objetos, esc.celda + esc.obstaculos):
        forma = p.getCollisionShapeData(b, -1)[0]
        pos, quat = p.getBasePositionAndOrientation(b)
        tipo, dim = forma[2], forma[3]
        if tipo == p.GEOM_BOX:
            d = list(dim)
        elif tipo == p.GEOM_CYLINDER:
            d = [dim[0], dim[1]]
        else:
            d = [dim[0]]
        difs["pybullet"].append(max(np.max(np.abs(np.subtract(d, dims_de(o)))),
                                    np.linalg.norm(np.subtract(pos, o["pose"][:3])),
                                    angulo(quat, p.getQuaternionFromEuler(o["pose"][3:6]))))
    for mo in R["escena"]:
        o = por_id[mo["id"]]
        if o["forma"] == "caja":
            nominal = [v - 2 * margen for v in mo["dims"]]
        elif o["forma"] == "cilindro":
            nominal = [mo["dims"][0] - 2 * margen, mo["dims"][1] - margen]
        else:
            nominal = [mo["dims"][0] - margen]
        difs["moveit"].append(max(np.max(np.abs(np.subtract(nominal, dims_de(o)))),
                                  np.linalg.norm(np.subtract(mo["pos"], o["pose"][:3])),
                                  angulo(mo["quat"], p.getQuaternionFromEuler(o["pose"][3:6]))))
    mundo = ET.parse(a.mundo_sdf).getroot().find("world")
    for mod in mundo.findall("model"):
        o = por_id[mod.get("name")]
        pose = [float(v) for v in mod.find("pose").text.split()]
        g = mod.find("link/collision/geometry")
        if g.find("box") is not None:
            d = [float(v) for v in g.find("box/size").text.split()]
        elif g.find("cylinder") is not None:
            d = [float(g.find("cylinder/length").text), float(g.find("cylinder/radius").text)]
        else:
            d = [float(g.find("sphere/radius").text)]
        difs["gazebo_sdf"].append(max(np.max(np.abs(np.subtract(d, dims_de(o)))),
                                      np.linalg.norm(np.subtract(pose[:3], o["pose"][:3])),
                                      angulo(p.getQuaternionFromEuler(pose[3:6]),
                                             p.getQuaternionFromEuler(o["pose"][3:6]))))
    informe["escena_objetos"] = len(objetos)
    informe["escena_max_dif_vs_contrato"] = {k: float(max(v)) for k, v in difs.items()}
    informe["escena_objetos_por_motor"] = {k: len(v) for k, v in difs.items()}
    informe["geometria_robot_pybullet_vs_fcl"] = "error máx. 1.14 mm (paquete 3.11)"

    salida = a.datos_ros.parent / f"equivalencia_escenario_{R['variante'].replace(' ', '_')}.yaml"
    salida.write_text(yaml.safe_dump(informe, allow_unicode=True, sort_keys=False))
    print(yaml.safe_dump(informe, allow_unicode=True, sort_keys=False))
    print(f"-> {salida}")


if __name__ == "__main__":
    main()
