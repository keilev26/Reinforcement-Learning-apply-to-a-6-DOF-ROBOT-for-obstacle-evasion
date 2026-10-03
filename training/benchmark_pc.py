import argparse
import datetime
import multiprocessing as mp
import os
import socket
import sys
import time
from pathlib import Path

import numpy as np
import torch
import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

CONFIGURACIONES = [([256, 256], 256), ([256, 256], 1024), ([512, 512, 512], 1024), ([1024, 1024, 1024], 2048)]
RAM_POR_CORRIDA_GB = 1.5
EFICIENCIA_MINIMA = 0.7


def info_sistema() -> dict:
    meminfo = {}
    for linea in Path("/proc/meminfo").read_text().splitlines():
        clave, valor = linea.split(":")
        meminfo[clave] = int(valor.split()[0]) / 1e6
    gpu = None
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        gpu = {"nombre": props.name, "memoria_gb": round(props.total_memory / 1e9, 1)}
    return {"equipo": socket.gethostname(), "nucleos": os.cpu_count(), "ram_gb": round(meminfo["MemTotal"], 1),
            "ram_disponible_gb": round(meminfo["MemAvailable"], 1), "torch": str(torch.__version__), "gpu": gpu}


def _trabajador(segundos: float, listos, inicio, resultados) -> None:
    from gym_env.entorno import EntornoE6
    env = EntornoE6()
    env.reset(seed=0)
    listos.put(1)
    inicio.wait()
    pasos, limite = 0, time.perf_counter() + segundos
    while time.perf_counter() < limite:
        _, _, te, tr, _ = env.step(env.action_space.sample())
        pasos += 1
        if te or tr:
            env.reset()
    resultados.put(pasos)
    env.close()


def simulacion(n_procesos: int, segundos: float) -> float:
    ctx = mp.get_context("spawn")
    listos, resultados, inicio = ctx.Queue(), ctx.Queue(), ctx.Event()
    procesos = [ctx.Process(target=_trabajador, args=(segundos, listos, inicio, resultados)) for _ in range(n_procesos)]
    for p in procesos:
        p.start()
    for _ in procesos:
        listos.get()
    inicio.set()
    total = sum(resultados.get() for _ in procesos)
    for p in procesos:
        p.join()
    return total / segundos


def ms_actualizacion(dispositivo: str, arquitectura: list[int], lote: int, objetivo_s: float) -> float:
    from stable_baselines3 import SAC
    from gym_env.entorno import EntornoE6
    env = EntornoE6()
    modelo = SAC("MlpPolicy", env, learning_starts=10 ** 9, buffer_size=20000, batch_size=lote, device=dispositivo,
                 policy_kwargs={"net_arch": arquitectura}, seed=0)
    modelo.learn(total_timesteps=max(2 * lote, 2000))

    def medir(repeticiones: int) -> float:
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        modelo.train(gradient_steps=repeticiones, batch_size=lote)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        return (time.perf_counter() - t0) / repeticiones * 1000

    medir(3)
    estimado = medir(5)
    ms = medir(max(5, int(objetivo_s * 1000 / max(estimado, 0.01))))
    env.close()
    return ms


def pasos_por_segundo_estimados(t_sim_ms: float, t_actualizacion_ms: float, n_entornos: int) -> float:
    return 1000.0 / (t_actualizacion_ms + t_sim_ms / n_entornos)


