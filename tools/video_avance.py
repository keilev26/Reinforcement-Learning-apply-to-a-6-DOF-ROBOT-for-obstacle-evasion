import argparse
import csv
import io
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pybullet as p
from PIL import Image, ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato
from tools.verificar_resolubilidad import rrt_connect
from tools.video_semillas import (AMBAR, CELESTE, ESTELA, FONDO, FPS, ROJO, TENUE, TINTA, VERDE, fuente,
                                  veredicto)

ANCHO, ALTO, CABECERA, PIE = 1920, 1080, 130, 120
PANEL_W, PANEL_H = ANCHO, ALTO - CABECERA - PIE
OJO, OBJETIVO, UP = [0.95, -0.85, 0.65], [0.18, -0.12, 0.08], [0, 0, 1]
AMARILLO = (214, 160, 0)
CORRIDAS = RAIZ / "training" / "runs"


class Camara:
    def __init__(self, cliente: int):
        self.cl = cliente
        self.V = p.computeViewMatrix(OJO, OBJETIVO, UP, physicsClientId=cliente)
        self.P = p.computeProjectionMatrixFOV(48, PANEL_W / PANEL_H, 0.05, 5, physicsClientId=cliente)
        self.M = np.array(self.P).reshape(4, 4).T @ np.array(self.V).reshape(4, 4).T

    def imagen(self) -> Image.Image:
        w, h, rgb, *_ = p.getCameraImage(PANEL_W, PANEL_H, self.V, self.P, renderer=p.ER_TINY_RENDERER,
                                         physicsClientId=self.cl)
        return Image.fromarray(np.reshape(rgb, (h, w, 4))[:, :, :3].astype(np.uint8))

    def proyectar(self, punto) -> tuple[float, float]:
        c = self.M @ np.array([punto[0], punto[1], punto[2], 1.0])
        return (c[0] / c[3] * 0.5 + 0.5) * PANEL_W, (1 - (c[1] / c[3] * 0.5 + 0.5)) * PANEL_H


class Video:
    def __init__(self, salida: Path):
        salida.parent.mkdir(parents=True, exist_ok=True)
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                    "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                                    "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", str(salida)],
                                   stdin=subprocess.PIPE)

    def cuadro(self, img: Image.Image, repeticiones: int = 1):
        datos = img.convert("RGB").tobytes()
        for _ in range(repeticiones):
            self.ff.stdin.write(datos)

    def cerrar(self):
        self.ff.stdin.close()
        self.ff.wait()


def lienzo() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (ANCHO, ALTO), FONDO)
    return img, ImageDraw.Draw(img)


def tarjeta_titulo(video: Video, titulo: str, sub: str, pie: str, segundos: float):
    img, d = lienzo()
    d.text((120, 380), titulo, fill=TINTA, font=fuente(110, True))
    d.text((124, 540), sub, fill=TENUE, font=fuente(44))
    d.text((124, 900), pie, fill=TENUE, font=fuente(32))
    video.cuadro(img, int(segundos * FPS))


def tarjeta_lista(video: Video, titulo: str, filas: list[tuple[str, str, tuple]], segundos: float):
    img, d = lienzo()
    d.text((80, 50), titulo, fill=TINTA, font=fuente(64, True))
    y = 220
    for etiqueta, texto, color in filas:
        d.ellipse([90, y + 14, 120, y + 44], fill=color)
        d.text((150, y), etiqueta, fill=TINTA, font=fuente(46, True))
        d.text((150, y + 58), texto, fill=TENUE, font=fuente(34))
        y += 150
    video.cuadro(img, int(segundos * FPS))


def leer_validacion(ruta: Path):
    with open(ruta) as f:
        filas = list(csv.DictReader(f))
    return np.array([float(r["pasos"]) for r in filas]), np.array([float(r["exito"]) for r in filas])


def tarjeta_curva(video: Video, segundos: float):
    series = [("sac_v2 semilla 0", "sac_v2_s0", "#2e5a9c"), ("sac_v2 semilla 1", "sac_v2_s1", "#6a9bd8"),
              ("sac_v2 semilla 2", "sac_v2_s2", "#9dc3e6"), ("control sin castigo", "sac_v1_5m_s0", "#1a8c3c")]
    fig, ax = plt.subplots(figsize=(19.2, 8.2), dpi=100)
    for nombre, prefijo, color in series:
        carpeta = sorted(CORRIDAS.glob(f"{prefijo}_20261028_1753"))[-1]
        x, y = leer_validacion(carpeta / "validacion.csv")
        ax.plot(x / 1e6, y, color=color, lw=3, label=nombre)
    ax.axhline(0.987, color="#cc2626", ls="--", lw=2, label="RRT-Connect (0.987)")
    ax.axhline(0.66, color="#888888", ls=":", lw=2, label="sac_v1 a 1 M (0.66)")
    ax.set_xlabel("millones de pasos de entrenamiento", fontsize=20)
    ax.set_ylabel("éxito en 200 escenas de validación", fontsize=20)
    ax.set_ylim(0, 1.02)
    ax.tick_params(labelsize=18)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=20, loc="lower right")
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#fcfcfb")
    plt.close(fig)
    grafica = Image.open(buf).convert("RGB")
    img, d = lienzo()
    d.text((80, 30), "El éxito sube al entrenar más pasos", fill=TINTA, font=fuente(60, True))
    img.paste(grafica.resize((ANCHO, ALTO - 140)), (0, 140))
    video.cuadro(img, int(segundos * FPS))


