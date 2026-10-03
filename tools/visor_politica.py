"""Visor de escenarios y de la política entrenada en PyBullet (demostración en vivo).

Recorre un conjunto de escenas con el teclado y, si se da un modelo, ejecuta la política SAC
(determinista) en cada una, a tiempo real (30 ms por paso). Con --linea-base dibuja en amarillo el
camino del TCP que planificó RRT-Connect para la MISMA escena (datos ya medidos, results/raw/),
y la política deja su camino en verde.

Conjuntos (--conjunto):
  contrato      las 19 variantes del contrato (el escenario 8 es la prueba de generalización)
  evaluacion    las 100 escenas fijas de evaluación (E001 a E100)
  entrenamiento escenas aleatorias de entrenamiento; el número de escena es la semilla

Teclas (con la ventana de PyBullet enfocada):
  n o →   escena siguiente        p o ←   escena anterior
  r       repetir la escena       espacio  pausa
  q       salir

Uso:
  .venv/bin/python tools/visor_politica.py --modelo training/runs/sac_v1_s0_20260930_0705/modelo_final.zip
  .venv/bin/python tools/visor_politica.py --modelo <zip> --conjunto evaluacion --escena E074 --linea-base
  .venv/bin/python tools/visor_politica.py --conjunto contrato          # solo ver las escenas, sin política
  .venv/bin/python tools/visor_politica.py --modelo <zip> --sin-ventana --captura /data/tmp/visor
"""
import argparse
import gzip
import json
import sys
import time
from pathlib import Path

import numpy as np
import pybullet as p

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.entorno import EntornoE6  # noqa: E402
from gym_env.escena import contrato  # noqa: E402

VERDE, AMARILLO, ROJO, BLANCO, CELESTE = (0.1, 0.7, 0.2), (0.95, 0.75, 0.0), (0.85, 0.15, 0.15), (1, 1, 1), (0.2, 0.5, 0.9)
LINEA_BASE = {"contrato": "linea_base_20260929_0025.jsonl.gz",
              "evaluacion": "linea_base_evaluacion_20260930_0648.jsonl.gz"}


def modelo_por_defecto() -> Path | None:
    cand = sorted((RAIZ / "training" / "runs").glob("sac_v1_s*_*/modelo_final.zip"))
    return cand[0] if cand else None


def lista_escenas(conjunto: str, C: dict):
    """[(etiqueta, opciones de reset)] del conjunto."""
    if conjunto == "contrato":
        return [(et, {"escenario": int(et.split()[0]), "variante": et})
                for n in C["escenarios"] for et, _ in contrato.variantes(C, n)]
    if conjunto == "evaluacion":
        return [(et, {"obstaculos": obst, "etiqueta": et}) for et, obst in contrato.escenas_evaluacion()]
    return [(f"entrenamiento #{i}", {"semilla": i}) for i in range(10_000)]


def cargar_linea_base(conjunto: str) -> dict:
    """{etiqueta: trayectoria [[t, q1..q6], ...]} del primer plan exitoso de RRT-Connect."""
    ruta = RAIZ / "results" / "raw" / LINEA_BASE.get(conjunto, "")
    if conjunto not in LINEA_BASE or not ruta.exists():
        return {}
    out = {}
    with gzip.open(ruta, "rt") as f:
        for linea in f:
            r = json.loads(linea)
            if r["planner"] == "RRTConnect" and r["codigo"] == 1 and r["variante"] not in out:
                out[r["variante"]] = r["trayectoria"]
    return out


