import numpy as np
import pytest
from gymnasium.utils.env_checker import check_env

from gym_env.controladores import recta_con_frenado
from gym_env.entorno import EntornoE6


@pytest.fixture(scope="module")
def env():
    e = EntornoE6()
    yield e
    e.close()


@pytest.fixture(scope="module")
def q_place(env):
    T = env.C["tarea_nominal"]
    env.esc.poner_obstaculos([])
    return env.esc.ik_tcp(T["p_place"]["pos"], T["p_place"]["rpy"], T["q_inicial_rad"])


def recta(env, q_place, **opciones):
    _, info = env.reset(options=opciones)
    terminado = truncado = False
    while not (terminado or truncado):
        a = recta_con_frenado(env, q_place, info["q"], env.dq_prev)
        _, _, terminado, truncado, info = env.step(a)
    return info


def test_cumple_la_api_de_gymnasium(env):
    check_env(env, skip_render_check=True)


def test_espacios_del_mdp(env):
    assert env.action_space.shape == (6,)
    assert env.observation_space.shape == (43,)
    assert env.dq_max == 0.05 and env.subpasos == 3 and env.pasos_max == 300


def test_accion_acotada(env):
    _, info = env.reset(seed=1, options={"escenario": 1})
    q0 = info["q"]
    _, _, _, _, info = env.step(np.full(6, 5.0))
    assert np.max(np.abs(info["q"] - q0)) <= 0.05 + 1e-9


def test_aceleracion_acotada(env):
    assert env.ddq_max == pytest.approx(4.72 * 0.03 ** 2)
    _, info = env.reset(seed=1, options={"escenario": 1})
    qs = [info["q"]]
    for a in [np.ones(6)] * 15 + [-np.ones(6)] * 15:
        _, _, te, tr, info = env.step(a)
        qs.append(info["q"])
        if te or tr:
            break
    dq = np.diff(qs, axis=0)
    assert np.max(np.abs(np.diff(dq, axis=0))) <= env.ddq_max + 1e-9
    assert np.max(np.abs(dq)) <= env.dq_max + 1e-9


def test_reproducible_con_semilla(env):
    a, _ = env.reset(seed=7)
    b, _ = env.reset(seed=7)
    np.testing.assert_array_equal(a, b)


def test_espacio_libre_se_resuelve_sin_chocar(env, q_place):
    info = recta(env, q_place, escenario=1)
    assert info["exito"] and info["colisiones"] == 0
    assert info["error_pos_m"] <= env.tol_pos


@pytest.mark.parametrize("escenario,variante", [(2, None), (5, "5 k=2.0")])
def test_obstaculo_detiene_la_recta(env, q_place, escenario, variante):
    info = recta(env, q_place, escenario=escenario, variante=variante)
    assert not info["exito"] and info["colisiones"] >= 1
    assert info["d_min_obstaculos_m"] <= 0


def test_paso_estrecho_se_cruza_con_holgura(env, q_place):
    info = recta(env, q_place, escenario=7, variante="7 holgura=0.08")
    assert info["exito"] and info["colisiones"] == 0
    assert 0 < info["d_min_obstaculos_m"] < 0.02


def test_observacion_de_distancias(env):
    obs, _ = env.reset(options={"escenario": 2})
    distancias = obs[19:25]
    direcciones = obs[25:43].reshape(6, 3)
    assert np.all(distancias <= 1.0)
    cerca = distancias < 1.0
    np.testing.assert_allclose(np.linalg.norm(direcciones[cerca], axis=1), 1.0, atol=1e-4)


def test_distancias_concuerdan_con_fcl():
    pytest.importorskip("fcl")
    from geometry.validar_fcl import informe, validar
    r = informe(validar(perturbadas=1, escenarios=[2]))
    assert r["error_max_mm"] < 1.5
    assert r["discrepancias_fuera_de_banda"] == 0
