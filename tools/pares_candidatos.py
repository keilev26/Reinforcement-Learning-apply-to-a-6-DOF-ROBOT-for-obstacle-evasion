import argparse
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pybullet as p
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.entorno import EntornoE6
from tools.verificar_resolubilidad import rrt_connect

RPY = [3.1416, 0.0, 0.0]
Z_PICK, Z_PLACE = 0.05, 0.10
PARES = [
    ("N0", (0, -300), (300, 0)), ("N1", (-60, -300), (300, 0)), ("N2", (60, -300), (300, 0)),
    ("N3", (0, -250), (300, 0)), ("N4", (0, -350), (300, 0)), ("N5", (0, -300), (300, -60)),
    ("N6", (0, -300), (300, 60)), ("N7", (0, -300), (250, 0)), ("N8", (0, -300), (350, 0)),
    ("N9", (-60, -340), (340, 60)), ("N10", (60, -260), (260, -60)),
]
ESCENAS = "AEKMNQRV"


def jacobiana(m, q):
    n = len(q)
    lin, ang = p.calculateJacobian(m.cuerpo, m.tool0, [0, 0, 0], list(q), [0.0] * n, [0.0] * n, physicsClientId=m.cliente)
    s = np.linalg.svd(np.vstack([np.array(lin), np.array(ang)]), compute_uv=False)
    return float(s[-1]), float(s[0] / s[-1])


def evaluar_par(env, esc, par, semilla):
    _, pick, place = par
    q_pick = esc.ik_tcp([pick[0] / 1000, pick[1] / 1000, Z_PICK], RPY, semilla)
    q_place = None if q_pick is None else esc.ik_tcp([place[0] / 1000, place[1] / 1000, Z_PLACE], RPY, q_pick)
    return q_pick, q_place


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", type=Path, default=RAIZ / "tools" / "escenas_demo" / "kit.yaml")
    ap.add_argument("--limite", type=float, default=8.0)
    ap.add_argument("--figura", type=Path, default=RAIZ / "docs" / "semana-10" / "kit-obstaculos" / "08_pares_candidatos.png")
    ap.add_argument("--salida", type=Path, default=RAIZ / "shared_scenarios" / "pares_kit.yaml")
    a = ap.parse_args()

    env = EntornoE6()
    env.reset(options={"obstaculos": [], "etiqueta": "vacia"})
    esc, m = env.esc, env.esc.m
    escenas = {e["etiqueta"][0]: e["obstaculos"] for e in yaml.safe_load(a.kit.read_text())["escenas"]}
    filas, salida = [], []
    for par in PARES:
        esc.poner_obstaculos([])
        q_pick, q_place = evaluar_par(env, esc, par, env.q_pick_ref)
        fila = {"id": par[0], "pick": par[1], "place": par[2],
                "L_mm": round(float(np.hypot(par[2][0] - par[1][0], par[2][1] - par[1][1])), 0)}
        if q_pick is None or q_place is None:
            fila.update(ik=False)
            filas.append(fila)
            continue
        margen = min(float(np.min(np.minimum(q - m.q_min, m.q_max - q))) for q in (q_pick, q_place))
        sv = [jacobiana(m, q) for q in (q_pick, q_place)]
        directa = sum(1 for t in np.linspace(0, 1, 60) if esc.en_colision(q_pick + (q_place - q_pick) * t))
        fila.update(ik=True, margen_limites_deg=round(float(np.degrees(margen)), 1),
                    sigma_min=round(min(s[0] for s in sv), 3), cond_max=round(max(s[1] for s in sv), 1),
                    recta_libre=directa == 0, escenas={})
        for letra in ESCENAS:
            esc.poner_obstaculos(escenas[letra])
            qa, qb = evaluar_par(env, esc, par, env.q_pick_ref)
            if qa is None or qb is None:
                fila["escenas"][letra] = "sin IK"
                continue
            ruta, t = rrt_connect(esc, qa, qb, a.limite, np.random.default_rng(0))
            fila["escenas"][letra] = "ok" if ruta is not None else "sin ruta"
        filas.append(fila)
        salida.append({"id": par[0], "pick": {"pos": [par[1][0] / 1000, par[1][1] / 1000, Z_PICK], "rpy": RPY},
                       "place": {"pos": [par[2][0] / 1000, par[2][1] / 1000, Z_PLACE], "rpy": RPY}})
        print(fila, flush=True)

    a.salida.write_text(yaml.safe_dump({"descripcion": "Pares recoger/depositar candidatos. Generado por tools/pares_candidatos.py",
                                        "pares": salida}, sort_keys=False))
    fig, ax = plt.subplots(figsize=(11, 9), dpi=110)
    ax.add_patch(plt.Rectangle((-600, -500), 1200, 1000, fc="#c9a96b", ec="#7a6030"))
    ax.add_patch(plt.Rectangle((-100, -425), 200, 250, fc="#2e9a48", alpha=0.8))
    ax.add_patch(plt.Rectangle((380, -250), 300, 500, fc="#354052", alpha=0.85))
    ax.add_patch(plt.Circle((0, 0), 450, fill=False, ec="#cc2626", lw=2))
    ax.plot([0], [0], "k^", ms=12)
    ax.text(20, 20, "robot", fontsize=11)
    ax.text(380 + 30, 0, "CNC", color="white", fontsize=14)
    ax.text(-90, -415, "bandeja", color="white", fontsize=11)
    for f in filas:
        ok = f.get("ik")
        color = "#1f5fbf" if ok else "#999999"
        ax.plot([f["pick"][0], f["place"][0]], [f["pick"][1], f["place"][1]], "-", color="#555555", lw=0.8, alpha=0.5)
        ax.plot(*f["pick"], "o", color=color, ms=9)
        ax.plot(*f["place"], "s", color="#1a8c3c" if ok else "#999999", ms=9)
        ax.text(f["pick"][0] + 8, f["pick"][1] - 18, f["id"], fontsize=10, color=color)
        ax.text(f["place"][0] + 8, f["place"][1] + 8, f["id"], fontsize=10, color="#1a8c3c" if ok else "#999999")
    ax.set_xlim(-620, 720)
    ax.set_ylim(-520, 520)
    ax.set_aspect("equal")
    ax.set_title("Pares recoger (círculo azul) y depositar (cuadrado verde), mm", fontsize=15)
    a.figura.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.figura, facecolor="white", bbox_inches="tight")
    print(a.salida)


if __name__ == "__main__":
    main()
