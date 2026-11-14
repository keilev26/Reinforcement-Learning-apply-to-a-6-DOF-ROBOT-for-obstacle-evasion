import gymnasium as gym
import numpy as np
import pybullet as p

from evaluation.metricas import ContadorMetricas
from geometry.distancia import D_MAX, ESLABONES_OBSERVADOS, MedidorDistancias
from gym_env import kit
from gym_env.escena import ESLABONES_MOVILES, Escena, contrato
from gym_env.robot_e6 import cargar_e6

RECOMPENSA_V0 = {
    "progreso": 10.0,
    "orientacion": 1.0,
    "d_seguridad_m": 0.02,
    "proximidad": 1.0,
    "suavidad": 0.05,
    "tiempo": 0.01,
    "quieto": 0.0,
    "umbral_quieto": 0.1,
    "colision": 10.0,
    "exito": 10.0,
    "precision": 0.0,
    "sigma_pos_m": 0.02,
    "sigma_ori_rad": 0.10,
}


RECOMPENSA_V1 = {**RECOMPENSA_V0, "orientacion": 5.0, "precision": 10.0}

RECOMPENSA_V2 = {**RECOMPENSA_V1, "quieto": 0.05}


def castigo_quieto(dq: np.ndarray, dq_max: float, dist_m: float, tol_m: float, w: dict) -> float:
    if w["quieto"] <= 0.0 or dist_m <= tol_m:
        return 0.0
    movimiento = float(np.linalg.norm(dq)) / (dq_max * np.sqrt(len(dq)))
    return w["quieto"] * max(0.0, 1.0 - movimiento / w["umbral_quieto"])


def potencial_precision(dist_m: float, ang_rad: float, w: dict) -> float:
    return float(np.exp(-dist_m / w["sigma_pos_m"]) * np.exp(-ang_rad / w["sigma_ori_rad"]))


