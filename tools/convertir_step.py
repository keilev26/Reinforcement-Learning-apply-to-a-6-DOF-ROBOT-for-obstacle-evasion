import argparse
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh


def convertir(step: Path, salida: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bruto = Path(tmp) / "pieza.stl"
        cq.exporters.export(cq.importers.importStep(str(step)), str(bruto), tolerance=0.2, angularTolerance=0.2)
        malla = trimesh.load(bruto)
    v = np.asarray(malla.vertices)
    malla.vertices = np.column_stack([v[:, 0], -v[:, 2], v[:, 1]]) * 0.001
    malla.export(salida)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", type=Path, default=Path("cad/Mesa_E6_SolidWorks/STEP"))
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args()
    a.salida.mkdir(parents=True, exist_ok=True)
    for step in sorted(a.entrada.glob("*.STEP")):
        convertir(step, a.salida / f"{step.stem}.stl")
        print(step.stem, flush=True)


if __name__ == "__main__":
    main()
