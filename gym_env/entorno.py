"""Paquetes 3.2 y 3.3 — Entorno Gymnasium del Magician E6 con el MDP del proyecto.

Tarea: llevar el TCP de p_pick a p_place (contrato v2.0) sin chocar. Todos los parámetros del MDP
salen de `shared_scenarios/metricas.yaml` y la geometría de `escenarios.yaml`:

  Acción       a ∈ [-1, 1]^6  ->  Δq = a · 0.05 rad, recortada a los límites articulares
  Transición   cinemática: q <- q + Δq cada 30 ms (el período de ServoJ del E6 real)
  Colisiones   cada paso se revisa en 3 subpasos (<= 0.017 rad)
  Observación  43 valores, todos calculables en el robot real:
                 q normalizado (6) · Δq anterior / Δq_max (6) · error de posición / L (3)
                 · error de orientación como cuaternión (4) · distancia / d_max por eslabón (6)
                 · dirección unitaria al obstáculo más cercano por eslabón (18)
  Fin          éxito (5 mm y 0.05 rad) o colisión: terminated; 300 pasos: truncated

La recompensa es la v0, para que el entorno funcione de punta a punta. La formal es el paquete 3.4
(semana 8); sus pesos se pasan en `recompensa=` sin tocar este archivo.

Uso:
    env = EntornoE6()                                   # escenas aleatorias de entrenamiento
    env = EntornoE6(escenario=5, variante="5 k=2.0")    # una variante fija del contrato
    obs, info = env.reset(seed=0)
"""
import gymnasium as gym
import numpy as np
import pybullet as p

from evaluation.metricas import ContadorMetricas
from geometry.distancia import D_MAX, ESLABONES_OBSERVADOS, MedidorDistancias
from gym_env.escena import ESLABONES_MOVILES, Escena, contrato
from gym_env.robot_e6 import cargar_e6

# Recompensa v0. Longitudes normalizadas por L, la longitud de la tarea (propuesta, sección 1.2.6).
RECOMPENSA_V0 = {
    "progreso": 10.0,        # por cada L de acercamiento del TCP a la meta
    "orientacion": 1.0,      # por cada rad de reducción del error angular
    "d_seguridad_m": 0.02,   # umbral de la penalización por proximidad (~0.05 L)
    "proximidad": 1.0,       # penalización máxima por paso al tocar el umbral de 0 m
    "suavidad": 0.05,        # por el cambio de acción (Δq - Δq_anterior)^2 normalizado
    "tiempo": 0.01,          # por paso
    "colision": 10.0,        # al chocar (termina el episodio)
    "exito": 10.0,           # al llegar (termina el episodio)
    # Términos de la v1 (paquete 3.4); en 0 la recompensa es exactamente la v0.
    "precision": 0.0,        # peso del potencial de precisión conjunta posición-orientación
    "sigma_pos_m": 0.02,     # escala del potencial en posición
    "sigma_ori_rad": 0.10,   # escala del potencial en orientación
}


# Recompensa v1 (paquete 3.4, 2026-09-29): la v0 con la orientación reequilibrada y el potencial
# de precisión. Elegida frente a "solo orientación" en docs/semana-07/resumen-semana-07.md:
# a 300 000 pasos, 3 de 4 variantes resueltas frente a 0.
RECOMPENSA_V1 = {**RECOMPENSA_V0, "orientacion": 5.0, "precision": 10.0}


def potencial_precision(dist_m: float, ang_rad: float, w: dict) -> float:
    """Φ = exp(-d/σp) · exp(-θ/σo): vale 1 solo si posición Y orientación están cerca de la meta.

    Entra en la recompensa como diferencia Φ(s') - Φ(s) (moldeado por potencial): da gradiente
    fuerte cerca de la meta sin cambiar la política óptima. Un bono por paso, en cambio, pagaría
    por quedarse rondando la meta en vez de terminar el episodio.
    """
    return float(np.exp(-dist_m / w["sigma_pos_m"]) * np.exp(-ang_rad / w["sigma_ori_rad"]))


