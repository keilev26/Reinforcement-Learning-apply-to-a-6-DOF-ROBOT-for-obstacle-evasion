import argparse
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "shared_scenarios"))
import contrato


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