def tarjeta_barras(video: Video, segundos: float):
    nombres = ["sac_v1\n1 M pasos", "sac_v2\n4.6 M (3 semillas)", "control sin castigo\n4.6 M (1 semilla)",
               "RRT-Connect"]
    valores = [0.66, 0.917, 0.96, 0.987]
    colores = ["#888888", "#2e5a9c", "#1a8c3c", "#cc2626"]
    fig, ax = plt.subplots(figsize=(19.2, 8.2), dpi=100)
    barras = ax.bar(nombres, valores, color=colores, width=0.55)
    for b, v in zip(barras, valores):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.3f}", ha="center", fontsize=30, fontweight="bold")
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("éxito en 100 escenas de evaluación", fontsize=20)
    ax.tick_params(labelsize=20)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor="#fcfcfb")
    plt.close(fig)
    grafica = Image.open(buf).convert("RGB")
    img, d = lienzo()
    d.text((80, 30), "Resultado en 100 escenas fijas", fill=TINTA, font=fuente(60, True))
    img.paste(grafica.resize((ANCHO, ALTO - 140)), (0, 140))
    video.cuadro(img, int(segundos * FPS))


def componer(panel: Image.Image, titulo: str, sub: str, estado: str, resultado: tuple | None):
    img, d = lienzo()
    d.text((48, 22), titulo, fill=TINTA, font=fuente(50, True))
    d.text((50, 88), sub, fill=TENUE, font=fuente(28))
    img.paste(panel, (0, CABECERA))
    d.text((48, CABECERA + PANEL_H + 30), estado, fill=TINTA, font=fuente(36))
    if resultado:
        texto, color = resultado
        d.text((ANCHO - 560, CABECERA + PANEL_H + 24), texto, fill=color, font=fuente(48, True))
    return img


def marcas_sobre(d: ImageDraw.ImageDraw, cam: Camara, marcas):
    for nombre, pos, color in marcas:
        x, y = cam.proyectar(pos)
        d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=color, width=3)
        d.text((x + 12, y - 10), nombre, fill=color, font=fuente(20, True))


def pintar(cam: Camara, trayectorias, marcas) -> Image.Image:
    img = cam.imagen()
    d = ImageDraw.Draw(img)
    for pts3, color in trayectorias:
        pts = [cam.proyectar(q) for q in pts3]
        if len(pts) > 1:
            d.line(pts, fill=color, width=5)
    marcas_sobre(d, cam, marcas)
    return img


