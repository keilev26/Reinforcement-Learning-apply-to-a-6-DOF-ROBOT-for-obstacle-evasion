import argparse
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "shared_scenarios"))
import contrato

RES = RAIZ / "results"
SALIDA = RES / "analisis_generalizacion"
TOLERANCIAS_M = [0.005, 0.0075, 0.010, 0.015, 0.020, 0.030]
TOL_ORI = 0.05
GRUPO_DENTRO = {1, 2, 4, 5, 6}
RADIO_TAREA_M = 0.30

SUPERFICIE, TINTA, TINTA_2, TENUE, REJILLA = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
AZUL, NARANJA, AZUL_OSCURO, AZUL_MEDIO = "#2a78d6", "#eb6834", "#184f95", "#6da7ec"
plt.rcParams.update({"font.size": 10, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": TINTA_2,
                     "xtick.color": TENUE, "ytick.color": TENUE, "axes.titlecolor": TINTA,
                     "figure.facecolor": SUPERFICIE, "axes.facecolor": SUPERFICIE})


def wilson(exitos: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    p = exitos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    mitad = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return float(centro - mitad), float(centro + mitad)


def escenas_evaluacion() -> pd.DataFrame:
    datos = yaml.safe_load((RAIZ / "shared_scenarios" / "evaluacion.yaml").read_text())
    filas = []
    for e in datos["escenas"]:
        et = e["etiqueta"]
        m = re.search(r"k=([\d.]+) d=\(([+-][\d.]+),([+-][\d.]+)\)", et)
        k, dx, dy = (float(m.group(i)) for i in (1, 2, 3))
        pose = e["obstaculos"][0]["pose"]
        filas.append({"escena": et, "forma": et.split()[1], "k": k, "dx": dx, "dy": dy,
                      "x": pose[0], "y": pose[1], "r": float(np.hypot(dx, dy)),
                      "d_arco": float(abs(np.hypot(pose[0], pose[1]) - RADIO_TAREA_M))})
    return pd.DataFrame(filas)


def episodios_detalle(modelo_ruta: Path) -> pd.DataFrame:
    from stable_baselines3 import SAC
    from gym_env.entorno import EntornoE6
    modelo = SAC.load(modelo_ruta, device="cpu")
    env = EntornoE6()
    C = contrato.cargar()
    trabajos = [("evaluacion", et, {"obstaculos": obst, "etiqueta": et})
                for et, obst in contrato.escenas_evaluacion()]
    trabajos += [("contrato", et, {"escenario": n, "variante": et})
                 for n in C["escenarios"] for et, _ in contrato.variantes(C, n)]
    filas = []
    for conjunto, etiqueta, opciones in trabajos:
        obs, info = env.reset(options=opciones)
        primera = {t: None for t in TOLERANCIAS_M}
        pos_min = pos_min_ori = np.inf
        fin = False
        while not fin:
            a, _ = modelo.predict(obs, deterministic=True)
            obs, _, te, tr, info = env.step(a)
            fin = te or tr
            ep, eo = info["error_pos_m"], info["error_ori_rad"]
            pos_min = min(pos_min, ep)
            if eo <= TOL_ORI:
                pos_min_ori = min(pos_min_ori, ep)
                for t in TOLERANCIAS_M:
                    if primera[t] is None and ep <= t:
                        primera[t] = info["pasos"]
        fila = {"conjunto": conjunto, "escena": etiqueta, "exito": bool(info["exito"]),
                "colision_paso": info["pasos"] if info["colisiones"] > 0 else np.nan,
                "pasos": info["pasos"], "pos_final_mm": info["error_pos_m"] * 1000,
                "ori_final_rad": info["error_ori_rad"], "pos_min_mm": pos_min * 1000,
                "pos_min_ori_ok_mm": pos_min_ori * 1000}
        for t in TOLERANCIAS_M:
            fila[f"entra_{t * 1000:g}mm"] = primera[t] if primera[t] is not None else np.nan
        filas.append(fila)
    env.close()
    return pd.DataFrame(filas)


def exito_con_tolerancia(det: pd.DataFrame, tol_m: float) -> pd.Series:
    entra = det[f"entra_{tol_m * 1000:g}mm"]
    return entra.notna() & (det["colision_paso"].isna() | (entra < det["colision_paso"]))


def fila_metricas(nombre: str, df: pd.DataFrame) -> dict:
    n, ok = len(df), int(df["exito"].sum())
    bajo, alto = wilson(ok, n)
    exitosos = df[df["exito"]]
    dmin = exitosos["d_min_obstaculos_m"].replace([np.inf, -np.inf], np.nan).dropna() * 1000
    colisiones = df["colisiones"].fillna(0)
    por_paso = float("nan")
    if (df["planner"] == "SAC").all():
        por_paso = float((df["t_computo_ms"] / (df["t_ejecucion_s"] / 0.03)).median())
    return {"metodo": nombre, "episodios": n, "M1_exito": ok / n, "M1_ic95_bajo": bajo, "M1_ic95_alto": alto,
            "M2_episodios_con_colision": int((colisiones > 0).sum()), "M2_entradas_en_contacto": int(colisiones.sum()),
            "M3_cart_mediana_m": exitosos["L_cart_m"].median(), "M3_art_mediana_rad": exitosos["L_art_rad"].median(),
            "M4_computo_mediana_ms": exitosos["t_computo_ms"].median(), "M4_ejecucion_mediana_s": exitosos["t_ejecucion_s"].median(),
            "M4_inferencia_por_paso_ms": por_paso,
            "M5_dmin_mediana_mm": dmin.median()}


def tabla_5_metricas() -> pd.DataFrame:
    filas = []
    ev = {s: pd.read_csv(RES / f"politica_sac_v1_acel_s{s}_1M_evaluacion.csv") for s in (0, 1)}
    rrt = pd.read_csv(RES / "linea_base_evaluacion_20260930_0648_metricas.csv")
    lazy = pd.read_csv(RES / "linea_base_evaluacion_20260930_0651_metricas.csv")
    for nombre, df in (("SAC semilla 0", ev[0]), ("SAC semilla 1", ev[1]),
                       ("RRT-Connect", rrt[rrt.planner == "RRTConnect"]), ("LazyPRM*", lazy[lazy.planner == "LazyPRMstar"])):
        filas.append({"conjunto": "evaluación (100 escenas)", **fila_metricas(nombre, df)})
    co = {s: pd.read_csv(RES / f"politica_sac_v1_acel_s{s}_1M_contrato.csv") for s in (0, 1)}
    base = pd.read_csv(RES / "linea_base_20260929_0025_metricas.csv")
    for nombre, df in (("SAC semilla 0", co[0]), ("SAC semilla 1", co[1]),
                       ("RRT-Connect", base[base.planner == "RRTConnect"]), ("LazyPRM*", base[base.planner == "LazyPRMstar"])):
        filas.append({"conjunto": "contrato (19 variantes)", **fila_metricas(nombre, df)})
    return pd.DataFrame(filas)


def exito_por_escena() -> pd.DataFrame:
    esc = escenas_evaluacion().set_index("escena")
    for s in (0, 1):
        d = pd.read_csv(RES / f"politica_sac_v1_acel_s{s}_1M_evaluacion.csv").set_index("variante")
        esc[f"s{s}"] = d["exito"].astype(float)
    rrt = pd.read_csv(RES / "linea_base_evaluacion_20260930_0648_metricas.csv")
    esc["rrt"] = rrt.groupby("variante")["exito"].mean()
    esc["politica"] = esc[["s0", "s1"]].mean(axis=1)
    return esc.reset_index()


def agrupar(esc: pd.DataFrame, columna: str, orden=None) -> pd.DataFrame:
    g = esc.groupby(columna, observed=True).agg(escenas=("escena", "count"), politica=("politica", "mean"), rrt=("rrt", "mean"))
    if orden is not None:
        g = g.reindex(orden)
    return g.reset_index()


def contrato_por_variante() -> pd.DataFrame:
    base = pd.read_csv(RES / "linea_base_20260929_0025_metricas.csv")
    base = base[base.planner == "RRTConnect"].groupby("variante")["exito"].mean()
    filas = []
    for s in (0, 1):
        d = pd.read_csv(RES / f"politica_sac_v1_acel_s{s}_1M_contrato.csv").set_index("variante")
        filas.append(d["exito"].astype(float).rename(f"s{s}"))
    df = pd.concat(filas, axis=1)
    df["rrt"] = base
    df["escenario"] = [int(v.split()[0]) for v in df.index]
    df["grupo"] = np.where(df["escenario"].isin(GRUPO_DENTRO), "dentro de la distribución", "fuera de la distribución")
    return df.reset_index()


def estilo(ax):
    ax.grid(color=REJILLA, linewidth=0.6, axis="y")
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)


