"""Paquete 3.5 — Entrenamiento SAC del Magician E6.

Lee la configuración de training/configs/<nombre>.yaml, entrena con Stable-Baselines3 sobre
`gym_env.entorno.EntornoE6` y evalúa periódicamente la política determinista sobre variantes del
contrato (nunca el escenario 8: es la prueba de generalización y no puede verse al entrenar).

Salidas en training/runs/<config>_s<semilla>_<fecha>/ (no se versiona):
  modelo_final.zip, modelos intermedios, evaluaciones.csv, tensorboard/

Uso:
  .venv/bin/python -m training.entrenar_sac --config sac_v0
  .venv/bin/python -m training.entrenar_sac --config sac_v0 --pasos 20000 --semilla 1
"""
import argparse
import csv
import datetime
from pathlib import Path

import numpy as np
import yaml
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv

from gym_env.entorno import EntornoE6

RAIZ = Path(__file__).resolve().parents[1]


def _fusionar(base: dict, cambios: dict) -> dict:
    out = dict(base)
    for k, v in cambios.items():
        out[k] = _fusionar(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def cargar_config(nombre: str) -> dict:
    """Lee training/configs/<nombre>.yaml. Con `base: <otra>`, hereda de ella y solo cambia lo
    que declara: cada experimento muestra exactamente en qué difiere."""
    cfg = yaml.safe_load((RAIZ / "training" / "configs" / f"{nombre}.yaml").read_text())
    if "base" in cfg:
        cfg = _fusionar(cargar_config(cfg.pop("base")), cfg)
    return cfg


def episodio(modelo, env, escenario, variante):
    obs, info = env.reset(options={"escenario": escenario, "variante": variante})
    fin = False
    while not fin:
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
    return info


class Curriculo(BaseCallback):
    """Currículo de escala (3.6): el obstáculo máximo crece linealmente durante el entrenamiento.

    Empieza en `escala_max_inicial` y llega a `escala_max_final` (el rango completo del contrato) al
    `fraccion` de los pasos totales; después queda fijo. Solo cambia el muestreo de ENTRENAMIENTO:
    las evaluaciones periódicas y las finales usan siempre las mismas escenas.
    """

    def __init__(self, cfg: dict, pasos_totales: int):
        super().__init__()
        self.c, self.total, self.ultimo = cfg, pasos_totales, None

    def valor(self) -> float:
        c = self.c
        avance = min(1.0, self.num_timesteps / (c["fraccion"] * self.total))
        return c["escala_max_inicial"] + avance * (c["escala_max_final"] - c["escala_max_inicial"])

    def _on_training_start(self) -> None:
        self._aplicar()

    def _on_step(self) -> bool:
        if self.num_timesteps % 5000 < self.training_env.num_envs:
            self._aplicar()
        return True

    def _aplicar(self) -> None:
        v = round(self.valor(), 3)
        if v != self.ultimo:
            self.training_env.env_method("fijar_escala_max", v)
            self.logger.record("curriculo/escala_max", v)
            self.ultimo = v


class Evaluacion(BaseCallback):
    """Evalúa la política determinista cada `cada` pasos y guarda una fila por variante."""

    def __init__(self, cfg, carpeta: Path):
        super().__init__()
        self.cfg, self.carpeta = cfg["evaluacion"], carpeta
        self.env = EntornoE6(recompensa=cfg["entorno"]["recompensa"])
        self.proxima = self.cfg["cada_pasos"]
        self.csv = open(carpeta / "evaluaciones.csv", "w", newline="")
        self.w = csv.writer(self.csv)
        self.w.writerow(["pasos", "variante", "exito", "colisiones_media", "error_pos_mm_mediana",
                         "error_ori_rad_mediana", "pasos_media", "L_cart_media_m"])

    def _on_training_start(self) -> None:
        # Al continuar un modelo el contador no empieza en 0
        self.proxima = self.num_timesteps + self.cfg["cada_pasos"]

    def _on_step(self) -> bool:
        if self.num_timesteps < self.proxima:
            return True
        self.proxima += self.cfg["cada_pasos"]
        for etiqueta in self.cfg["variantes"]:
            n = int(etiqueta.split()[0])
            infos = [episodio(self.model, self.env, n, etiqueta) for _ in range(self.cfg["episodios_por_variante"])]
            exito = np.mean([i["exito"] for i in infos])
            self.w.writerow([self.num_timesteps, etiqueta, f"{exito:.2f}",
                             np.mean([i["colisiones"] for i in infos]),
                             f"{np.median([i['error_pos_m'] for i in infos]) * 1000:.1f}",
                             f"{np.median([i['error_ori_rad'] for i in infos]):.3f}",
                             np.mean([i["pasos"] for i in infos]),
                             f"{np.mean([i['L_cart_m'] for i in infos]):.3f}"])
            self.logger.record(f"eval/exito_{etiqueta}", exito)
        self.csv.flush()
        self.model.save(self.carpeta / f"modelo_{self.num_timesteps}")
        return True

    def _on_training_end(self) -> None:
        self.csv.close()
        self.env.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="sac_v0")
    ap.add_argument("--pasos", type=int, default=None, help="sobrescribe entrenamiento.pasos_totales")
    ap.add_argument("--semilla", type=int, default=None)
    ap.add_argument("--desde", type=Path, default=None,
                    help="continuar desde un modelo guardado (.zip). El búfer de repetición no se "
                         "guarda: se vuelve a llenar durante learning_starts pasos")
    ap.add_argument("--dispositivo", choices=["auto", "cpu", "cuda"], default="auto",
                    help="dónde se entrena la red. La evaluación de M4 se hace SIEMPRE en CPU")
    ap.add_argument("--hilos", type=int, default=None,
                    help="hilos de PyTorch; al correr varios entrenamientos a la vez conviene 2-3 "
                         "por corrida para no sobresuscribir la CPU")
    a = ap.parse_args()
    if a.hilos:
        import torch
        torch.set_num_threads(a.hilos)
    cfg = cargar_config(a.config)
    pasos = a.pasos or cfg["entrenamiento"]["pasos_totales"]
    semilla = cfg["entrenamiento"]["semilla"] if a.semilla is None else a.semilla

    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    carpeta = RAIZ / "training" / "runs" / f"{a.config}_s{semilla}_{fecha}"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "config.yaml").write_text(yaml.safe_dump({**cfg, "pasos_usados": pasos, "semilla_usada": semilla}))

    E = cfg["entorno"]
    venv = make_vec_env(EntornoE6, n_envs=E["n_entornos"], seed=semilla, vec_env_cls=SubprocVecEnv,
                        env_kwargs={"escenario": E["escenario"], "recompensa": E["recompensa"]})
    S = cfg["sac"]
    if a.desde:
        modelo = SAC.load(a.desde, env=venv, device=a.dispositivo,
                          tensorboard_log=str(carpeta / "tensorboard"))
        (carpeta / "continua_desde.txt").write_text(str(a.desde) + "\n")
        # El búfer no viene guardado: se rellena antes de volver a actualizar
        modelo.learning_starts = modelo.num_timesteps + S["learning_starts"]
    else:
        modelo = SAC("MlpPolicy", venv, learning_rate=S["learning_rate"], buffer_size=S["buffer_size"],
                 learning_starts=S["learning_starts"], batch_size=S["batch_size"], tau=S["tau"],
                 gamma=S["gamma"], train_freq=S["train_freq"], gradient_steps=S["gradient_steps"],
                 ent_coef=S["ent_coef"], policy_kwargs={"net_arch": S["net_arch"]}, seed=semilla,
                 device=a.dispositivo,
                 tensorboard_log=str(carpeta / "tensorboard"), verbose=0)
    callbacks = [Evaluacion(cfg, carpeta)]
    if cfg.get("curriculo"):
        callbacks.append(Curriculo(cfg["curriculo"], pasos))
    modelo.learn(total_timesteps=pasos, callback=callbacks, progress_bar=False,
                 reset_num_timesteps=a.desde is None)
    modelo.save(carpeta / "modelo_final")
    venv.close()
    print(f"modelo en {carpeta}")


if __name__ == "__main__":
    main()
