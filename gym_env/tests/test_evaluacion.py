import numpy as np
import pytest

from evaluation.evaluar_linea_base import Evaluador
from gym_env.controladores import recta_con_frenado
from gym_env.entorno import EntornoE6


@pytest.fixture(scope="module")
def ev():
    return Evaluador()


@pytest.fixture(scope="module")
def recorrido():
    env = EntornoE6()
    T = env.C["tarea_nominal"]
    env.esc.poner_obstaculos([])
    q_place = env.esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], T["q_inicial_rad"])
    resultados = {}
    for escenario, variante in [(1, "1"), (7, "7 holgura=0.08")]:
        _, info = env.reset(options={"escenario": escenario, "variante": variante})
        qs, fin = [info["q"]], False
        while not fin:
            _, _, te, tr, info = env.step(recta_con_frenado(env, q_place, info["q"], env.dq_prev))
            qs.append(info["q"]); fin = te or tr
        resultados[variante] = (np.array(qs), info)
    env.close()
    return resultados, env.dt


@pytest.mark.parametrize("variante", ["1", "7 holgura=0.08"])
def test_mismas_metricas_que_el_entorno(ev, recorrido, variante):
    (qs, info), dt = recorrido[0][variante], recorrido[1]
    registro = {"variante": variante, "planner": "prueba", "consulta": 0, "codigo": 1,
                "t_computo_ms": 0.0,
                "trayectoria": [[i * dt, *q] for i, q in enumerate(qs)]}
    fila = ev.evaluar(registro)
    assert fila["exito"] == info["exito"]
    assert fila["colisiones"] == info["colisiones"]
    assert fila["L_art_rad"] == pytest.approx(info["L_art_rad"], abs=1e-9)
    assert fila["L_cart_m"] == pytest.approx(info["L_cart_m"], abs=1e-9)
    assert fila["d_min_obstaculos_m"] == pytest.approx(info["d_min_obstaculos_m"], abs=1e-9)


def test_trayectoria_que_atraviesa_el_obstaculo(ev, recorrido):
    (qs, _), dt = recorrido[0]["1"], recorrido[1]
    fila = ev.evaluar({"variante": "2", "planner": "prueba", "consulta": 0, "codigo": 1,
                       "t_computo_ms": 0.0, "trayectoria": [[i * dt, *q] for i, q in enumerate(qs)]})
    assert not fila["exito"] and fila["colisiones"] >= 1 and fila["d_min_obstaculos_m"] < 0


def test_plan_fallido_no_es_exito(ev):
    fila = ev.evaluar({"variante": "2", "planner": "prueba", "consulta": 0, "codigo": 99999,
                       "t_computo_ms": 5000.0, "trayectoria": []})
    assert fila["exito"] is False and fila["colisiones"] is None


def test_evaluador_de_politica_devuelve_las_5_metricas():
    from stable_baselines3 import SAC

    from evaluation.evaluar_linea_base import CAMPOS
    from evaluation.evaluar_politica import evaluar

    env = EntornoE6()
    fila = evaluar(SAC("MlpPolicy", env, seed=0, device="cpu"), env, "2", 0)
    env.close()
    assert set(fila) == set(CAMPOS)
    assert fila["t_computo_ms"] > 0 and fila["t_ejecucion_s"] > 0
