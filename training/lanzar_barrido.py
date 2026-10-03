import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
RUNS = RAIZ / "training" / "runs"
ENTORNOS_POR_CORRIDA = 4


def nombre_corrida(c: dict) -> str:
    base = f"{c['config']}_{c['etiqueta']}" if c.get("etiqueta") else c["config"]
    return f"{base}_s{c['semilla']}"


def carpetas_de(c: dict) -> list[Path]:
    return sorted(RUNS.glob(f"{nombre_corrida(c)}_[0-9]*"))


def terminada(carpeta: Path, pasos_pedidos: int | None) -> bool:
    if not (carpeta / "modelo_final.zip").exists():
        return False
    estado = carpeta / "estado.json"
    if pasos_pedidos is None or not estado.exists():
        return True
    return json.loads(estado.read_text())["pasos_totales"] >= pasos_pedidos


def completada(c: dict) -> bool:
    return any(terminada(d, c.get("pasos")) for d in carpetas_de(c))


def expandir(barrido: dict) -> list[dict]:
    comunes = barrido.get("comunes", {})
    return [{**comunes, **c} for c in barrido["corridas"]]


def comando(c: dict) -> list[str]:
    cmd = [sys.executable, "-m", "training.entrenar_sac", "--config", c["config"], "--semilla", str(c["semilla"])]
    for clave, bandera in (("pasos", "--pasos"), ("dispositivo", "--dispositivo"), ("hilos", "--hilos"),
                           ("etiqueta", "--etiqueta")):
        if c.get(clave) not in (None, ""):
            cmd += [bandera, str(c[clave])]
    for clave, valor in (c.get("cambios") or {}).items():
        cmd += ["--set", f"{clave}={json.dumps(valor)}"]
    return cmd


def paralelo_por_defecto(barrido: dict) -> int:
    hilos = barrido.get("comunes", {}).get("hilos") or 2
    return max(1, (os.cpu_count() or 2) // (ENTORNOS_POR_CORRIDA + hilos))


def resumen(corridas: list[dict]) -> str:
    filas = [f"{'corrida':<34}{'estado':<14}{'pasos del mejor':>16}{'éxito val.':>12}{'colisión val.':>15}{'error mm':>10}"]
    for c in corridas:
        carpetas = carpetas_de(c)
        estado = "completada" if completada(c) else ("parcial" if carpetas else "pendiente")
        mejor = None
        for d in reversed(carpetas):
            if (d / "mejor.json").exists():
                mejor = json.loads((d / "mejor.json").read_text())
                break
        if mejor:
            filas.append(f"{nombre_corrida(c):<34}{estado:<14}{mejor['pasos']:>16}{mejor['exito']:>12.2f}"
                         f"{mejor['colision']:>15.2f}{mejor['error_mm']:>10.1f}")
        else:
            filas.append(f"{nombre_corrida(c):<34}{estado:<14}")
    return "\n".join(filas)


def ejecutar(corridas: list[dict], paralelo: int, carpeta_logs: Path) -> int:
    pendientes = [c for c in corridas if not completada(c)]
    activos: list[tuple[dict, subprocess.Popen, float]] = []
    fallidas = 0
    carpeta_logs.mkdir(parents=True, exist_ok=True)

    def terminar(*_):
        for _, proc, _ in activos:
            proc.terminate()
        sys.exit(130)

    signal.signal(signal.SIGINT, terminar)
    signal.signal(signal.SIGTERM, terminar)
    while pendientes or activos:
        while pendientes and len(activos) < paralelo:
            c = pendientes.pop(0)
            log = open(carpeta_logs / f"{nombre_corrida(c)}.log", "w")
            proc = subprocess.Popen(comando(c), cwd=RAIZ, stdout=log, stderr=subprocess.STDOUT)
            activos.append((c, proc, time.time()))
            print(f"[{time.strftime('%H:%M:%S')}] inicia {nombre_corrida(c)} (pid {proc.pid})", flush=True)
        time.sleep(5)
        for item in list(activos):
            c, proc, t0 = item
            if proc.poll() is not None:
                activos.remove(item)
                ok = proc.returncode == 0
                fallidas += 0 if ok else 1
                print(f"[{time.strftime('%H:%M:%S')}] {'termina' if ok else 'FALLA '} {nombre_corrida(c)} "
                      f"({(time.time() - t0) / 60:.1f} min, código {proc.returncode})", flush=True)
    return fallidas


def main():
    ap = argparse.ArgumentParser(description="Lanza un barrido de entrenamientos en paralelo y resume sus resultados")
    ap.add_argument("barrido", type=Path)
    ap.add_argument("--paralelo", type=int, default=None, help="corridas simultáneas (por defecto, según los núcleos)")
    ap.add_argument("--simular", action="store_true", help="mostrar los comandos sin ejecutarlos")
    ap.add_argument("--resumen", action="store_true", help="solo resumir lo que ya existe")
    a = ap.parse_args()
    barrido = yaml.safe_load(a.barrido.read_text())
    corridas = expandir(barrido)
    paralelo = a.paralelo or barrido.get("paralelo") or paralelo_por_defecto(barrido)
    if a.resumen:
        print(resumen(corridas))
        return
    if a.simular:
        print(f"{len(corridas)} corridas, {paralelo} en paralelo\n")
        for c in corridas:
            print(("[completada, se omite] " if completada(c) else "") + shlex.join(comando(c)))
        return
    fallidas = ejecutar(corridas, paralelo, RUNS / "barridos" / a.barrido.stem)
    print("\n" + resumen(corridas))
    sys.exit(1 if fallidas else 0)


if __name__ == "__main__":
    main()
