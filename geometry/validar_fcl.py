import argparse

import numpy as np
import pybullet as p

from geometry.fcl_referencia import ReferenciaFCL
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import RUTA_URDF, cargar_e6

ESLABONES = ("Link1", "Link2", "Link3", "Link4", "Link5", "Link6")
BANDA_M = 0.002


def comparar(esc: Escena, ref: ReferenciaFCL, objetos: list[dict], cuerpos: list[int]) -> list[tuple]:
    c, m = esc.m.cliente, esc.m
    filas = []
    fuentes = [(n, m.cuerpo, m.eslabones[n]) for n in ESLABONES] + [("efector", esc.efector, -1)]
    for nombre, cuerpo, idx in fuentes:
        if nombre == "efector":
            pos, quat = p.getBasePositionAndOrientation(cuerpo, physicsClientId=c)
            ef = contrato.objeto_efector(esc.C)
            a = [ReferenciaFCL.objeto_primitivo(ef, pos, quat)]
        else:
            s = p.getLinkState(cuerpo, idx, computeForwardKinematics=True, physicsClientId=c)
            a = ref.objetos_eslabon(nombre, s[4], s[5])
        for o, b in zip(objetos, cuerpos):
            r = p.getClosestPoints(cuerpo, b, 0.5, linkIndexA=idx, physicsClientId=c)
            d_pb = min((x[8] for x in r), default=np.inf)
            d_fcl, contacto = ReferenciaFCL.distancia(a, [ReferenciaFCL.objeto_primitivo(o)])
            filas.append((nombre, o["id"], d_pb, d_fcl, contacto))
    return filas


def validar(perturbadas: int = 3, semilla: int = 0, escenarios=range(1, 9)) -> np.ndarray:
    rng = np.random.default_rng(semilla)
    C = contrato.cargar()
    m = cargar_e6(p.connect(p.DIRECT))
    esc, ref = Escena(m, C), ReferenciaFCL(RUTA_URDF)
    T = C["tarea_nominal"]
    esc.poner_obstaculos([])
    qa = esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], T["q_inicial_rad"])
    qb = esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], T["q_inicial_rad"])
    celda = contrato.celda(C)
    filas = []
    for n in escenarios:
        for _, obst in contrato.variantes(C, n):
            esc.poner_obstaculos(obst)
            objetos, cuerpos = celda + obst, esc.celda + esc.obstaculos
            for i in range(0, 101, 5):
                base = qa + (qb - qa) * i / 100
                for k in range(perturbadas + 1):
                    q = base if k == 0 else np.clip(base + rng.normal(0, 0.25, 6), m.q_min, m.q_max)
                    esc.fijar_q(q)
                    filas += comparar(esc, ref, objetos, cuerpos)
    return np.array(filas, dtype=object)


def informe(filas: np.ndarray) -> dict:
    d_pb, d_fcl = filas[:, 2].astype(float), filas[:, 3].astype(float)
    contacto_fcl = filas[:, 4].astype(bool)
    contacto_pb = d_pb <= 0
    separados = ~contacto_fcl & ~contacto_pb & (d_pb < 0.5)
    err = np.abs(d_pb[separados] - d_fcl[separados])
    discrepa = contacto_pb != contacto_fcl
    return {
        "pares": len(filas),
        "separados_comparados": int(separados.sum()),
        "error_medio_mm": float(err.mean() * 1000),
        "error_p99_mm": float(np.percentile(err, 99) * 1000),
        "error_max_mm": float(err.max() * 1000),
        "contactos_fcl": int(contacto_fcl.sum()),
        "contactos_pybullet": int(contacto_pb.sum()),
        "discrepancias_contacto": int(discrepa.sum()),
        "discrepancias_fuera_de_banda": int((discrepa & (np.abs(d_pb) > BANDA_M)).sum()),
        "prof_max_discrepancia_mm": float(np.abs(d_pb[discrepa]).max() * 1000) if discrepa.any() else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perturbadas", type=int, default=3)
    ap.add_argument("--semilla", type=int, default=0)
    a = ap.parse_args()
    filas = validar(a.perturbadas, a.semilla)
    r = informe(filas)
    for k, v in r.items():
        print(f"{k:<32}{v:.3f}" if isinstance(v, float) else f"{k:<32}{v}")
    print(f"\n{'elemento':<10}{'separados':>11}{'err medio mm':>14}{'err máx mm':>12}{'discrep.':>10}")
    for e in list(ESLABONES) + ["efector"]:
        s = filas[filas[:, 0] == e]
        d_pb, d_fcl, cf = s[:, 2].astype(float), s[:, 3].astype(float), s[:, 4].astype(bool)
        sep = ~cf & (d_pb > 0) & (d_pb < 0.5)
        err = np.abs(d_pb[sep] - d_fcl[sep]) * 1000
        print(f"{e:<10}{sep.sum():>11}{err.mean():>14.3f}{err.max():>12.3f}{int(((d_pb <= 0) != cf).sum()):>10}")


if __name__ == "__main__":
    main()
