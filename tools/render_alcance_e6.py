import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
import video_semillas as v
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato
from gym_env.robot_e6 import fijar_q

GRANATE, AZUL, GRIS = (138, 0, 0), (30, 36, 51), (110, 116, 130)


def punteada(d, a, b, color, ancho=4, largo=14, hueco=10):
    a, b = np.array(a), np.array(b)
    n = np.linalg.norm(b - a)
    u = (b - a) / max(n, 1e-9)
    t = 0.0
    while t < n:
        d.line([tuple(a + u * t), tuple(a + u * min(t + largo, n))], fill=color, width=ancho)
        t += largo + hueco


def cota(d, a, b, color, texto, desplazamiento, fuente):
    a, b = np.array(a), np.array(b)
    d.line([tuple(a), tuple(b)], fill=color, width=5)
    u = (b - a) / max(np.linalg.norm(b - a), 1e-9)
    n = np.array([-u[1], u[0]])
    for p, s in ((a, 1), (b, -1)):
        d.polygon([tuple(p), tuple(p + s * 22 * u + 9 * n), tuple(p + s * 22 * u - 9 * n)], fill=color)
    medio = (a + b) / 2 + np.array(desplazamiento)
    caja = d.textbbox(medio, texto, font=fuente, anchor="mm")
    d.rectangle([caja[0] - 8, caja[1] - 5, caja[2] + 8, caja[3] + 5], fill=(251, 250, 247))
    d.text(medio, texto, fill=color, font=fuente, anchor="mm")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=RAIZ / "docs" / "presentacion" / "p1" / "img" / "alcance_radio_altura.png")
    ap.add_argument("--clave", default="p_pick")
    ap.add_argument("--ancho", type=int, default=1400)
    ap.add_argument("--alto", type=int, default=900)
    a = ap.parse_args()

    v.PANEL_W, v.PANEL_H = a.ancho, a.alto
    v.OJO, v.OBJETIVO = [-0.75, -0.62, 0.5], [0.0, -0.16, 0.19]
    env = EntornoE6()
    C = contrato.cargar()
    T = C["tarea_nominal"][a.clave]
    env.reset(options={"obstaculos": [], "etiqueta": "vacio"})
    q = env.esc.ik_tcp(T["pos"], T["rpy"], np.array(C["tarea_nominal"]["q_inicial_rad"]))
    fijar_q(env.m, q)
    cam = v.Camara(env.cliente)
    img = cam.imagen()
    d = ImageDraw.Draw(img)
    x, y, z = T["pos"]
    radio = float(np.hypot(x, y))
    P = cam.proyectar
    f_t, f_m = v.fuente(34, True), v.fuente(30, False)

    punteada(d, P([0, 0, 0]), P([0, 0, 0.42]), AZUL, ancho=5)
    d.text((P([0, 0, 0.42])[0] + 14, P([0, 0, 0.42])[1] - 6), "eje de J1", fill=AZUL, font=f_t, anchor="lm")
    punteada(d, P([0, 0, z]), P([x, y, z]), GRIS, ancho=3)
    punteada(d, P([x, y, 0]), P([x, y, z]), GRIS, ancho=3)
    cota(d, P([0, 0, 0.0]), P([x, y, 0.0]), GRANATE, f"radio = {radio:.2f} m", (-20, 45), f_t)
    lado = np.array([95.0, 0.0])
    base, punta = np.array(P([x, y, 0.0])), np.array(P([x, y, z]))
    for p0 in (base, punta):
        d.line([tuple(p0 + np.array([12.0, 0.0])), tuple(p0 + lado)], fill=AZUL, width=2)
    cota(d, tuple(base + lado), tuple(punta + lado), AZUL, f"altura = {z:.2f} m", (190, 0), f_t)
    px, py = P([x, y, z])
    d.ellipse([px - 13, py - 13, px + 13, py + 13], fill=GRANATE, outline=(255, 255, 255), width=3)
    d.text((px - 30, py - 46), "TCP", fill=GRANATE, font=f_t, anchor="rm")
    d.text((40, 40), "Magician E6 · posición de recogida", fill=AZUL, font=v.fuente(38, True))
    d.text((40, 90), "TCP = punto central de la herramienta", fill=GRIS, font=f_m)

    a.salida.parent.mkdir(parents=True, exist_ok=True)
    img.save(a.salida)
    env.close()
    print(a.salida)


if __name__ == "__main__":
    main()
