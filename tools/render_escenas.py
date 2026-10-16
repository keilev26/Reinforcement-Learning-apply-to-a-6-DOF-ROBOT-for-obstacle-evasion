import argparse
import sys
from pathlib import Path

from PIL import ImageDraw

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
import video_semillas as v
from gym_env.entorno import EntornoE6
from gym_env.escena import contrato

ESCENAS = {"escena_1.png": (1, 0), "escena_2.png": (2, 0), "escena_3.png": (3, 0), "escena_7.png": (7, 1),
           "escena_8.png": (8, 0)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", type=Path, default=RAIZ / "docs" / "informe" / "img")
    ap.add_argument("--ancho", type=int, default=1280)
    ap.add_argument("--alto", type=int, default=860)
    a = ap.parse_args()

    v.PANEL_W, v.PANEL_H = a.ancho, a.alto
    v.OJO, v.OBJETIVO = [0.05, -1.0, 0.85], [0.25, -0.1, 0.12]
    a.salida.mkdir(parents=True, exist_ok=True)
    env = EntornoE6()
    C = contrato.cargar()
    cam = v.Camara(env.cliente)
    T = C["tarea_nominal"]
    marcas = [("RECOGER", T["p_pick"]["pos"], v.CELESTE), ("DEPOSITAR", T["p_place"]["pos"], v.VERDE)]
    for nombre, (escenario, indice) in ESCENAS.items():
        etiqueta, obst = contrato.variantes(C, escenario)[indice]
        env.reset(options={"obstaculos": obst, "etiqueta": etiqueta})
        img = cam.imagen()
        d = ImageDraw.Draw(img)
        for texto, pos, color in marcas:
            x, y = cam.proyectar(pos)
            d.ellipse([x - 12, y - 12, x + 12, y + 12], outline=color, width=4)
            d.text((x + 16, y - 12), texto, fill=color, font=v.fuente(26, True))
        img.save(a.salida / nombre)
        print(a.salida / nombre)
    env.close()


if __name__ == "__main__":
    main()
