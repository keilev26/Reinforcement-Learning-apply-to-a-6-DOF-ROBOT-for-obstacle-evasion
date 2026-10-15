import argparse
import subprocess
import sys
from pathlib import Path

import numpy as np
import pybullet as p
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato

ANCHO, ALTO, CABECERA, PIE = 1920, 1080, 150, 170
PANEL_W, PANEL_H = ANCHO // 3, ALTO - CABECERA - PIE
FONDO, TINTA, TENUE = (252, 252, 251), (11, 11, 11), (82, 81, 78)
VERDE, ROJO, AMBAR, CELESTE = (26, 140, 60), (204, 38, 38), (200, 140, 0), (42, 120, 214)
ESTELA = (235, 104, 52)
OJO, OBJETIVO, UP = [0.95, -0.85, 0.65], [0.18, -0.12, 0.08], [0, 0, 1]
FPS = 33


def fuente(tam: int, negrita: bool = False) -> ImageFont.FreeTypeFont:
    ruta = font_manager.findfont(font_manager.FontProperties(family="DejaVu Sans", weight="bold" if negrita else "normal"))
    return ImageFont.truetype(ruta, tam)


def carpeta_semilla(semilla: int) -> Path:
    cand = sorted((RAIZ / "training" / "runs").glob(f"sac_v1_s{semilla}_*/modelo_1000000.zip"))
    if not cand:
        sys.exit(f"no hay corrida completa de sac_v1 con semilla {semilla}")
    return cand[-1].parent


def buscar_escena(prefijo: str):
    for etiqueta, obst in contrato.escenas_evaluacion():
        if etiqueta.startswith(prefijo):
            return etiqueta, obst
    sys.exit(f"escena '{prefijo}' no existe en evaluacion.yaml")


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


def episodio(env, cam, modelo, etiqueta, obst, marcas):
    obs, info = env.reset(options={"obstaculos": obst, "etiqueta": etiqueta})
    tray, cuadros, fin = [env.metricas.tcp()[0]], [], False
    while True:
        img = cam.imagen()
        d = ImageDraw.Draw(img)
        pts = [cam.proyectar(q) for q in tray]
        if len(pts) > 1:
            d.line(pts, fill=ESTELA, width=4)
        for nombre, pos, color in marcas:
            x, y = cam.proyectar(pos)
            d.ellipse([x - 9, y - 9, x + 9, y + 9], outline=color, width=3)
            d.text((x + 12, y - 10), nombre, fill=color, font=fuente(20, True))
        cuadros.append((img, dict(info), fin))
        if fin:
            return cuadros
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
        tray.append(env.metricas.tcp()[0])


def veredicto(info: dict) -> tuple[str, tuple]:
    if info["exito"]:
        return "ÉXITO", VERDE
    if info["colisiones"] > 0:
        return "COLISIÓN", ROJO
    return "TIEMPO AGOTADO", AMBAR


def componer(paneles, semillas, pasos_entrenamiento, etiqueta, k, n_max):
    lienzo = Image.new("RGB", (ANCHO, ALTO), FONDO)
    d = ImageDraw.Draw(lienzo)
    d.text((48, 28), f"Política SAC tras {pasos_entrenamiento:,} pasos de entrenamiento".replace(",", " "),
           fill=TINTA, font=fuente(52, True))
    d.text((48, 96), f"Misma escena en las tres semillas: {etiqueta}", fill=TENUE, font=fuente(30))
    for i, (img, info, fin) in enumerate(paneles):
        x0 = i * PANEL_W
        lienzo.paste(img, (x0, CABECERA))
        d.rectangle([x0, CABECERA, x0 + PANEL_W - 1, CABECERA + PANEL_H - 1], outline=(195, 194, 183), width=2)
        d.text((x0 + 24, CABECERA + 14), f"Semilla {semillas[i]}", fill=TINTA, font=fuente(40, True))
        y = CABECERA + PANEL_H + 18
        d.text((x0 + 24, y), f"paso {info['pasos']:>3} / {n_max}", fill=TENUE, font=fuente(30))
        d.text((x0 + 24, y + 42), f"error {info['error_pos_m'] * 1000:6.1f} mm", fill=TINTA, font=fuente(30))
        if fin:
            texto, color = veredicto(info)
            d.text((x0 + 24, y + 90), texto, fill=color, font=fuente(40, True))
    return lienzo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--escena", default="E016")
    ap.add_argument("--puntos", type=int, nargs="+", default=[100000, 300000, 600000, 1000000])
    ap.add_argument("--semillas", type=int, nargs=3, default=[0, 1, 2])
    ap.add_argument("--salida", type=Path, default=RAIZ / "results" / "video_semillas.mp4")
    ap.add_argument("--pausa", type=float, default=1.2)
    a = ap.parse_args()

    from stable_baselines3 import SAC
    etiqueta, obst = buscar_escena(a.escena)
    carpetas = [carpeta_semilla(s) for s in a.semillas]
    env = EntornoE6()
    cam = Camara(env.cliente)
    C = contrato.cargar()
    T = C["tarea_nominal"]
    marcas = [("RECOGER", T["p_pick"]["pos"], CELESTE), ("DEPOSITAR", T["p_place"]["pos"], VERDE)]
    n_max = env.pasos_max

    a.salida.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{ANCHO}x{ALTO}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "20", "-pix_fmt", "yuv420p", str(a.salida)], stdin=subprocess.PIPE)
    try:
        for pasos in a.puntos:
            tandas = []
            for c in carpetas:
                modelo = SAC.load(c / f"modelo_{pasos}.zip", device="cpu")
                tandas.append(episodio(env, cam, modelo, etiqueta, obst, marcas))
                print(f"{pasos}: {c.name} {len(tandas[-1])} cuadros {veredicto(tandas[-1][-1][1])[0]}", flush=True)
            largo = max(len(t) for t in tandas) + int(a.pausa * FPS)
            for i in range(largo):
                paneles = [t[min(i, len(t) - 1)] for t in tandas]
                ff.stdin.write(componer(paneles, a.semillas, pasos, etiqueta, None, n_max).tobytes())
    finally:
        ff.stdin.close()
        ff.wait()
        env.close()
    print(f"-> {a.salida}")


if __name__ == "__main__":
    main()
