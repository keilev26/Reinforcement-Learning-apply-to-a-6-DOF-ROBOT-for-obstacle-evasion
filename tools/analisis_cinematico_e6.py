import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pybullet as p
import yaml
from matplotlib.colors import LinearSegmentedColormap

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6, fijar_q

SUPERFICIE, TINTA, TINTA_2, TENUE, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
AZUL = "#2a78d6"
RAMPA = LinearSegmentedColormap.from_list(
    "azul", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": TINTA_2,
                     "xtick.color": TENUE, "ytick.color": TENUE, "axes.titlecolor": TINTA,
                     "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE})

RPY_ABAJO = [np.pi, 0.0, 0.0]


def jacobiano_tcp(m, q, largo):
    fijar_q(m, q)
    ceros = [0.0] * 6
    jl, ja = p.calculateJacobian(m.cuerpo, m.tool0, [0, 0, largo], list(q), ceros, ceros)
    return np.vstack([np.array(jl), np.array(ja)])


def manipulabilidad(m, q, largo):
    J = jacobiano_tcp(m, q, largo)
    s = np.linalg.svd(J, compute_uv=False)
    return float(abs(np.linalg.det(J))), float(s.min())


def estilo(ax):
    ax.grid(color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def main():
    C = contrato.cargar()
    m = cargar_e6(p.connect(p.DIRECT))
    esc = Escena(m, C)
    esc.poner_obstaculos([])
    largo = C["efector"]["largo_m"]
    T = C["tarea_nominal"]
    semilla = np.array(T["q_inicial_rad"])

    radios = np.arange(0.10, 0.5001, 0.025)
    alturas = np.arange(0.02, 0.3801, 0.03)
    azimut = -np.pi / 4
    w = np.full((len(alturas), len(radios)), np.nan)
    for i, z in enumerate(alturas):
        for j, r in enumerate(radios):
            q = esc.ik_tcp([r * np.cos(azimut), r * np.sin(azimut), z], RPY_ABAJO, semilla, intentos=20)
            if q is not None:
                w[i, j] = manipulabilidad(m, q, largo)[0]
    alcanzables = np.isfinite(w)

    tarea = {}
    for k in ("p_pick", "p_place"):
        pos = T[k]["pos"]
        q = esc.ik_tcp(pos, T[k]["rpy"], semilla)
        tarea[k] = {"radio_m": float(np.hypot(pos[0], pos[1])), "altura_m": pos[2],
                    "manipulabilidad": manipulabilidad(m, q, largo)[0],
                    "sigma_min": manipulabilidad(m, q, largo)[1]}

    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    wmax = np.nanmax(w)
    im = ax.pcolormesh(radios, alturas, np.ma.masked_invalid(w / wmax), cmap=RAMPA, vmin=0, vmax=1,
                       shading="nearest", edgecolors=SUPERFICIE, linewidth=1.0)
    for k, etiqueta in (("p_pick", "p_pick"), ("p_place", "p_place")):
        ax.plot(tarea[k]["radio_m"], tarea[k]["altura_m"], "o", ms=9, mfc=SUPERFICIE, mec=TINTA, mew=2)
        ax.annotate(etiqueta, (tarea[k]["radio_m"], tarea[k]["altura_m"]), xytext=(-12, 0),
                    textcoords="offset points", color=TINTA, fontsize=9, ha="right", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc=SUPERFICIE, ec="none"))
    cb = fig.colorbar(im, ax=ax, pad=0.02)
    cb.set_label("manipulabilidad relativa |det J| / máx", color=TINTA_2)
    cb.outline.set_visible(False)
    ax.set_xlabel("radio del TCP desde el eje de J1 (m)")
    ax.set_ylabel("altura del TCP sobre la mesa (m)")
    ax.set_title("Magician E6 · alcance con herramienta hacia abajo y efector de 7 cm", loc="left",
                 fontsize=11)
    ax.text(0.0, -0.2, "Celdas en blanco: sin cinemática inversa libre de colisión con la celda.",
            transform=ax.transAxes, color=TENUE, fontsize=8)
    estilo(ax)
    fig.tight_layout()
    salida = RAIZ / "results" / "figures"
    salida.mkdir(parents=True, exist_ok=True)
    fig.savefig(salida / "1.6_alcanzabilidad_e6.png", dpi=160)
    plt.close(fig)

    q_pick = esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], semilla)
    q_place = esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], semilla)
    base = (q_pick + q_place) / 2
    barrido = np.linspace(-np.pi, np.pi, 361)

    def barrer(j):
        out = []
        for v in barrido:
            q = base.copy(); q[j] = v
            out.append(manipulabilidad(m, q, largo)[0])
        return np.array(out)

    w_j5, w_j3 = barrer(4), barrer(2)
    camino = [q_pick + (q_place - q_pick) * s for s in np.linspace(0, 1, 101)]
    w_cam = np.array([manipulabilidad(m, q, largo)[0] for q in camino])
    s_cam = np.array([manipulabilidad(m, q, largo)[1] for q in camino])
    ref = max(w_j5.max(), w_j3.max(), w_cam.max())

    fig, ejes = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, x, y, titulo, xl in (
            (ejes[0], np.degrees(barrido), w_j5 / ref, "Muñeca: barrido de J5", "J5 (°)"),
            (ejes[1], np.degrees(barrido), w_j3 / ref, "Codo: barrido de J3", "J3 (°)"),
            (ejes[2], np.linspace(0, 100, 101), w_cam / ref, "Camino directo pick → place",
             "avance (%)")):
        ax.plot(x, y, color=AZUL, lw=2)
        ax.set_title(titulo, loc="left", fontsize=10)
        ax.set_xlabel(xl)
        estilo(ax)
    ejes[0].set_ylabel("|det J| relativa")
    for x0 in (-180, 0, 180):
        ejes[0].axvline(x0, color=TENUE, lw=0.8, ls=":")
    ejes[0].text(0.5, 0.97, "J5 = 0°: J4 y J6 alineados", transform=ejes[0].transAxes, ha="center",
                 va="top", color=TINTA_2, fontsize=8,
                 bbox=dict(boxstyle="round,pad=0.2", fc=SUPERFICIE, ec="none"))
    fig.suptitle("Magician E6 · manipulabilidad en el TCP (J de 6×6)", x=0.01, ha="left", fontsize=11,
                 color=TINTA)
    fig.tight_layout()
    fig.savefig(salida / "1.7_singularidades_e6.png", dpi=160)
    plt.close(fig)

    def ceros(v):
        r = v / ref
        idx = [i for i in range(len(r)) if r[i] < 0.01
               and r[i] <= r[max(i - 1, 0)] and r[i] <= r[min(i + 1, len(r) - 1)]]
        return sorted({round(float(np.degrees(barrido[i]))) for i in idx})

    dq_max = contrato.cargar_metricas()["accion"]["delta_q_max_rad"]
    resumen = {
        "alcanzabilidad": {
            "celdas": int(alcanzables.size), "alcanzables": int(alcanzables.sum()),
            "radio_m": [float(radios[0]), float(radios[-1])], "altura_tcp_m": [float(alturas[0]), float(alturas[-1])],
            "azimut_deg": float(np.degrees(azimut)), "tarea": tarea},
        "singularidades": {
            "ceros_J5_deg": ceros(w_j5), "ceros_J3_deg": ceros(w_j3),
            "camino_directo": {"manipulabilidad_min_rel": float(w_cam.min() / ref),
                               "sigma_min_min": float(s_cam.min()),
                               "avance_del_minimo_pct": int(np.argmin(w_cam))},
            "dq_max_de_la_accion_rad": dq_max},
    }
    (RAIZ / "results" / "analisis_cinematico_e6.yaml").write_text(
        yaml.safe_dump(resumen, allow_unicode=True, sort_keys=False))
    print(yaml.safe_dump(resumen, allow_unicode=True, sort_keys=False))


if __name__ == "__main__":
    main()
