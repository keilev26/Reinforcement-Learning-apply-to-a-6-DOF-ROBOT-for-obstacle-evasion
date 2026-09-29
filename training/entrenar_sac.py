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


def episodio(modelo, env, escenario, variante):
    obs, info = env.reset(options={"escenario": escenario, "variante": variante})
    fin = False
    while not fin:
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
    return info


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
                         "pasos_media", "L_cart_media_m"])

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
    a = ap.parse_args()
    cfg = yaml.safe_load((RAIZ / "training" / "configs" / f"{a.config}.yaml").read_text())
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
    modelo = SAC("MlpPolicy", venv, learning_rate=S["learning_rate"], buffer_size=S["buffer_size"],
                 learning_starts=S["learning_starts"], batch_size=S["batch_size"], tau=S["tau"],
                 gamma=S["gamma"], train_freq=S["train_freq"], gradient_steps=S["gradient_steps"],
                 ent_coef=S["ent_coef"], policy_kwargs={"net_arch": S["net_arch"]}, seed=semilla,
                 tensorboard_log=str(carpeta / "tensorboard"), verbose=0)
    modelo.learn(total_timesteps=pasos, callback=Evaluacion(cfg, carpeta), progress_bar=False)
    modelo.save(carpeta / "modelo_final")
    venv.close()
    print(f"modelo en {carpeta}")


if __name__ == "__main__":
    main()