class Visor:
    def __init__(self, a):
        self.a = a
        self.C = contrato.cargar()
        self.escenas = lista_escenas(a.conjunto, self.C)
        self.base = cargar_linea_base(a.conjunto) if a.linea_base else {}
        self.env = EntornoE6(render_mode=None if a.sin_ventana else "human")
        self.cl = self.env.cliente
        self.modelo = None
        if a.modelo:
            from stable_baselines3 import SAC
            self.modelo = SAC.load(a.modelo, device="cpu")
        self.texto = {}
        T = self.C["tarea_nominal"]
        self.pick, self.place = T["p_pick"]["pos"], T["p_place"]["pos"]
        if not a.sin_ventana:
            p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=self.cl)
            p.resetDebugVisualizerCamera(1.25, 55, -28, [0.18, -0.12, 0.08], physicsClientId=self.cl)

    # ------------------------------------------------------------------ dibujo
    def escribir(self, clave, texto, pos, color=BLANCO, tam=1.4):
        self.texto[clave] = p.addUserDebugText(texto, pos, textColorRGB=color, textSize=tam,
                                               replaceItemUniqueId=self.texto.get(clave, -1),
                                               physicsClientId=self.cl)

    def marcas(self):
        for pos, color in ((self.pick, CELESTE), (self.place, VERDE)):
            p.addUserDebugLine([pos[0] - .02, pos[1], pos[2]], [pos[0] + .02, pos[1], pos[2]], color, 4,
                               physicsClientId=self.cl)
            p.addUserDebugLine([pos[0], pos[1] - .02, pos[2]], [pos[0], pos[1] + .02, pos[2]], color, 4,
                               physicsClientId=self.cl)
            p.addUserDebugLine(pos, [pos[0], pos[1], pos[2] + .05], color, 4, physicsClientId=self.cl)
        self.escribir("pick", "RECOGER", [self.pick[0], self.pick[1], self.pick[2] + .07], CELESTE, 1.0)
        self.escribir("place", "DEPOSITAR", [self.place[0], self.place[1], self.place[2] + .07], VERDE, 1.0)

    def dibujar_linea_base(self, etiqueta):
        tray = self.base.get(etiqueta)
        if not tray:
            return
        env = self.env
        pts = []
        for fila in tray[::3] + [tray[-1]]:
            env.esc.fijar_q(fila[1:])
            pts.append(env.metricas.tcp()[0])
        env.esc.fijar_q(env.q)
        for a_, b_ in zip(pts, pts[1:]):
            p.addUserDebugLine(a_, b_, AMARILLO, 3, physicsClientId=self.cl)

    # ------------------------------------------------------------------ teclado
    def tecla(self):
        ev = p.getKeyboardEvents(physicsClientId=self.cl)
        def apretada(*codigos):
            return any(ev.get(c, 0) & p.KEY_WAS_TRIGGERED for c in codigos)
        if apretada(ord("q")):
            return "salir"
        if apretada(ord("n"), p.B3G_RIGHT_ARROW):
            return "sig"
        if apretada(ord("p"), p.B3G_LEFT_ARROW):
            return "ant"
        if apretada(ord("r")):
            return "repetir"
        if apretada(ord(" ")):
            return "pausa"
        return None

    # ------------------------------------------------------------------ un episodio
    def episodio(self, i):
        etiqueta, opc = self.escenas[i]
        env = self.env
        p.removeAllUserDebugItems(physicsClientId=self.cl)
        self.texto = {}
        if "semilla" in opc:
            obs, info = env.reset(seed=opc["semilla"])
        else:
            obs, info = env.reset(options=opc)
        self.marcas()
        self.dibujar_linea_base(etiqueta)
        n = len(self.escenas) if self.a.conjunto != "entrenamiento" else "∞"
        self.escribir("titulo", f"[{i + 1}/{n}] {env.etiqueta}", [-0.25, 0.35, 0.55], BLANCO, 1.6)
        self.escribir("ayuda", "n/p: escena   r: repetir   espacio: pausa   q: salir", [-0.25, 0.35, 0.50],
                      (0.7, 0.7, 0.7), 1.0)
        if self.base and etiqueta in self.base:
            self.escribir("leyenda", "amarillo: RRT-Connect   verde: política", [-0.25, 0.35, 0.45], AMARILLO, 1.0)

        prev, fin, pausa = env.metricas.tcp()[0], False, False
        if self.modelo is None and self.a.sin_ventana:        # prueba sin política: solo dibujar la escena
            self.resultado = ("SOLO ESCENA", {"error_pos_m": info["error_pos_m"], "pasos": 0})
            if self.a.captura:
                self.captura(i)
            return "fin"
        while not fin:
            t0 = time.perf_counter()
            k = self.tecla()
            if k in ("salir", "sig", "ant", "repetir"):
                return k
            if k == "pausa":
                pausa = not pausa
            if pausa:
                time.sleep(0.05)
                continue
            if self.modelo is None:
                time.sleep(0.2)             # sin política: solo se ve la escena
                continue
            a, _ = self.modelo.predict(obs, deterministic=True)
            obs, _, te, tr, info = env.step(a)
            fin = te or tr
            pos = env.metricas.tcp()[0]
            p.addUserDebugLine(prev, pos, VERDE, 4, physicsClientId=self.cl)
            prev = pos
            self.escribir("estado", f"paso {info['pasos']:>3}   error {info['error_pos_m'] * 1000:6.1f} mm   "
                          f"d_min {min(info['d_min_obstaculos_m'], 9.99) * 1000:6.1f} mm",
                          [-0.25, 0.35, 0.40], BLANCO, 1.2)
            resto = env.dt / self.a.velocidad - (time.perf_counter() - t0)
            if resto > 0 and not self.a.sin_ventana:
                time.sleep(resto)
        if info["exito"]:
            veredicto, color = "ÉXITO", VERDE
        elif info["colisiones"] > 0:
            veredicto, color = "COLISIÓN", ROJO
        else:
            veredicto, color = "TIEMPO AGOTADO", AMARILLO
        self.escribir("veredicto", f"{veredicto}   {info['error_pos_m'] * 1000:.1f} mm   {info['pasos']} pasos"
                      f"   {info['t_ejecucion_s']:.1f} s", [-0.25, 0.35, 0.33], color, 1.6)
        self.resultado = (veredicto, info)
        if self.a.captura:
            self.captura(i)
        return "fin"

    def captura(self, i):
        carpeta = Path(self.a.captura)
        carpeta.mkdir(parents=True, exist_ok=True)
        V = p.computeViewMatrix([0.95, -0.85, 0.65], [0.18, -0.12, 0.08], [0, 0, 1], physicsClientId=self.cl)
        P = p.computeProjectionMatrixFOV(50, 1.5, 0.05, 5, physicsClientId=self.cl)
        w, h, rgb, *_ = p.getCameraImage(900, 600, V, P, renderer=p.ER_TINY_RENDERER, physicsClientId=self.cl)
        from PIL import Image
        Image.fromarray(np.reshape(rgb, (h, w, 4))[:, :, :3].astype(np.uint8)).save(carpeta / f"escena_{i:03d}.png")

    # ------------------------------------------------------------------ bucle principal
    def correr(self):
        i = 0
        if self.a.escena:
            etiquetas = [e for e, _ in self.escenas]
            if self.a.escena.isdigit() and self.a.conjunto == "entrenamiento":
                i = int(self.a.escena)
            else:
                coinc = [k for k, e in enumerate(etiquetas) if e == self.a.escena or e.startswith(self.a.escena + " ")]
                if not coinc:
                    sys.exit(f"escena '{self.a.escena}' no existe. Ejemplos: {etiquetas[:4]}")
                i = coinc[0]
        while True:
            r = self.episodio(i)
            if self.a.sin_ventana:
                print(f"{self.escenas[i][0]:<40} {self.resultado[0]:<15} {self.resultado[1]['error_pos_m'] * 1000:7.1f} mm")
                if self.a.captura or self.a.una_vez:
                    return
            if r == "salir":
                return
            if r == "ant":
                i = (i - 1) % len(self.escenas)
            elif r == "repetir":
                pass
            elif r == "sig":
                i = (i + 1) % len(self.escenas)
            else:                            # "fin": esperar la siguiente orden o avanzar solo
                limite = time.time() + (self.a.auto if self.a.auto else 1e9)
                orden = None
                while orden is None and time.time() < limite:
                    orden = self.tecla()
                    time.sleep(0.05)
                if orden == "salir":
                    return
                i = (i - 1) % len(self.escenas) if orden == "ant" else i if orden == "repetir" \
                    else (i + 1) % len(self.escenas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", type=Path, default=None, help="modelo SAC (.zip); sin él solo se ven las escenas")
    ap.add_argument("--conjunto", choices=["contrato", "evaluacion", "entrenamiento"], default="contrato")
    ap.add_argument("--escena", default="", help="etiqueta (p. ej. E074, '5 k=2.0', 8) o, en entrenamiento, la semilla")
    ap.add_argument("--linea-base", action="store_true", help="dibujar el camino de RRT-Connect (amarillo)")
    ap.add_argument("--velocidad", type=float, default=1.0, help="1.0 = tiempo real; 2.0 = el doble de rápido")
    ap.add_argument("--auto", type=float, default=0.0, help="pasar a la siguiente escena tras N s")
    ap.add_argument("--sin-ventana", action="store_true", help="sin GUI (pruebas)")
    ap.add_argument("--captura", default="", help="carpeta donde guardar una imagen al terminar la escena")
    ap.add_argument("--una-vez", action="store_true", help="con --sin-ventana: una sola escena")
    a = ap.parse_args()
    Visor(a).correr()


if __name__ == "__main__":
    main()
