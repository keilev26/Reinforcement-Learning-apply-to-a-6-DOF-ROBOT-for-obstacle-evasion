import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

GRUPOS = [("S", "estructuradas, par nominal"), ("SP", "estructuradas, otro par"), ("R", "sorteo, par nominal"),
          ("RPv", "sorteo, par visto"), ("RPn", "sorteo, par no visto")]


def grupo(variante: str) -> str:
    m = re.match(r"^(SP|S|RPv|RPn|R)[-\d]", variante)
    return m.group(1) if m else "otro"


def leer(ruta: Path) -> dict[str, list[dict]]:
    por_grupo = defaultdict(list)
    with open(ruta) as f:
        for fila in csv.DictReader(f):
            por_grupo[grupo(fila["variante"])].append(fila)
    return por_grupo


def main():
    ap = argparse.ArgumentParser(description="Éxito por grupo de escenas del kit a partir de los CSV de evaluar_politica")
    ap.add_argument("csv", type=Path, nargs="+")
    a = ap.parse_args()
    datos = {r.stem: leer(r) for r in a.csv}
    print(f"{'grupo':<30}" + "".join(f"{n[:24]:>26}" for n in datos))
    for g, texto in GRUPOS + [("otro", "otras")]:
        if not any(g in d for d in datos.values()):
            continue
        celdas = []
        for d in datos.values():
            filas = d.get(g, [])
            ok = [fila["exito"] == "True" for fila in filas]
            col = [float(fila["colisiones"]) > 0 for fila in filas]
            celdas.append(f"{np.mean(ok):.3f} ({sum(ok)}/{len(ok)}, col {np.mean(col):.2f})" if filas else "-")
        print(f"{g + ' ' + texto:<30}" + "".join(f"{c:>26}" for c in celdas))
    total = [sum(fila["exito"] == "True" for fs in d.values() for fila in fs) / max(1, sum(len(fs) for fs in d.values()))
             for d in datos.values()]
    print(f"{'total':<30}" + "".join(f"{t:>26.3f}" for t in total))


if __name__ == "__main__":
    main()