def clip(video, env, cam, modelo, etiqueta, obst, titulo, sub, marcas, con_rrt, pausa):
    obs, info = env.reset(options={"obstaculos": obst, "etiqueta": etiqueta})
    q0 = env.q.copy()
    tray, fin = [env.metricas.tcp()[0]], False
    while True:
        panel = pintar(cam, [(tray, ESTELA)], marcas)
        estado = (f"paso {info['pasos']:>3} / {env.pasos_max}     error {info['error_pos_m'] * 1000:6.1f} mm"
                  f"     d_min {min(info['d_min_obstaculos_m'], 9.99) * 1000:6.1f} mm")
        res = veredicto(info) if fin else None
        video.cuadro(componer(panel, titulo, sub, estado, res))
        if fin:
            break
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
        tray.append(env.metricas.tcp()[0])
    ultimo = componer(pintar(cam, [(tray, ESTELA)], marcas), titulo, sub, estado, veredicto(info))
    video.cuadro(ultimo, int(pausa * FPS))
    if not con_rrt:
        return
    T = contrato.cargar()["tarea_nominal"]
    esc = env.esc
    q1 = esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], q0)
    ruta, t_plan = rrt_connect(esc, q0, np.asarray(q1), 30.0, np.random.default_rng(0))
    sub2 = "RRT-Connect (propio, en amarillo): "
    if ruta is None:
        video.cuadro(componer(pintar(cam, [(tray, ESTELA)], marcas), titulo, sub2 + "sin solución", "", None),
                     int(pausa * FPS))
        return
    cuadros = []
    for a_, b_ in zip(ruta, ruta[1:]):
        n = max(1, int(np.ceil(np.max(np.abs(b_ - a_)) / env.dq_max)))
        cuadros += [a_ + (b_ - a_) * k / n for k in range(1, n + 1)]
    esc.fijar_q(q0)
    traza = [env.metricas.tcp()[0]]
    paso = max(1, len(cuadros) // 330)
    for i, q in enumerate(cuadros):
        esc.fijar_q(q)
        traza.append(env.metricas.tcp()[0])
        if i % paso:
            continue
        estado = f"plan en {t_plan * 1000:.0f} ms     {len(cuadros)} pasos     paso {i + 1}"
        video.cuadro(componer(pintar(cam, [(tray, ESTELA), (traza, AMARILLO)], marcas), titulo, sub2 + "llega", estado,
                              None))
    final = componer(pintar(cam, [(tray, ESTELA), (traza, AMARILLO)], marcas), titulo, sub2 + "llega",
                     f"plan en {t_plan * 1000:.0f} ms     {len(cuadros)} pasos", ("ÉXITO", VERDE))
    video.cuadro(final, int(pausa * FPS))


def buscar(conjunto_archivo: Path | None, prefijo: str):
    for etiqueta, obst in (contrato.escenas_evaluacion(conjunto_archivo) if conjunto_archivo else contrato.escenas_evaluacion()):
        if etiqueta.startswith(prefijo):
            return etiqueta, obst
    sys.exit(f"escena {prefijo} no encontrada")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=RAIZ / "results" / "avance_entrenamiento.mp4")
    ap.add_argument("--modelo", type=Path, default=CORRIDAS / "sac_v1_5m_s0_20261028_1753" / "mejor.zip")
    ap.add_argument("--pausa", type=float, default=1.5)
    a = ap.parse_args()

    from stable_baselines3 import SAC
    modelo = SAC.load(a.modelo, device="cpu")
    demo = RAIZ / "tools" / "escenas_demo"
    casos = [
        (None, "E016", "Escena de evaluación E016", "Un obstáculo, como en el entrenamiento", False),
        (demo / "dispersos.yaml", "D3", "Cuatro obstáculos dispersos", "Escena nueva: el entrenamiento solo usa uno", False),
        (demo / "dificiles.yaml", "R6", "Barra horizontal baja", "Escena nueva fuera de distribución", False),
        (demo / "lados.yaml", "L3", "Muro de 1.60 m", "La política choca; RRT-Connect lo resuelve rodeando por el lado de la base", True),
    ]

    video = Video(a.salida)
    env = EntornoE6()
    cam = Camara(env.cliente)
    T = contrato.cargar()["tarea_nominal"]
    marcas = [("RECOGER", T["p_pick"]["pos"], CELESTE), ("DEPOSITAR", T["p_place"]["pos"], VERDE)]
    try:
        tarjeta_titulo(video, "Avance entrenamiento", "SAC frente a RRT-Connect · DOBOT Magician E6 · simulación",
                       "Proyecto mecatrónico MT818 · Semana 10 · 2026-10-31", 3.0)
        tarjeta_lista(video, "Qué se hizo", [
            ("Castigo por quedarse quieto", "Nueva recompensa sac_v2, probada contra un control sin castigo", AMBAR),
            ("5 veces más pasos", "≈ 4.6 M de pasos, 4 corridas en paralelo durante ≈ 17.5 h", VERDE),
            ("Análisis de fallos", "Fallan los obstáculos grandes y los escenarios fuera de distribución", ROJO),
            ("Escenas nuevas", "Varios obstáculos, varillas, rejas y muros de hasta 1.60 m", CELESTE),
        ], 6.0)
        tarjeta_curva(video, 6.0)
        tarjeta_barras(video, 6.0)
        for archivo, prefijo, titulo, sub, con_rrt in casos:
            etiqueta, obst = buscar(archivo, prefijo)
            print(etiqueta, flush=True)
            clip(video, env, cam, modelo, etiqueta, obst, titulo, sub, marcas, con_rrt, a.pausa)
        tarjeta_lista(video, "Lo que sigue", [
            ("Set nuevo de obstáculos y de evaluación", "Más obstáculos por escena, muros, trampas, ≈ 200 escenas", CELESTE),
            ("5 semillas", "Falta el control con las semillas 1 a 4", AMBAR),
            ("Entrenamiento final de ≈ 40 h", "Con el set nuevo; luego repetir métricas y línea base", VERDE),
            ("Electrónica y actas", "Atrasadas: sin evidencia en el repositorio", ROJO),
        ], 6.0)
    finally:
        video.cerrar()
        env.close()
    print(f"-> {a.salida}")


if __name__ == "__main__":
    main()
