import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from gym_env.kit import COMBINACIONES, COMBINACIONES_2, COMBINACIONES_3, conflictos, objeto_kit

TODAS = COMBINACIONES + COMBINACIONES_2 + COMBINACIONES_3


def main():
    for letra, _, piezas in TODAS:
        for m in conflictos(piezas):
            print(f"{letra}: {m}")
    escenas = [dict(etiqueta=f"{letra} {titulo}", obstaculos=[objeto_kit(i, pz) for i, pz in enumerate(piezas)])
               for letra, titulo, piezas in TODAS]
    salida = RAIZ / "tools" / "escenas_demo" / "kit.yaml"
    salida.write_text(yaml.safe_dump(dict(descripcion="Combinaciones del kit fisico de obstaculos (envolventes). Generado por tools/kit_a_escenas.py",
                                          contrato="2.0", escenas=escenas), sort_keys=False, allow_unicode=True))
    print(salida)


if __name__ == "__main__":
    main()