def figura_por_factor(forma: pd.DataFrame, escala: pd.DataFrame, distancia: pd.DataFrame):
    fig, ejes = plt.subplots(1, 3, figsize=(11.5, 3.6), sharey=True)
    for ax, g, col, titulo in ((ejes[0], forma, "forma", "Forma del obstáculo"),
                               (ejes[1], escala, "k_bin", "Tamaño (k = escala)"),
                               (ejes[2], distancia, "d_bin", "Distancia del obstáculo al arco de la tarea")):
        x = np.arange(len(g))
        ax.plot(x, g["rrt"] * 100, "o-", color=NARANJA, lw=2, ms=7, mec=SUPERFICIE, mew=1.5, label="RRT-Connect")
        ax.plot(x, g["politica"] * 100, "o-", color=AZUL, lw=2, ms=7, mec=SUPERFICIE, mew=1.5, label="Política SAC")
        for xi, (n, pol) in enumerate(zip(g["escenas"], g["politica"])):
            ax.annotate(f"n={n}", (xi, pol * 100), xytext=(0, -15), textcoords="offset points", ha="center",
                        color=TENUE, fontsize=8)
        ax.set_xticks(x)
        ax.set_xticklabels([str(v) for v in g[col]])
        ax.set_xlim(-0.45, len(g) - 0.55)
        ax.set_title(titulo, loc="left", fontsize=10)
        ax.set_ylim(0, 105)
        estilo(ax)
    ejes[0].set_ylabel("éxito en las 100 escenas (%)")
    ejes[0].legend(frameon=False, loc="lower left", fontsize=9)
    fig.suptitle("Éxito según las características del obstáculo (política: media de 2 semillas)", x=0.01,
                 ha="left", fontsize=11, color=TINTA)
    fig.tight_layout()
    fig.savefig(RES / "figures" / "4.3_exito_por_factor.png", dpi=160)
    plt.close(fig)