class EntornoE6(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 33}

    def __init__(self, escenario: int | None = None, variante: str | None = None,
                 recompensa: dict | None = None, render_mode: str | None = None):
        super().__init__()
        self.C, self.M = contrato.cargar(), contrato.cargar_metricas()
        term, acc = self.M["terminacion"], self.M["accion"]
        self.dq_max = acc["delta_q_max_rad"]
        self.subpasos = acc["subpasos_colision"]
        self.pasos_max = term["pasos_maximos"]
        self.tol_pos, self.tol_ori = term["tolerancia_posicion_m"], term["tolerancia_orientacion_rad"]
        self.dt = term["periodo_control_s"]
        self.w = {**RECOMPENSA_V0, **(recompensa or {})}
        self.escenario, self.variante = escenario, variante
        self.render_mode = render_mode

        self.cliente = p.connect(p.GUI if render_mode == "human" else p.DIRECT)
        self.m = cargar_e6(self.cliente)
        self.esc = Escena(self.m, self.C)
        eslabones = {n: (self.m.cuerpo, self.m.eslabones[n]) for n in ESLABONES_OBSERVADOS if n != "efector"}
        eslabones["efector"] = (self.esc.efector, -1)
        self.medidor = MedidorDistancias(self.cliente, eslabones)
        # M2, M3 y M5 con el mismo contador que usa el evaluador de la línea base. M5 abarca
        # todos los eslabones móviles y el efector, no solo los observados.
        todos = {n: (self.m.cuerpo, self.m.eslabones[n]) for n in ESLABONES_MOVILES}
        todos["efector"] = (self.esc.efector, -1)
        self.metricas = ContadorMetricas(
            self.esc, MedidorDistancias(self.cliente, todos, tuple(todos), d_max=1.0),
            self.subpasos, self.M["m2_colisiones"]["histeresis_m"], self.C["efector"]["largo_m"])

        T = self.C["tarea_nominal"]
        self.p_meta = np.array(T["p_place"]["pos"])
        self.quat_meta = np.array(p.getQuaternionFromEuler(T["p_place"]["rpy"]))
        self.L = float(np.linalg.norm(self.p_meta - np.array(T["p_pick"]["pos"])))
        self.esc.poner_obstaculos([])
        self.q_pick_ref = self.esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], T["q_inicial_rad"])
        if self.q_pick_ref is None:
            raise RuntimeError("p_pick sin cinemática inversa libre de colisión en la celda vacía")

        self.action_space = gym.spaces.Box(-1.0, 1.0, (6,), np.float32)
        # Todas las componentes quedan en [-1, 1] salvo el error de posición / L: el TCP nunca está
        # a más de ~0.95 m de la meta (2.2 L). Se recorta a [-3, 3] por seguridad.
        n = len(ESLABONES_OBSERVADOS)
        self.observation_space = gym.spaces.Box(-3.0, 3.0, (6 + 6 + 3 + 4 + n + 3 * n,), np.float32)

    # ------------------------------------------------------------------ geometría de la tarea

    def _errores(self):
        pos, quat = self.metricas.tcp()
        d = p.getDifferenceQuaternion(quat, self.quat_meta)      # rotación de la actual a la meta
        d = np.array(d) if d[3] >= 0 else -np.array(d)
        ang = 2 * np.arctan2(np.linalg.norm(d[:3]), d[3])
        return self.p_meta - pos, d, float(ang), pos

    # ------------------------------------------------------------------ observación

    def _observar(self, medida):
        e_pos, e_quat, _, _ = self._errores()
        q_norm = 2 * (self.q - self.m.q_min) / (self.m.q_max - self.m.q_min) - 1
        return np.concatenate([q_norm, self.dq_prev / self.dq_max, e_pos / self.L, e_quat,
                               medida.distancia / D_MAX, medida.direccion.ravel()]).clip(-3, 3).astype(np.float32)

    # ------------------------------------------------------------------ API de Gymnasium

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        opciones = options or {}
        esc_n = opciones.get("escenario", self.escenario)
        var = opciones.get("variante", self.variante)
        for _ in range(20):
            if esc_n is None:
                self.etiqueta, obst = contrato.muestrear_entrenamiento(self.C, self.np_random)
            else:
                vs = contrato.variantes(self.C, esc_n)
                self.etiqueta, obst = next((v for v in vs if v[0] == var), vs[0]) if var else vs[0]
            self.esc.poner_obstaculos(obst)
            q0 = self.q_pick_ref
            if self.esc.en_colision(q0):
                T = self.C["tarea_nominal"]
                q0 = self.esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], self.q_pick_ref)
            if q0 is not None:
                break
            if esc_n is not None:
                raise RuntimeError(f"{self.etiqueta}: p_pick sin solución libre de colisión")
        self.q = np.array(q0, dtype=float)
        self.metricas.reiniciar(self.q)
        self.dq_prev = np.zeros(6)
        self.pasos = 0
        medida = self.medidor.medir(self.esc.celda + self.esc.obstaculos)
        e_pos, _, self.err_ang, _ = self._errores()
        self.dist_meta = float(np.linalg.norm(e_pos))
        return self._observar(medida), self._info(False)

    def step(self, accion):
        a = np.clip(np.asarray(accion, dtype=float), -1.0, 1.0)
        dq = a * self.dq_max
        q_nuevo = np.clip(self.q + dq, self.m.q_min, self.m.q_max)
        dq = q_nuevo - self.q

        choco = self.metricas.paso(self.q, q_nuevo)
        self.q = q_nuevo
        medida = self.medidor.medir(self.esc.celda + self.esc.obstaculos)
        e_pos, _, err_ang, _ = self._errores()
        dist_meta = float(np.linalg.norm(e_pos))
        self.pasos += 1

        exito = dist_meta <= self.tol_pos and err_ang <= self.tol_ori and not choco
        w = self.w
        r = (w["progreso"] * (self.dist_meta - dist_meta) / self.L
             + w["orientacion"] * (self.err_ang - err_ang)
             - w["proximidad"] * max(0.0, 1.0 - medida.d_min / w["d_seguridad_m"])
             - w["suavidad"] * float(np.sum(((dq - self.dq_prev) / self.dq_max) ** 2)) / 6
             - w["tiempo"]
             + w["precision"] * (potencial_precision(dist_meta, err_ang, w)
                                 - potencial_precision(self.dist_meta, self.err_ang, w)))
        if choco:
            r -= w["colision"]
        if exito:
            r += w["exito"]
        self.dist_meta, self.err_ang, self.dq_prev = dist_meta, err_ang, dq

        terminado = exito or choco
        truncado = self.pasos >= self.pasos_max and not terminado
        return self._observar(medida), float(r), terminado, truncado, self._info(exito)

    def _info(self, exito):
        return {"escena": self.etiqueta, "exito": exito, "pasos": self.pasos,
                "colisiones": self.metricas.colisiones, "error_pos_m": self.dist_meta,
                "error_ori_rad": self.err_ang, "L_cart_m": self.metricas.L_cart,
                "L_art_rad": self.metricas.L_art, "d_min_obstaculos_m": self.metricas.d_min_obst,
                "t_ejecucion_s": self.pasos * self.dt,
                "q": self.q.copy()}

    def close(self):
        if p.isConnected(self.cliente):
            p.disconnect(self.cliente)
