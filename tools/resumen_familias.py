import csv
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env import kit


def grupo(variante: str) -> str:
    pref = variante.split(" ")[0]
    if pref.startswith("PG-"):
        par = variante.rsplit("par=", 1)[-1]
        return "PG " + ("par no visto" if par in kit.PARES_NO_VISTOS else "par visto")
    if pref.startswith(("S-", "SP-")):
        letra = pref.split("-")[1]
        return pref.split("-")[0] + (" prueba" if letra in kit.FAMILIAS_PRUEBA else " entrenadas")
    return pref.rstrip("0123456789")


def main():
    for ruta in sys.argv[1:]:
        cuentas = defaultdict(lambda: [0, 0])
        for f in csv.DictReader(open(ruta)):
            g = grupo(f["variante"])
            cuentas[g][1] += 1
            cuentas[g][0] += f["exito"] == "True"
        total = [sum(v[0] for v in cuentas.values()), sum(v[1] for v in cuentas.values())]
        print(Path(ruta).parent.name)
        for g in sorted(cuentas):
            n, t = cuentas[g]
            print(f"  {g:14s} {n / t:6.1%} ({n}/{t})")
        print(f"  {'total':14s} {total[0] / total[1]:6.1%}")


if __name__ == "__main__":
    main()
