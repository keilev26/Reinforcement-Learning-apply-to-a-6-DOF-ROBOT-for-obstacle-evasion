from pathlib import Path

import numpy as np
import pytest
import yaml

from gym_env import kit
from gym_env.entorno import EntornoE6
from shared_scenarios import contrato
from training.entrenar_sac import cargar_config

RAIZ = Path(__file__).resolve().parents[2]
SHARED = RAIZ / "shared_scenarios"
PICK, PLACE = np.array([0.0, -0.30, 0.05]), np.array([0.30, 0.0, 0.10])


@pytest.fixture(scope="module")
def pares():
    return {q["id"]: q for q in contrato.pares_kit(SHARED / "pares_kit.yaml")}


@pytest.fixture(scope="module")
def env(pares):
    e = EntornoE6(muestreo="kit", pares=[pares[i] for i in ("N0", "N1", "N2")])
    yield e
    e.close()


def test_muestreo_es_reproducible_y_dentro_de_rango():
    cuentas = []
    for semilla in range(30):
        et1, o1 = kit.muestrear(np.random.default_rng(semilla), PICK, PLACE)
        et2, o2 = kit.muestrear(np.random.default_rng(semilla), PICK, PLACE)
        assert et1 == et2 and o1 == o2
        assert 1 <= len(o1) <= 6
        cuentas.append(len(o1))
        for o in o1:
            assert np.hypot(o["pose"][0], o["pose"][1]) <= kit.RADIO_MAX_M + 0.1
            assert o["pose"][2] > 0.0
    assert len(set(cuentas)) > 2


def test_el_muestreo_no_tapa_los_pasillos_con_piezas_altas():
    for semilla in range(60):
        rng = np.random.default_rng(semilla)
        etiqueta, obst = kit.muestrear(rng, PICK, PLACE)
        piezas = []
        for texto in etiqueta.split(" ", 2)[2].split(";"):
            codigo, resto = texto.split("(")
            x, y, yaw = (int(v) for v in resto.rstrip(")").split(","))
            piezas.append((codigo, x, y, yaw))
        assert kit.conflictos(piezas, PICK[:2], PLACE[:2]) == []


def test_objeto_kit_apoya_en_la_mesa():
    o = kit.objeto_kit(0, ("T03", 225, -225, 0))
    assert o["forma"] == "cilindro" and o["dims"] == [0.45, 0.015]
    assert o["pose"][2] == pytest.approx(0.225)
    viga = kit.objeto_kit(1, ("P08", 225, -175, 90, 0.35))
    assert viga["pose"][2] == pytest.approx(0.36)
    assert viga["pose"][5] == pytest.approx(np.pi / 2, abs=1e-3)


def test_par_distinto_cambia_la_meta_y_se_restaura_el_nominal(env, pares):
    env.reset(options={"obstaculos": [], "etiqueta": "x", "par": pares["N1"]})
    assert np.allclose(env.p_meta, pares["N1"]["place"])
    assert env.L == pytest.approx(np.linalg.norm(np.array(pares["N1"]["place"]) - np.array(pares["N1"]["pick"])))
    assert env.L_obs == pytest.approx(np.linalg.norm(PLACE - PICK))
    obs_antes, _ = env.reset(options={"obstaculos": [], "etiqueta": "x", "par": env.par_nominal})
    assert np.allclose(env.p_meta, PLACE)
    nominal = EntornoE6()
    obs_nominal, _ = nominal.reset(options={"obstaculos": [], "etiqueta": "x"})
    nominal.close()
    assert np.allclose(obs_antes, obs_nominal, atol=1e-5)


def test_el_entrenamiento_sortea_pares_y_obstaculos(env):
    metas, n_obst = set(), set()
    for _ in range(25):
        obs, info = env.reset()
        assert obs.shape == env.observation_space.shape
        metas.add(tuple(np.round(np.concatenate([env.p_pick, env.p_meta]), 3)))
        n_obst.add(len(env.esc.obstaculos))
    assert len(metas) == 3
    assert len(n_obst) > 2


def test_el_entorno_por_defecto_no_cambia():
    e = EntornoE6()
    assert e.muestreo == "contrato" and e.pares is None
    e.reset()
    assert np.allclose(e.p_meta, PLACE) and len(e.esc.obstaculos) <= 1
    e.close()


def test_conjuntos_del_kit(pares):
    evaluacion = yaml.safe_load((SHARED / "kit_evaluacion.yaml").read_text())
    assert len(evaluacion["escenas"]) >= 150
    assert set(evaluacion["pares_vistos"]).isdisjoint(evaluacion["pares_no_vistos"])
    assert set(evaluacion["pares_vistos"] + evaluacion["pares_no_vistos"]) <= set(pares)
    etiquetas = [e["etiqueta"] for e in evaluacion["escenas"]]
    assert len(set(etiquetas)) == len(etiquetas)
    for e in evaluacion["escenas"]:
        if "par" in e:
            assert e["par"]["id"] in pares
    claves = lambda escenas: {tuple((o["forma"], tuple(round(d, 4) for d in o["dims"]), tuple(round(v, 3) for v in o["pose"][:3]))
                                    for o in e["obstaculos"]) + ((e["par"]["id"],) if "par" in e else ()) for e in escenas}
    for nombre in ("kit_validacion.yaml", "kit_validacion_pares.yaml"):
        val = yaml.safe_load((SHARED / nombre).read_text())["escenas"]
        assert len(val) >= 195
        assert claves(val).isdisjoint(claves(evaluacion["escenas"]))


def test_las_escenas_con_par_se_pueden_reiniciar():
    escenas = contrato.escenas_con_par(SHARED / "kit_evaluacion.yaml")
    e = EntornoE6()
    for etiqueta, obst, par in escenas[::40]:
        opciones = {"obstaculos": obst, "etiqueta": etiqueta}
        if par:
            opciones["par"] = par
        e.reset(options=opciones)
        assert e.etiqueta == etiqueta
    e.close()


def test_configuraciones_v3():
    v3, v3p = cargar_config("sac_v3"), cargar_config("sac_v3p")
    assert v3["entorno"]["muestreo"] == "kit" and not v3["entorno"].get("pares_archivo")
    assert v3p["entorno"]["pares_ids"] == ["N0", "N1", "N2", "N3", "N7"]
    assert v3["entrenamiento"]["pasos_totales"] == v3p["entrenamiento"]["pasos_totales"]
    assert v3["evaluacion"]["validacion"]["archivo"].endswith("kit_validacion.yaml")
    assert v3p["evaluacion"]["validacion"]["archivo"].endswith("kit_validacion_pares.yaml")
    assert not v3["entorno"]["recompensa"].get("quieto")
