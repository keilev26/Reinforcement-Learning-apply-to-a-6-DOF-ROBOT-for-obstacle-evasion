import argparse
import copy
import csv
import datetime
import json
import math
from pathlib import Path

import numpy as np
import torch
import yaml
from stable_baselines3 import SAC
from stable_baselines3.common.buffers import ReplayBuffer
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.type_aliases import ReplayBufferSamples
from stable_baselines3.common.vec_env import SubprocVecEnv

from gym_env.entorno import EntornoE6
from gym_env.escena import contrato

RAIZ = Path(__file__).resolve().parents[1]


def _fusionar(base: dict, cambios: dict) -> dict:
    out = dict(base)
    for k, v in cambios.items():
        out[k] = _fusionar(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def cargar_config(nombre: str) -> dict:
    cfg = yaml.safe_load((RAIZ / "training" / "configs" / f"{nombre}.yaml").read_text())
    if "base" in cfg:
        cfg = _fusionar(cargar_config(cfg.pop("base")), cfg)
    return cfg


def interpretar(valor: str):
    try:
        return json.loads(valor)
    except ValueError:
        return yaml.safe_load(valor)


def aplicar_cambios(cfg: dict, cambios: list[str]) -> dict:
    out = copy.deepcopy(cfg)
    for cambio in cambios:
        clave, separador, valor = cambio.partition("=")
        if not separador:
            raise ValueError(f"cambio sin '=': {cambio}")
        *ruta, hoja = clave.split(".")
        nodo = out
        for k in ruta:
            if not isinstance(nodo.get(k), dict):
                raise KeyError(f"clave desconocida: {clave}")
            nodo = nodo[k]
        if hoja not in nodo:
            raise KeyError(f"clave desconocida: {clave}")
        nodo[hoja] = interpretar(valor)
    return out


def criterio_mejor(nuevo: dict, mejor: dict | None) -> bool:
    if mejor is None:
        return True
    clave = lambda m: (m["exito"], -m["colision"], -m["error_mm"])
    return clave(nuevo) > clave(mejor)


def debe_detener(criticos: list[float], validaciones: list[float], parada: dict) -> str | None:
    umbral, lecturas = parada.get("critic_loss"), parada["lecturas"]
    if umbral is not None and len(criticos) >= lecturas and all(c > umbral for c in criticos[-lecturas:]):
        return "critic_loss"
    n = parada["validaciones"]
    if len(validaciones) >= n:
        mejor = max(validaciones)
        if mejor > 0 and all(v < parada["validacion_ratio"] * mejor for v in validaciones[-n:]):
            return "validacion"
    return None


class BufferConDemos(ReplayBuffer):

    def __init__(self, *args, demos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.demos = None if demos is None else {k: np.asarray(v) for k, v in demos.items()}
        self.rng = np.random.default_rng(0)

    def sample(self, batch_size, env=None):
        if self.demos is None:
            return super().sample(batch_size, env)
        n_demos = batch_size // 2
        propias = super().sample(batch_size - n_demos, env)
        d = self.demos
        i = self.rng.integers(0, len(d["acciones"]), n_demos)
        demos = (d["obs"][i], d["acciones"][i], d["obs_sig"][i],
                 d["terminados"][i].reshape(-1, 1), d["recompensas"][i].reshape(-1, 1))
        demos = [self.to_torch(x.astype(np.float32)) for x in demos]
        return ReplayBufferSamples(*[torch.cat([a, b]) for a, b in zip(propias[:5], demos)])


def episodio_escena(modelo, env, etiqueta, obstaculos, par=None):
    opciones = {"obstaculos": obstaculos, "etiqueta": etiqueta}
    if par:
        opciones["par"] = par
    obs, info = env.reset(options=opciones)
    fin = False
    while not fin:
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
    return info


def episodio(modelo, env, escenario, variante):
    obs, info = env.reset(options={"escenario": escenario, "variante": variante})
    fin = False
    while not fin:
        a, _ = modelo.predict(obs, deterministic=True)
        obs, _, te, tr, info = env.step(a)
        fin = te or tr
    return info


class ParadaDivergencia(BaseCallback):

    def __init__(self, parada: dict, validacion, carpeta: Path):
        super().__init__()
        self.parada, self.validacion, self.carpeta = parada, validacion, carpeta
        self.criticos, self.ema, self.proxima, self.motivo = [], None, 5000, None

    def _on_training_start(self) -> None:
        self.proxima = self.num_timesteps + 5000

    def _on_step(self) -> bool:
        if self.num_timesteps < self.proxima:
            return True
        self.proxima += 5000
        valor = self.model.logger.name_to_value.get("train/critic_loss")
        if valor is not None:
            self.ema = float(valor) if self.ema is None else 0.8 * self.ema + 0.2 * float(valor)
            self.criticos.append(self.ema)
        self.motivo = debe_detener(self.criticos, self.validacion.historial, self.parada)
        return self.motivo is None


class AcotarEntropia(BaseCallback):

    def __init__(self, ent_max: float):
        super().__init__()
        self.tope = math.log(ent_max)

    def _on_step(self) -> bool:
        with torch.no_grad():
            self.model.log_ent_coef.clamp_(max=self.tope)
        return True


class GuardarBuffer(BaseCallback):

    def __init__(self, carpeta: Path, cada: int = 1_000_000):
        super().__init__()
        self.carpeta, self.cada, self.proxima = carpeta, cada, cada

    def _on_training_start(self) -> None:
        self.proxima = self.num_timesteps + self.cada

    def _on_step(self) -> bool:
        if self.num_timesteps >= self.proxima:
            self.proxima += self.cada
            self.model.save_replay_buffer(self.carpeta / "buffer")
        return True

    def _on_training_end(self) -> None:
        self.model.save_replay_buffer(self.carpeta / "buffer")


class Curriculo(BaseCallback):

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


class CurriculoEstructuradas(BaseCallback):

    def __init__(self, cfg: dict, pasos_totales: int):
        super().__init__()
        self.c, self.total, self.ultimo = cfg, pasos_totales, None

    def valor(self) -> float:
        c = self.c
        avance = min(1.0, self.num_timesteps / (c["fraccion"] * self.total))
        return c["p_inicial"] + avance * (c["p_final"] - c["p_inicial"])

    def _on_training_start(self) -> None:
        self._aplicar()

    def _on_step(self) -> bool:
        if self.num_timesteps % 5000 < self.training_env.num_envs:
            self._aplicar()
        return True

    def _aplicar(self) -> None:
        v = round(self.valor(), 3)
        if v != self.ultimo:
            self.training_env.env_method("fijar_p_estructuradas", v)
            self.logger.record("curriculo/p_estructuradas", v)
            self.ultimo = v


class Evaluacion(BaseCallback):

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


class Validacion(BaseCallback):

    def __init__(self, cfg, carpeta: Path):
        super().__init__()
        v = cfg["evaluacion"]["validacion"]
        ruta = Path(v["archivo"])
        self.escenas = contrato.escenas_con_par(ruta if ruta.is_absolute() else RAIZ / ruta)
        self.cada, self.carpeta, self.mejor, self.ultimo = v["cada_pasos"], carpeta, None, -1
        self.historial = []
        self.env = EntornoE6(recompensa=cfg["entorno"]["recompensa"])
        self.csv = open(carpeta / "validacion.csv", "w", newline="")
        self.w = csv.writer(self.csv)
        self.w.writerow(["pasos", "exito", "colision", "error_pos_mm_mediana", "pasos_media", "es_mejor"])

    def _on_training_start(self) -> None:
        self.proxima = self.num_timesteps + self.cada

    def _validar(self) -> None:
        infos = [episodio_escena(self.model, self.env, et, ob, par) for et, ob, par in self.escenas]
        m = {"pasos": int(self.num_timesteps), "exito": float(np.mean([i["exito"] for i in infos])),
             "colision": float(np.mean([i["colisiones"] > 0 for i in infos])),
             "error_mm": float(np.median([i["error_pos_m"] for i in infos]) * 1000),
             "pasos_media": float(np.mean([i["pasos"] for i in infos]))}
        es_mejor = criterio_mejor(m, self.mejor)
        if es_mejor:
            self.mejor = m
            self.model.save(self.carpeta / "mejor")
            (self.carpeta / "mejor.json").write_text(json.dumps(m))
        self.w.writerow([m["pasos"], f"{m['exito']:.3f}", f"{m['colision']:.3f}", f"{m['error_mm']:.1f}",
                         f"{m['pasos_media']:.1f}", int(es_mejor)])
        self.csv.flush()
        self.ultimo = self.num_timesteps
        self.historial.append(m["exito"])
        self.logger.record("validacion/exito", m["exito"])
        self.logger.record("validacion/colision", m["colision"])

    def _on_step(self) -> bool:
        if self.num_timesteps >= self.proxima:
            self.proxima += self.cada
            self._validar()
        return True

    def _on_training_end(self) -> None:
        if self.num_timesteps != self.ultimo:
            self._validar()
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
    ap.add_argument("--buffer", type=Path, default=None,
                    help="búfer de repetición guardado (.pkl) para cargar junto con --desde")
    ap.add_argument("--dispositivo", choices=["auto", "cpu", "cuda"], default="auto",
                    help="dónde se entrena la red. La evaluación de M4 se hace SIEMPRE en CPU")
    ap.add_argument("--set", dest="cambios", action="append", default=[], metavar="CLAVE=VALOR",
                    help="cambia un valor de la configuración, p. ej. sac.learning_rate=0.0001 o "
                         "sac.net_arch=[512,512]; repetible")
    ap.add_argument("--etiqueta", default="", help="se añade al nombre de la carpeta de la corrida")
    ap.add_argument("--hilos", type=int, default=None,
                    help="hilos de PyTorch; al correr varios entrenamientos a la vez conviene 2-3 "
                         "por corrida para no sobresuscribir la CPU")
    a = ap.parse_args()
    if a.hilos:
        import torch
        torch.set_num_threads(a.hilos)
    cfg = aplicar_cambios(cargar_config(a.config), a.cambios)
    pasos = a.pasos or cfg["entrenamiento"]["pasos_totales"]
    semilla = cfg["entrenamiento"]["semilla"] if a.semilla is None else a.semilla

    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    nombre = f"{a.config}_{a.etiqueta}" if a.etiqueta else a.config
    carpeta = RAIZ / "training" / "runs" / f"{nombre}_s{semilla}_{fecha}"
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "config.yaml").write_text(yaml.safe_dump(
        {**cfg, "pasos_usados": pasos, "semilla_usada": semilla, "cambios": a.cambios}))

    E = cfg["entorno"]
    kwargs = {"escenario": E["escenario"], "recompensa": E["recompensa"]}
    if E.get("muestreo"):
        kwargs["muestreo"] = E["muestreo"]
    if E.get("pares_archivo"):
        ruta_pares = Path(E["pares_archivo"])
        kwargs["pares"] = contrato.pares_kit(ruta_pares if ruta_pares.is_absolute() else RAIZ / ruta_pares,
                                             E.get("pares_ids"))
    venv = make_vec_env(EntornoE6, n_envs=E["n_entornos"], seed=semilla, vec_env_cls=SubprocVecEnv,
                        env_kwargs=kwargs)
    S = cfg["sac"]
    clase, extra, politica = SAC, {}, {"net_arch": S["net_arch"]}
    if S["algoritmo"] == "TQC":
        from sb3_contrib import TQC
        clase = TQC
        politica["n_quantiles"] = S["tqc"]["n_cuantiles"]
        extra["top_quantiles_to_drop_per_net"] = S["tqc"]["descartados"]
    if E.get("demos"):
        ruta_demos = Path(E["demos"])
        with np.load(ruta_demos if ruta_demos.is_absolute() else RAIZ / ruta_demos) as f:
            extra["replay_buffer_class"] = BufferConDemos
            extra["replay_buffer_kwargs"] = {"demos": {k: f[k] for k in f.files}}
    if a.desde:
        modelo = clase.load(a.desde, env=venv, device=a.dispositivo,
                            tensorboard_log=str(carpeta / "tensorboard"))
        (carpeta / "continua_desde.txt").write_text(str(a.desde) + "\n")
        modelo.learning_starts = modelo.num_timesteps + S["learning_starts"]
        if a.buffer:
            modelo.load_replay_buffer(a.buffer)
            modelo.learning_starts = modelo.num_timesteps
    else:
        modelo = clase("MlpPolicy", venv, learning_rate=S["learning_rate"], buffer_size=S["buffer_size"],
                       learning_starts=S["learning_starts"], batch_size=S["batch_size"], tau=S["tau"],
                       gamma=S["gamma"], train_freq=S["train_freq"], gradient_steps=S["gradient_steps"],
                       ent_coef=S["ent_coef"], policy_kwargs=politica, seed=semilla,
                       device=a.dispositivo, tensorboard_log=str(carpeta / "tensorboard"), verbose=0, **extra)
    callbacks = [Evaluacion(cfg, carpeta)]
    validacion = None
    if cfg["evaluacion"].get("validacion"):
        validacion = Validacion(cfg, carpeta)
        callbacks.append(validacion)
    if cfg.get("curriculo"):
        callbacks.append(Curriculo(cfg["curriculo"], pasos))
    if cfg.get("estructuradas"):
        callbacks.append(CurriculoEstructuradas(cfg["estructuradas"], pasos))
    parada = cfg["entrenamiento"]["parada"]
    vigilante = None
    if parada["activa"] and validacion is not None:
        vigilante = ParadaDivergencia(parada, validacion, carpeta)
        callbacks.append(vigilante)
    if S["ent_max"] is not None:
        callbacks.append(AcotarEntropia(S["ent_max"]))
    if cfg["entrenamiento"]["guardar_buffer"]:
        callbacks.append(GuardarBuffer(carpeta))
    modelo.learn(total_timesteps=pasos, callback=callbacks, progress_bar=False,
                 reset_num_timesteps=a.desde is None)
    modelo.save(carpeta / "modelo_final")
    estado = {"pasos_totales": int(modelo.num_timesteps)}
    if vigilante is not None and vigilante.motivo:
        estado["detenida_por"] = vigilante.motivo
    (carpeta / "estado.json").write_text(json.dumps(estado))
    venv.close()
    print(f"modelo en {carpeta}")


if __name__ == "__main__":
    main()
