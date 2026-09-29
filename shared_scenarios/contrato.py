"""Lectura del contrato de escenarios (paquete 3.1): la MISMA expansión para PyBullet y MoveIt.

Ningún pipeline interpreta `escenarios.yaml` por su cuenta: ambos llaman a este módulo, que solo
depende de PyYAML y de la biblioteca estándar (lo importan el `.venv` y el Python de ROS 2).

Cada objeto de escena es un dict con:
    id     identificador único en la escena
    forma  "caja" | "cilindro" | "esfera"
    dims   caja: [x, y, z]; cilindro: [altura, radio]; esfera: [radio]   (convención de MoveIt)
    pose   [x, y, z, roll, pitch, yaw] del centro geométrico, en el marco base_link
"""
import math
from pathlib import Path

import yaml

RUTA = Path(__file__).resolve().parent / "escenarios.yaml"
RUTA_METRICAS = Path(__file__).resolve().parent / "metricas.yaml"


def cargar(ruta=RUTA) -> dict:
    return yaml.safe_load(Path(ruta).read_text())


def cargar_metricas(ruta=RUTA_METRICAS) -> dict:
    return yaml.safe_load(Path(ruta).read_text())


def objeto(C: dict, id_: str, componente: str, pose, escala=1.0) -> dict:
    info = C["biblioteca"][componente]
    k = escala if isinstance(escala, list) else [escala] * 3
    if "dim" in info:
        return dict(id=id_, forma="caja", dims=[d * e for d, e in zip(info["dim"], k)], pose=list(pose))
    if componente == "cilindro":
        return dict(id=id_, forma="cilindro", dims=[info["altura"] * k[2], info["radio"] * k[0]],
                    pose=list(pose))
    if componente == "esfera":
        return dict(id=id_, forma="esfera", dims=[info["radio"] * k[0]], pose=list(pose))
    raise ValueError(f"componente sin geometría conocida: {componente}")


def _objetos(C: dict, lista: list) -> list[dict]:
    return [objeto(C, f"o{i}_{o['componente']}", o["componente"], o["pose"], o.get("escala", 1.0))
            for i, o in enumerate(lista)]


def celda(C: dict) -> list[dict]:
    return [objeto(C, c["componente"], c["componente"], c["pose"]) for c in C["celda_base"]]


def variantes(C: dict, n: int) -> list[tuple[str, list[dict]]]:
    """Variantes del escenario n como [(etiqueta, obstáculos)], sin la celda base."""
    e = C["escenarios"][n]
    if "variantes" in e:
        return [(f"{n} {v['etiqueta']}", _objetos(C, v["obstaculos"])) for v in e["variantes"]]
    if "obstaculos" in e:
        return [(f"{n}", _objetos(C, e["obstaculos"]))]
    raise ValueError(f"escenario {n}: estructura no reconocida (contrato {C['version']})")


# --------------------------------------------------------------------------- efector y TCP

def _matriz_rpy(r, p, y):
    cr, sr, cp, sp, cy, sy = math.cos(r), math.sin(r), math.cos(p), math.sin(p), math.cos(y), math.sin(y)
    return [[cy * cp, cy * sp * sr - sy * cr, cy * sp * cr + sy * sr],
            [sy * cp, sy * sp * sr + cy * cr, sy * sp * cr - cy * sr],
            [-sp, cp * sr, cp * cr]]


def tool0_desde_tcp(C: dict, pos, rpy) -> list[float]:
    """Posición de tool0 para que la punta del efector quede en `pos` con orientación `rpy`."""
    largo = C["efector"]["largo_m"]
    R = _matriz_rpy(*rpy)
    return [pos[i] - R[i][2] * largo for i in range(3)]


def objeto_efector(C: dict) -> dict:
    """Cilindro del efector en el marco de tool0 (centro a medio largo sobre +z)."""
    ef = C["efector"]
    return dict(id="efector", forma="cilindro", dims=[ef["largo_m"], ef["radio_m"]],
                pose=[0.0, 0.0, ef["largo_m"] / 2, 0.0, 0.0, 0.0])


# --------------------------------------------------------------------------- entrenamiento (3.6)

def _semialtura(o: dict) -> float:
    if o["forma"] == "caja":
        return o["dims"][2] / 2
    if o["forma"] == "cilindro":
        return o["dims"][0] / 2
    return o["dims"][0]


def muestrear_entrenamiento(C: dict, rng) -> tuple[str, list[dict]]:
    """Una escena de entrenamiento según `aleatorizacion_entrenamiento` del contrato.

    Se elige uno de los escenarios de entrenamiento con igual probabilidad. El 1 no tiene
    obstáculos; los demás (2, 4, 5 y 6 son el mismo primitivo sobre sus tres ejes de variación)
    dan un primitivo de forma, escala y posición aleatorias, apoyado en la mesa. El escenario 8
    nunca se muestrea.
    """
    A = C["aleatorizacion_entrenamiento"]
    n = int(rng.choice(A["escenarios_de_entrenamiento"]))
    if n == 1:
        return "1", []
    forma = str(rng.choice(A["forma"]["valores"]))
    k = float(rng.uniform(*A["escala"]["rango"]))
    dx, dy = (float(v) for v in rng.uniform(*A["posicion_m"]["rango"], size=2))
    cx, cy = A["centro_m"]
    o = objeto(C, f"o0_{forma}", forma, [cx + dx, cy + dy, 0.0, 0.0, 0.0, 0.0], k)
    o["pose"][2] = _semialtura(o) - 0.005          # apoyado en la mesa (z = -0.005)
    return f"entrenamiento {forma} k={k:.2f} d=({dx:+.3f},{dy:+.3f})", [o]