class EntornoE6(gym.Env):
    metadata = {"render_modes": ["human"], "render_fps": 33}

    def __init__(self, escenario: int | None = None, variante: str | None = None,
                 recompensa: dict | None = None, render_mode: str | None = None,
                 muestreo: str = "contrato", pares: list | None = None,
                 pares_combinados: dict | None = None, estructuradas_familias: dict | None = None):
        super().__init__()
        self.C, self.M = contrato.cargar(), contrato.cargar_metricas()
        term, acc = self.M["terminacion"], self.M["accion"]
        self.dq_max = acc["delta_q_max_rad"]
        self.dt = term["periodo_control_s"]
        self.ddq_max = acc["aceleracion_max_rad_s2"] * self.dt ** 2
        self.subpasos = acc["subpasos_colision"]
        self.pasos_max = term["pasos_maximos"]
        self.tol_pos, self.tol_ori = term["tolerancia_posicion_m"], term["tolerancia_orientacion_rad"]
        self.w = {**RECOMPENSA_V0, **(recompensa or {})}
        self.escenario, self.variante = escenario, variante
        self.escala_max = None
        self.muestreo, self.pares = muestreo, pares
        self.p_estructuradas = 0.0
        self.pares_combinados = pares_combinados
        self.familias_cfg = estructuradas_familias or {}
        self.pares_validos = {}
        self.render_mode = render_mode

        self.cliente = p.connect(p.GUI if render_mode == "human" else p.DIRECT)
        self.m = cargar_e6(self.cliente)
        self.esc = Escena(self.m, self.C)
        eslabones = {n: (self.m.cuerpo, self.m.eslabones[n]) for n in ESLABONES_OBSERVADOS if n != "efector"}
        eslabones["efector"] = (self.esc.efector, -1)
        self.medidor = MedidorDistancias(self.cliente, eslabones)
        todos = {n: (self.m.cuerpo, self.m.eslabones[n]) for n in ESLABONES_MOVILES}
        todos["efector"] = (self.esc.efector, -1)
        self.metricas = ContadorMetricas(
            self.esc, MedidorDistancias(self.cliente, todos, tuple(todos), d_max=1.0),
            self.subpasos, self.M["m2_colisiones"]["histeresis_m"], self.C["efector"]["largo_m"])

        T = self.C["tarea_nominal"]
        self.rpy_pick, self.rpy_meta = T["p_pick"]["rpy"], T["p_place"]["rpy"]
        self.quat_meta = np.array(p.getQuaternionFromEuler(self.rpy_meta))
        self.p_pick = np.array(T["p_pick"]["pos"])
        self.p_meta = np.array(T["p_place"]["pos"])
        self.L = float(np.linalg.norm(self.p_meta - self.p_pick))
        self.L_obs = self.L
        self.par_nominal = {"pick": self.p_pick.tolist(), "place": self.p_meta.tolist()}
        self.esc.poner_obstaculos([])
        self.q_pick_ref = self.esc.ik_tcp(T["p_pick"]["pos"], T["p_pick"]["rpy"], T["q_inicial_rad"])
        if self.q_pick_ref is None:
            raise RuntimeError("p_pick sin cinemática inversa libre de colisión en la celda vacía")
        self.q_referencias = {tuple(np.round(self.p_pick, 5)): self.q_pick_ref}

        self.action_space = gym.spaces.Box(-1.0, 1.0, (6,), np.float32)
        n = len(ESLABONES_OBSERVADOS)
        self.observation_space = gym.spaces.Box(-3.0, 3.0, (6 + 6 + 3 + 4 + n + 3 * n,), np.float32)


    def _errores(self):
        pos, quat = self.metricas.tcp()
        d = p.getDifferenceQuaternion(quat, self.quat_meta)
        d = np.array(d) if d[3] >= 0 else -np.array(d)
        ang = 2 * np.arctan2(np.linalg.norm(d[:3]), d[3])
        return self.p_meta - pos, d, float(ang), pos


    def _observar(self, medida):
        e_pos, e_quat, _, _ = self._errores()
        q_norm = 2 * (self.q - self.m.q_min) / (self.m.q_max - self.m.q_min) - 1
        return np.concatenate([q_norm, self.dq_prev / self.dq_max, e_pos / self.L_obs, e_quat,
                               medida.distancia / D_MAX, medida.direccion.ravel()]).clip(-3, 3).astype(np.float32)


    def fijar_par(self, par: dict) -> None:
        self.p_pick, self.p_meta = np.array(par["pick"], dtype=float), np.array(par["place"], dtype=float)
        self.L = float(np.linalg.norm(self.p_meta - self.p_pick))
        clave = tuple(np.round(self.p_pick, 5))
        if clave not in self.q_referencias:
            self.esc.poner_obstaculos([])
            q = self.esc.ik_tcp(self.p_pick, self.rpy_pick, self.q_referencias[tuple(np.round(self.par_nominal["pick"], 5))])
            if q is None:
                raise RuntimeError(f"par sin cinemática inversa libre en recoger: {par}")
            self.q_referencias[clave] = q
        self.q_pick_ref = self.q_referencias[clave]

    def _elegir_par(self, opciones: dict) -> None:
        par = opciones.get("par")
        if par is None and self.pares_combinados and self.np_random.random() >= self.pares_combinados["p_fijos"]:
            par = self._par_combinado()
        if par is None and self.pares:
            par = self.pares[int(self.np_random.integers(len(self.pares)))]
        self.fijar_par(par or self.par_nominal)

    def _par_combinado(self) -> dict | None:
        c = self.pares_combinados
        n = int(round(c["radio_m"] / c["paso_m"]))
        nom = self.par_nominal
        for _ in range(8):
            d = self.np_random.integers(-n, n + 1, size=4) * c["paso_m"]
            pick = np.array([nom["pick"][0] + d[0], nom["pick"][1] + d[1], nom["pick"][2]])
            place = np.array([nom["place"][0] + d[2], nom["place"][1] + d[3], nom["place"][2]])
            clave = (tuple(np.round(pick, 5)), tuple(np.round(place, 5)))
            if clave not in self.pares_validos:
                self.pares_validos[clave] = self._par_resoluble(pick, place)
            if self.pares_validos[clave]:
                return {"pick": pick.tolist(), "place": place.tolist()}
        return None

    def _par_resoluble(self, pick, place) -> bool:
        try:
            self.fijar_par({"pick": pick, "place": place})
        except RuntimeError:
            return False
        self.esc.poner_obstaculos([])
        return self.esc.ik_tcp(self.p_meta, self.rpy_meta, self.q_pick_ref, intentos=10) is not None

    def fijar_p_estructuradas(self, p: float) -> None:
        self.p_estructuradas = float(p)

    def _sorteo_con_kit(self, esc_n, opciones) -> bool:
        return self.muestreo == "kit" and esc_n is None and "obstaculos" not in opciones

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        opciones = options or {}
        esc_n = opciones.get("escenario", self.escenario)
        var = opciones.get("variante", self.variante)
        self._elegir_par(opciones)
        sorteo_kit = self._sorteo_con_kit(esc_n, opciones)
        q0 = None
        for _ in range(20):
            if "obstaculos" in opciones:
                self.etiqueta, obst = opciones.get("etiqueta", "escena dada"), opciones["obstaculos"]
            elif sorteo_kit and self.np_random.random() < self.p_estructuradas:
                self.etiqueta, obst = kit.muestrear_estructurada(self.np_random, self.p_pick, self.p_meta,
                                                                    self.familias_cfg.get("excluir", ()), self.familias_cfg.get("pesos"))
            elif sorteo_kit:
                self.etiqueta, obst = kit.muestrear(self.np_random, self.p_pick, self.p_meta)
            elif esc_n is None:
                self.etiqueta, obst = contrato.muestrear_entrenamiento(self.C, self.np_random,
                                                                       self.escala_max)
            else:
                vs = contrato.variantes(self.C, esc_n)
                self.etiqueta, obst = next((v for v in vs if v[0] == var), vs[0]) if var else vs[0]
            self.esc.poner_obstaculos(obst)
            q0 = self.q_pick_ref
            if self.esc.en_colision(q0):
                q0 = self.esc.ik_tcp(self.p_pick, self.rpy_pick, self.q_pick_ref)
            if q0 is not None and sorteo_kit and self.esc.ik_tcp(self.p_meta, self.rpy_meta, q0, intentos=10) is None:
                q0 = None
            if q0 is not None:
                break
            if esc_n is not None or "obstaculos" in opciones:
                raise RuntimeError(f"{self.etiqueta}: p_pick sin solución libre de colisión")
        if q0 is None:
            self.etiqueta = "1"
            self.esc.poner_obstaculos([])
            q0 = self.q_pick_ref
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
        dq = np.clip(a * self.dq_max, self.dq_prev - self.ddq_max, self.dq_prev + self.ddq_max)
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
             - castigo_quieto(dq, self.dq_max, dist_meta, self.tol_pos, w)
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

    def fijar_escala_max(self, valor) -> None:
        self.escala_max = valor

    def close(self):
        if p.isConnected(self.cliente):
            p.disconnect(self.cliente)
