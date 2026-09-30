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


def muestrear_entrenamiento(C: dict, rng, escala_max: float | None = None) -> tuple[str, list[dict]]:
    """Una escena de entrenamiento según `aleatorizacion_entrenamiento` del contrato.

    Se elige uno de los escenarios de entrenamiento con igual probabilidad. El 1 no tiene
    obstáculos; los demás (2, 4, 5 y 6 son el mismo primitivo sobre sus tres ejes de variación)
    dan un primitivo de forma, escala y posición aleatorias, apoyado en la mesa. El escenario 8
    nunca se muestrea.

    `escala_max` (currículo, 3.6) recorta el rango superior de la escala durante el entrenamiento;
    None = el rango completo del contrato. La evaluación nunca lo usa.
    """
    A = C["aleatorizacion_entrenamiento"]
    n = int(rng.choice(A["escenarios_de_entrenamiento"]))
    if n == 1:
        return "1", []
    forma = str(rng.choice(A["forma"]["valores"]))
    lo, hi = A["escala"]["rango"]
    k = float(rng.uniform(lo, hi if escala_max is None else max(lo, min(hi, escala_max))))
    dx, dy = (float(v) for v in rng.uniform(*A["posicion_m"]["rango"], size=2))
    cx, cy = A["centro_m"]
    o = objeto(C, f"o0_{forma}", forma, [cx + dx, cy + dy, 0.0, 0.0, 0.0, 0.0], k)
    o["pose"][2] = _semialtura(o) - 0.005          # apoyado en la mesa (z = -0.005)
    return f"entrenamiento {forma} k={k:.2f} d=({dx:+.3f},{dy:+.3f})", [o]


# --------------------------------------------------------------------------- exportación (1.4, 3.12)
# Convención de anclaje: el origen de cada modelo exportado es el centro geométrico del componente,
# igual que `pose` en el contrato. Así un escenario se compone colocando cada modelo en su pose.

GRIS, ROJO = "0.7 0.7 0.7 1", "0.8 0.3 0.2 1"


def _geom_sdf(o: dict) -> str:
    if o["forma"] == "caja":
        return f"<box><size>{' '.join(f'{v:.6g}' for v in o['dims'])}</size></box>"
    if o["forma"] == "cilindro":
        altura, radio = o["dims"]
        return f"<cylinder><radius>{radio:.6g}</radius><length>{altura:.6g}</length></cylinder>"
    return f"<sphere><radius>{o['dims'][0]:.6g}</radius></sphere>"


def _geom_urdf(o: dict) -> str:
    if o["forma"] == "caja":
        return f'<box size="{" ".join(f"{v:.6g}" for v in o["dims"])}"/>'
    if o["forma"] == "cilindro":
        altura, radio = o["dims"]
        return f'<cylinder radius="{radio:.6g}" length="{altura:.6g}"/>'
    return f'<sphere radius="{o["dims"][0]:.6g}"/>'


def modelo_sdf(o: dict, color: str = GRIS, con_pose: bool = True) -> str:
    """<model> estático de SDF para un objeto de escena."""
    pose = f"<pose>{' '.join(f'{v:.6g}' for v in o['pose'])}</pose>" if con_pose else ""
    g = _geom_sdf(o)
    return (f"<model name='{o['id']}'><static>true</static>{pose}<link name='link'>"
            f"<collision name='c'><geometry>{g}</geometry></collision>"
            f"<visual name='v'><geometry>{g}</geometry><material><ambient>{color}</ambient>"
            f"<diffuse>{color}</diffuse></material></visual></link></model>")


def mundo_sdf(C: dict, escenario: int, variante: str | None = None) -> tuple[str, str]:
    """Mundo de Gazebo (SDF) de una variante: celda base + obstáculos. Devuelve (etiqueta, sdf)."""
    vs = variantes(C, escenario)
    etiqueta, obst = next((v for v in vs if v[0] == variante), vs[0]) if variante else vs[0]
    modelos = [modelo_sdf(o, GRIS) for o in celda(C)] + [modelo_sdf(o, ROJO) for o in obst]
    return etiqueta, f"""<?xml version="1.0"?>
<sdf version="1.9">
  <world name="celda">
    <!-- Generado desde el contrato {C['version']}, variante "{etiqueta}" (shared_scenarios/contrato.py) -->
    <physics name="1ms" type="ignored"><max_step_size>0.001</max_step_size><real_time_factor>1.0</real_time_factor></physics>
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <light type="directional" name="sol"><pose>0 0 3 0 0 0</pose><direction>-0.5 0.1 -0.9</direction>
      <diffuse>0.8 0.8 0.8 1</diffuse><cast_shadows>true</cast_shadows></light>
    {''.join(modelos)}
  </world>
</sdf>
"""


def componente_urdf(C: dict, nombre: str, malla_visual: str | None = None) -> str:
    """URDF de un componente de la biblioteca, anclado en su centro geométrico.

    La colisión es la primitiva envolvente del contrato (geometría de colisión simplificada, 1.3).
    Si se da `malla_visual` (el CAD del componente), se usa como visual; si no, la misma primitiva.
    """
    o = objeto(C, nombre, nombre, [0, 0, 0, 0, 0, 0])
    visual = f'<mesh filename="{malla_visual}"/>' if malla_visual else _geom_urdf(o)
    return f"""<?xml version="1.0"?>
<!-- Componente "{nombre}" de la biblioteca del contrato {C['version']}. Origen = centro geométrico. -->
<robot name="{nombre}">
  <link name="{nombre}">
    <visual><geometry>{visual}</geometry></visual>
    <collision><geometry>{_geom_urdf(o)}</geometry></collision>
  </link>
</robot>
"""


def componente_sdf(C: dict, nombre: str) -> str:
    o = objeto(C, nombre, nombre, [0, 0, 0, 0, 0, 0])
    return f"""<?xml version="1.0"?>
<!-- Componente "{nombre}" de la biblioteca del contrato {C['version']}. Origen = centro geométrico. -->
<sdf version="1.9">{modelo_sdf(o, GRIS, con_pose=False)}</sdf>
"""


# --------------------------------------------------------------------------- evaluación (4.2)

RUTA_EVALUACION = Path(__file__).resolve().parent / "evaluacion.yaml"


def muestrear_con_obstaculo(C: dict, rng) -> tuple[str, list[dict]]:
    """Como `muestrear_entrenamiento`, pero siempre con obstáculo (escenarios 2, 4, 5 y 6)."""
    while True:
        etiqueta, obst = muestrear_entrenamiento(C, rng)
        if obst:
            return etiqueta, obst


def escenas_evaluacion(ruta=RUTA_EVALUACION) -> list[tuple[str, list[dict]]]:
    """Conjunto fijo de escenas de evaluación (metricas.yaml, protocolo): [(etiqueta, obstáculos)]."""
    datos = yaml.safe_load(Path(ruta).read_text())
    return [(e["etiqueta"], e["obstaculos"]) for e in datos["escenas"]]