def main():
    ap = argparse.ArgumentParser(description="Mide qué configuración de entrenamiento conviene en este equipo")
    ap.add_argument("--rapido", action="store_true", help="prueba corta de funcionamiento (no sirve para decidir)")
    ap.add_argument("--segundos", type=float, default=6.0, help="duración de cada medición de simulación")
    ap.add_argument("--objetivo", type=float, default=4.0, help="segundos por medición de actualización de la red")
    ap.add_argument("--hilos", type=int, default=2, help="hilos de PyTorch en CPU, como en el entrenamiento")
    ap.add_argument("--entornos", type=int, default=4, help="entornos por corrida")
    ap.add_argument("--sin-gpu", action="store_true")
    a = ap.parse_args()
    if a.rapido:
        a.segundos, a.objetivo = 1.0, 0.3
    torch.set_num_threads(a.hilos)

    sistema = info_sistema()
    print(yaml.safe_dump(sistema, allow_unicode=True, sort_keys=False))
    nucleos = sistema["nucleos"]
    escala = [1, 2] if a.rapido else sorted({k for k in (1, 2, 4, 8, 12, 16, 24, 32, 48, 64) if k <= nucleos} | {nucleos})

    print("simulación: pasos por segundo del entorno con k procesos a la vez")
    throughput = {}
    for k in escala:
        throughput[k] = simulacion(k, a.segundos)
        print(f"  k={k:<3} total {throughput[k]:>8.0f}/s   por proceso {throughput[k] / k:>7.0f}/s   "
              f"eficiencia {throughput[k] / (k * throughput[1]):>5.0%}", flush=True)
    utiles = max([k for k in escala if throughput[k] / (k * throughput[1]) >= EFICIENCIA_MINIMA] or [1])
    t_sim_ms = 1000.0 / throughput[1]

    dispositivos = ["cpu"] + (["cuda"] if torch.cuda.is_available() and not a.sin_gpu else [])
    print("\nactualización de la red SAC: ms por actualización")
    filas = []
    for dispositivo in dispositivos:
        for arquitectura, lote in CONFIGURACIONES:
            ms = ms_actualizacion(dispositivo, arquitectura, lote, a.objetivo)
            est = pasos_por_segundo_estimados(t_sim_ms, ms, a.entornos)
            filas.append({"dispositivo": dispositivo, "red": arquitectura, "lote": lote, "ms_por_actualizacion": round(ms, 2),
                          "pasos_por_s_una_corrida": round(est, 1)})
            print(f"  {dispositivo:<5} red {str(arquitectura):<20} lote {lote:<5} {ms:>9.2f} ms   "
                  f"-> ~{est:>5.0f} pasos/s por corrida", flush=True)

    base = [f for f in filas if f["red"] == [256, 256] and f["lote"] == 256]
    mejor_base = min(base, key=lambda f: f["ms_por_actualizacion"])
    hilos_por_corrida = a.entornos + a.hilos
    paralelo_cpu = max(1, nucleos // hilos_por_corrida)
    paralelo_ram = max(1, int(sistema["ram_disponible_gb"] // RAM_POR_CORRIDA_GB))
    paralelo = min(paralelo_cpu, paralelo_ram)
    recomendacion = {
        "dispositivo_para_la_red_base": mejor_base["dispositivo"],
        "pasos_por_s_por_corrida_red_base": mejor_base["pasos_por_s_una_corrida"],
        "corridas_en_paralelo": paralelo,
        "limitado_por": "núcleos" if paralelo_cpu <= paralelo_ram else "RAM",
        "procesos_de_simulacion_utiles": utiles,
        "horas_por_corrida_de_1M": round(1e6 / mejor_base["pasos_por_s_una_corrida"] / 3600, 2),
        "horas_para_el_barrido_nucleo_6_corridas": round(float(np.ceil(6 / paralelo)) * 1e6 / mejor_base["pasos_por_s_una_corrida"] / 3600, 2),
    }
    print("\nrecomendación para la red base (256x256, lote 256):")
    print(yaml.safe_dump(recomendacion, allow_unicode=True, sort_keys=False))

    resultado = {"sistema": sistema, "simulacion_pasos_por_s": {k: round(v, 1) for k, v in throughput.items()},
                 "actualizacion": filas, "recomendacion": recomendacion,
                 "supuestos": {"hilos_torch": a.hilos, "entornos_por_corrida": a.entornos, "ram_por_corrida_gb": RAM_POR_CORRIDA_GB,
                               "rapido": a.rapido}}
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    salida = RAIZ / "results" / f"benchmark_pc_{sistema['equipo']}_{fecha}{'_rapido' if a.rapido else ''}.yaml"
    salida.write_text(yaml.safe_dump(resultado, allow_unicode=True, sort_keys=False))
    print(f"-> {salida}")


if __name__ == "__main__":
    main()