def figura_mapa(esc: pd.DataFrame, T: dict):
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    estados = [(esc["politica"] == 1, AZUL_OSCURO, "resuelta en las 2 semillas"),
               ((esc["politica"] > 0) & (esc["politica"] < 1), AZUL_MEDIO, "resuelta en 1 semilla"),
               (esc["politica"] == 0, "none", "no resuelta")]
    for mascara, color, etiqueta in estados:
        sub = esc[mascara]
        if color == "none":
            ax.scatter(sub["x"], sub["y"], s=sub["k"] * 70, facecolors="none", edgecolors=TENUE, linewidths=1.4, label=etiqueta)
        else:
            ax.scatter(sub["x"], sub["y"], s=sub["k"] * 70, color=color, edgecolors=SUPERFICIE, linewidths=0.8, label=etiqueta)
    fallo = esc[esc["rrt"] < 1]
    ax.scatter(fallo["x"], fallo["y"], marker="x", s=90, color=NARANJA, linewidths=2, label="RRT-Connect falla")
    for nombre in ("p_pick", "p_place"):
        pos = T[nombre]["pos"]
        ax.plot(pos[0], pos[1], "s", color=TINTA, ms=9)
        ax.annotate(nombre, (pos[0], pos[1]), xytext=(8, 6), textcoords="offset points", color=TINTA, fontsize=9)
    ax.set_xlabel("x del obstáculo (m)")
    ax.set_ylabel("y del obstáculo (m)")
    ax.set_title("Dónde falla la política (tamaño del punto = escala k)", loc="left", fontsize=11)
    ax.set_aspect("equal")
    ax.grid(color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper left", fontsize=8.5)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    fig.savefig(RES / "figures" / "4.3_mapa_de_exito.png", dpi=160)
    plt.close(fig)


def figura_tolerancia(sens: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    for s, estilo_l in ((0, "-"), (1, "--")):
        sub = sens[sens["semilla"] == s]
        ax.plot(sub["tolerancia_mm"], sub["exito"] * 100, estilo_l, marker="o", color=AZUL, lw=2, ms=6,
                mec=SUPERFICIE, mew=1.2)
        ax.annotate(f"semilla {s}", (sub["tolerancia_mm"].iloc[-1], sub["exito"].iloc[-1] * 100),
                    xytext=(-8, 9), textcoords="offset points", ha="right", color=AZUL_OSCURO, fontsize=9)
    ax.axvline(5, color=TENUE, lw=1, ls=":")
    ax.annotate("tolerancia del contrato (5 mm)", (5, 4), xytext=(6, 0), textcoords="offset points", color=TENUE, fontsize=8)
    ax.set_xlabel("tolerancia de posición (mm), con orientación a 0.05 rad")
    ax.set_ylabel("éxito en las 100 escenas (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Cuántas escenas se resolverían con otra tolerancia", loc="left", fontsize=11)
    estilo(ax)
    fig.tight_layout()
    fig.savefig(RES / "figures" / "4.3_sensibilidad_tolerancia.png", dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Tabla de las 5 métricas y análisis de generalización (4.1 y 4.3)")
    ap.add_argument("--modelos", type=Path, nargs=2, metavar=("SEMILLA0", "SEMILLA1"), default=[
        RAIZ / "training/runs/sac_v1_s0_20260930_0705/modelo_final.zip",
        RAIZ / "training/runs/sac_v1_s1_20260930_0705/modelo_final.zip"])
    ap.add_argument("--recalcular", action="store_true", help="volver a ejecutar las políticas para el detalle por episodio")
    a = ap.parse_args()
    SALIDA.mkdir(parents=True, exist_ok=True)
    (RES / "figures").mkdir(parents=True, exist_ok=True)

    tabla = tabla_5_metricas()
    tabla.to_csv(SALIDA / "tabla_5_metricas.csv", index=False)

    esc = exito_por_escena()
    esc["k_bin"] = pd.cut(esc["k"], [0.59, 0.9, 1.2, 1.5, 1.8, 2.01], labels=["0.6-0.9", "0.9-1.2", "1.2-1.5", "1.5-1.8", "1.8-2.0"])
    esc["r_bin"] = pd.cut(esc["r"], [-0.001, 0.03, 0.06, 0.09, 0.2], labels=["0-3 cm", "3-6 cm", "6-9 cm", ">9 cm"])
    esc["d_bin"] = pd.cut(esc["d_arco"], [-0.001, 0.025, 0.05, 0.075, 0.2], labels=["0-2.5 cm", "2.5-5 cm", "5-7.5 cm", ">7.5 cm"])
    forma = agrupar(esc, "forma", ["prisma", "cilindro", "esfera"])
    escala = agrupar(esc, "k_bin")
    distancia = agrupar(esc, "d_bin")
    desplazamiento = agrupar(esc, "r_bin")
    for nombre, g in (("por_forma", forma), ("por_escala", escala), ("por_distancia_al_arco", distancia),
                      ("por_desplazamiento", desplazamiento)):
        g.to_csv(SALIDA / f"{nombre}.csv", index=False)
    esc.to_csv(SALIDA / "exito_por_escena.csv", index=False)

    acuerdo = pd.Series({"resuelta en las 2 semillas": int((esc["politica"] == 1).sum()),
                         "resuelta en 1 semilla": int(((esc["politica"] > 0) & (esc["politica"] < 1)).sum()),
                         "no resuelta": int((esc["politica"] == 0).sum())}, name="escenas")
    acuerdo.to_csv(SALIDA / "acuerdo_semillas.csv")

    var = contrato_por_variante()
    var.to_csv(SALIDA / "contrato_por_variante.csv", index=False)
    grupo = var.groupby("grupo").agg(variantes=("variante", "count"), s0=("s0", "mean"), s1=("s1", "mean"), rrt=("rrt", "mean"))
    grupo.to_csv(SALIDA / "contrato_por_grupo.csv")

    figura_por_factor(forma, escala, distancia)
    figura_mapa(esc, yaml.safe_load((RAIZ / "shared_scenarios" / "escenarios.yaml").read_text())["tarea_nominal"])

    detalles = {}
    for s, ruta in enumerate(a.modelos):
        cache = SALIDA / f"detalle_semilla{s}.csv"
        if a.recalcular or not cache.exists():
            episodios_detalle(ruta).to_csv(cache, index=False)
        detalles[s] = pd.read_csv(cache)
    filas, fallos = [], []
    for s, det in detalles.items():
        ev = det[det["conjunto"] == "evaluacion"]
        real = float(ev["exito"].mean())
        con_5 = float(exito_con_tolerancia(ev, 0.005).mean())
        if abs(real - con_5) > 1e-9:
            print(f"AVISO semilla {s}: éxito real {real:.2f} distinto del recalculado a 5 mm {con_5:.2f}")
        for t in TOLERANCIAS_M:
            filas.append({"semilla": s, "tolerancia_mm": t * 1000, "exito": float(exito_con_tolerancia(ev, t).mean())})
        malos = ev[~ev["exito"]]
        fallos.append({"semilla": s, "fallos": len(malos), "por_colision": int(malos["colision_paso"].notna().sum()),
                       "por_tiempo": int(malos["colision_paso"].isna().sum()),
                       "casi_exito_sin_choque_10mm": int(((malos["pos_min_ori_ok_mm"] <= 10) & malos["colision_paso"].isna()).sum()),
                       "dentro_de_30mm_con_orientacion": int((malos["pos_min_ori_ok_mm"] <= 30).sum()),
                       "nunca_cerca_mas_de_100mm": int((malos["pos_min_mm"] > 100).sum()),
                       "mediana_pos_min_mm": float(malos["pos_min_mm"].median())})
    sens = pd.DataFrame(filas)
    sens.to_csv(SALIDA / "sensibilidad_tolerancia.csv", index=False)
    pd.DataFrame(fallos).to_csv(SALIDA / "fallos.csv", index=False)
    figura_tolerancia(sens)

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print(tabla.round(3).to_string(index=False), "\n")
    for nombre, g in (("forma", forma), ("escala", escala), ("distancia al arco", distancia), ("desplazamiento", desplazamiento)):
        print(f"por {nombre}:\n{g.round(3).to_string(index=False)}\n")
    print(acuerdo.to_string(), "\n")
    print(grupo.round(3).to_string(), "\n")
    print(sens.pivot(index="tolerancia_mm", columns="semilla", values="exito").round(3).to_string(), "\n")
    print(pd.DataFrame(fallos).to_string(index=False))


if __name__ == "__main__":
    main()
