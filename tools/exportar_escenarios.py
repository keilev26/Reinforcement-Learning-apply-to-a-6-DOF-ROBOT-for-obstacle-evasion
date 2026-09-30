"""Paquetes 1.4 y 3.12 — Exporta la biblioteca de componentes y los escenarios del contrato.

  cad/exportados/urdf/<componente>.urdf    un modelo por componente, origen en su centro geométrico
  cad/exportados/sdf/<componente>.sdf      ídem para Gazebo
  cad/exportados/mundos/<variante>.sdf     con --mundos: los 19 mundos de Gazebo del contrato

La colisión de cada componente es su primitiva envolvente del contrato (geometría de colisión
simplificada). Si existe `cad/<componente>.stl` (el CAD del paquete 1.2), se usa como visual del
URDF; mientras no esté, la visual es la misma primitiva.

Todo sale de `shared_scenarios/contrato.py`: es la misma geometría que componen PyBullet
(`gym_env/escena.py`), MoveIt (`p6_contrato.py`) y Gazebo (`gazebo_e6.launch.py`).

Uso: .venv/bin/python tools/exportar_escenarios.py [--mundos]
"""
import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "shared_scenarios"))
import contrato  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mundos", action="store_true", help="exportar también los 19 mundos SDF")
    a = ap.parse_args()
    C = contrato.cargar()
    destino = RAIZ / "cad" / "exportados"
    for sub in ("urdf", "sdf"):
        (destino / sub).mkdir(parents=True, exist_ok=True)
    for nombre in C["biblioteca"]:
        malla = RAIZ / "cad" / f"{nombre}.stl"
        visual = f"../../{malla.name}" if malla.exists() else None
        (destino / "urdf" / f"{nombre}.urdf").write_text(contrato.componente_urdf(C, nombre, visual))
        (destino / "sdf" / f"{nombre}.sdf").write_text(contrato.componente_sdf(C, nombre))
        print(f"{nombre:<16} {'CAD como visual' if visual else 'visual = primitiva (sin CAD en cad/)'}")
    if a.mundos:
        (destino / "mundos").mkdir(exist_ok=True)
        for n in C["escenarios"]:
            for etiqueta, _ in contrato.variantes(C, n):
                archivo = etiqueta.replace(" ", "_").replace("=", "") + ".sdf"
                (destino / "mundos" / archivo).write_text(contrato.mundo_sdf(C, n, etiqueta)[1])
        print(f"mundos en {destino / 'mundos'}")


if __name__ == "__main__":
    main()
