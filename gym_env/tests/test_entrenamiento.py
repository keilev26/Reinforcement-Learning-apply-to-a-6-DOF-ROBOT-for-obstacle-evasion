import json
from pathlib import Path

import pytest
import yaml

from gym_env.escena import contrato
from training import lanzar_barrido
import numpy as np
import torch
from gymnasium import spaces

from training.entrenar_sac import (AcotarEntropia, BufferConDemos, Validacion, aplicar_cambios, cargar_config,
                                   criterio_mejor, debe_detener)

RAIZ = Path(__file__).resolve().parents[2]


def clave_escena(obstaculos):
    return tuple((o["forma"], tuple(round(d, 5) for d in o["dims"]), tuple(round(v, 4) for v in o["pose"][:3]))
                 for o in obstaculos)


def test_cambios_por_linea_de_comandos():
    cfg = cargar_config("sac_v1")
    nuevo = aplicar_cambios(cfg, ["sac.learning_rate=1e-4", "sac.net_arch=[512, 512]", "sac.ent_coef=auto",
                                  "evaluacion.validacion.cada_pasos=1000"])
    assert nuevo["sac"]["learning_rate"] == pytest.approx(1e-4)
    assert nuevo["sac"]["net_arch"] == [512, 512]
    assert nuevo["sac"]["ent_coef"] == "auto"
    assert nuevo["evaluacion"]["validacion"]["cada_pasos"] == 1000
    assert cfg["sac"]["learning_rate"] == pytest.approx(3e-4)


@pytest.mark.parametrize("cambio", ["sac.lerning_rate=1", "sac.nueva.clave=1", "sin_igual"])
def test_cambios_invalidos_no_pasan_en_silencio(cambio):
    with pytest.raises((KeyError, ValueError)):
        aplicar_cambios(cargar_config("sac_v1"), [cambio])


def test_criterio_del_mejor_punto():
    base = {"exito": 0.40, "colision": 0.10, "error_mm": 20.0}
    assert criterio_mejor(base, None)
    assert criterio_mejor({**base, "exito": 0.42}, base)
    assert not criterio_mejor({**base, "exito": 0.38, "colision": 0.0, "error_mm": 1.0}, base)
    assert criterio_mejor({**base, "colision": 0.06}, base)
    assert not criterio_mejor({**base, "error_mm": 25.0}, base)


def test_validacion_separada_de_la_evaluacion():
    va = contrato.escenas_evaluacion(contrato.RUTA_VALIDACION)
    ev = contrato.escenas_evaluacion()
    assert len(va) == 50 and all(et.startswith("V") for et, _ in va)
    assert not {clave_escena(o) for _, o in va} & {clave_escena(o) for _, o in ev}
    datos = yaml.safe_load(contrato.RUTA_VALIDACION.read_text())
    assert datos["semilla"] not in {0, 1, 2, 3, 4, contrato.cargar_metricas()["protocolo"]["semilla_conjunto"]}


def test_validacion_ampliada_contiene_a_la_original_y_no_toca_la_evaluacion():
    ruta = contrato.RUTA_VALIDACION.with_name("validacion_200.yaml")
    va50 = contrato.escenas_evaluacion(contrato.RUTA_VALIDACION)
    va200 = contrato.escenas_evaluacion(ruta)
    ev = contrato.escenas_evaluacion()
    assert len(va200) == 200
    assert [clave_escena(o) for _, o in va200[:50]] == [clave_escena(o) for _, o in va50]
    assert not {clave_escena(o) for _, o in va200} & {clave_escena(o) for _, o in ev}


def test_el_callback_de_validacion_guarda_el_mejor(tmp_path):
    from stable_baselines3 import SAC
    from stable_baselines3.common.logger import configure
    from gym_env.entorno import EntornoE6
    cfg = cargar_config("sac_v1")
    env = EntornoE6()
    modelo = SAC("MlpPolicy", env, seed=0, device="cpu")
    modelo.set_logger(configure(None, []))
    cb = Validacion(cfg, tmp_path)
    cb.escenas = cb.escenas[:2]
    cb.init_callback(modelo)
    cb._validar()
    cb._validar()
    cb.csv.close()
    cb.env.close()
    env.close()
    filas = (tmp_path / "validacion.csv").read_text().splitlines()
    assert len(filas) == 3 and filas[1].endswith(",1") and filas[2].endswith(",0")
    assert (tmp_path / "mejor.zip").exists()
    assert set(json.loads((tmp_path / "mejor.json").read_text())) >= {"exito", "colision", "error_mm", "pasos"}


def test_barridos_declarados_son_validos():
    archivos = sorted((RAIZ / "training" / "barridos").glob("*.yaml"))
    assert archivos
    for archivo in archivos:
        barrido = yaml.safe_load(archivo.read_text())
        for c in lanzar_barrido.expandir(barrido):
            aplicar_cambios(cargar_config(c["config"]), [f"{k}={json.dumps(v)}" for k, v in (c.get("cambios") or {}).items()])
        nombres = [lanzar_barrido.nombre_corrida(c) for c in lanzar_barrido.expandir(barrido)]
        assert len(nombres) == len(set(nombres)), f"{archivo.name}: corridas repetidas"


def test_comando_del_lanzador():
    c = {"config": "sac_v1c", "semilla": 2, "pasos": 1000, "etiqueta": "x", "hilos": 2, "dispositivo": "cpu",
         "cambios": {"sac.net_arch": [512, 512], "sac.learning_rate": 0.0001}}
    cmd = lanzar_barrido.comando(c)
    assert cmd[1:3] == ["-m", "training.entrenar_sac"]
    assert cmd[cmd.index("--etiqueta") + 1] == "x"
    assert "sac.net_arch=[512, 512]" in cmd and "sac.learning_rate=0.0001" in cmd


def test_una_corrida_corta_no_cuenta_como_completada(tmp_path, monkeypatch):
    monkeypatch.setattr(lanzar_barrido, "RUNS", tmp_path)
    c = {"config": "sac_v1", "semilla": 0, "pasos": 1000}
    carpeta = tmp_path / "sac_v1_s0_20260101_0000"
    carpeta.mkdir()
    assert not lanzar_barrido.completada(c)
    (carpeta / "modelo_final.zip").write_text("")
    assert lanzar_barrido.completada(c)
    (carpeta / "estado.json").write_text(json.dumps({"pasos_totales": 300}))
    assert not lanzar_barrido.completada(c)
    (carpeta / "estado.json").write_text(json.dumps({"pasos_totales": 1000}))
    assert lanzar_barrido.completada(c)
    assert not lanzar_barrido.completada({**c, "etiqueta": "otra"})


def test_sustituciones_desde_la_linea_de_comandos():
    base = [{"config": "sac_v1", "semilla": 0, "pasos": 1000000, "dispositivo": "cpu", "hilos": 2}]
    nuevo = lanzar_barrido.sustituir(base, "cuda", None, 5000)
    assert nuevo[0]["dispositivo"] == "cuda" and nuevo[0]["pasos"] == 5000 and nuevo[0]["hilos"] == 2
    assert base[0]["dispositivo"] == "cpu"
    assert lanzar_barrido.sustituir(base, None, None, None) == base


PARADA = {"critic_loss": 10.0, "lecturas": 3, "validacion_ratio": 0.3, "validaciones": 4}


def test_parada_por_critico_sostenido():
    assert debe_detener([1.0, 50.0, 60.0, 70.0], [], PARADA) == "critic_loss"
    assert debe_detener([50.0, 1.0, 60.0, 70.0], [], PARADA) is None
    assert debe_detener([50.0, 60.0], [], PARADA) is None


def test_parada_por_validacion_colapsada():
    assert debe_detener([], [0.8, 0.1, 0.1, 0.0, 0.1], PARADA) == "validacion"
    assert debe_detener([], [0.8, 0.1, 0.5, 0.0, 0.1], PARADA) is None
    assert debe_detener([], [0.0, 0.0, 0.0, 0.0], PARADA) is None


def test_parada_sin_umbral_de_critico_solo_mira_la_validacion():
    parada = dict(PARADA, critic_loss=None)
    assert debe_detener([1e6] * 10, [], parada) is None


def test_la_entropia_se_acota():
    class Modelo:
        log_ent_coef = torch.tensor([2.0])

    cb = AcotarEntropia(0.1)
    cb.model = Modelo()
    assert cb._on_step() is True
    assert float(cb.model.log_ent_coef.exp()) == pytest.approx(0.1, rel=1e-5)
    cb.model.log_ent_coef = torch.tensor([-5.0])
    cb._on_step()
    assert float(cb.model.log_ent_coef) == pytest.approx(-5.0)


def test_el_buffer_con_demos_mezcla_mitad_y_mitad():
    obs, act = spaces.Box(-1, 1, (4,), np.float32), spaces.Box(-1, 1, (2,), np.float32)
    n = 40
    demos = {"obs": np.full((n, 4), 7.0), "acciones": np.full((n, 2), 7.0), "obs_sig": np.full((n, 4), 7.0),
             "terminados": np.zeros(n), "recompensas": np.full(n, 7.0)}
    buf = BufferConDemos(100, obs, act, device="cpu", demos=demos)
    for _ in range(50):
        buf.add(np.zeros(4), np.zeros(4), np.zeros(2), np.zeros(1), np.zeros(1), [{}])
    lote = buf.sample(32)
    assert lote.observations.shape == (32, 4)
    assert int((lote.observations[:, 0] == 7.0).sum()) == 16
    sin = BufferConDemos(100, obs, act, device="cpu")
    for _ in range(50):
        sin.add(np.zeros(4), np.zeros(4), np.zeros(2), np.zeros(1), np.zeros(1), [{}])
    assert sin.sample(32).observations.shape == (32, 4)


def test_los_valores_por_defecto_no_cambian_las_configs_anteriores():
    for nombre in ("sac_v3", "sac_v3p"):
        c = cargar_config(nombre)
        assert c["sac"]["algoritmo"] == "SAC"
        assert c["sac"]["ent_max"] is None
        assert c["entrenamiento"]["parada"]["activa"] is False
        assert c["entorno"]["demos"] is None
        assert c["entrenamiento"]["guardar_buffer"] is False


def test_las_configs_v4_cargan_y_difieren_donde_corresponde():
    b, c, d = (cargar_config(n) for n in ("sac_v4b", "sac_v4c", "sac_v4d"))
    assert b["sac"]["algoritmo"] == "TQC"
    assert c["sac"]["algoritmo"] == "SAC" and c["sac"]["ent_max"] == pytest.approx(0.1)
    assert d["entorno"]["demos"] and d["sac"]["ent_max"] == c["sac"]["ent_max"]
    assert c["entorno"]["demos"] is None
    for x in (b, c, d):
        assert x["entrenamiento"]["pasos_totales"] == 4000000


def test_familias_de_prueba_nunca_se_sortean_en_entrenamiento():
    from gym_env import kit
    rng = np.random.default_rng(1)
    pick, place = np.array([0.0, -0.3, 0.05]), np.array([0.3, 0.0, 0.1])
    assert set(kit.familias_entrenamiento()).isdisjoint(kit.FAMILIAS_PRUEBA)
    vistas = set()
    for _ in range(200):
        etiqueta, obst = kit.muestrear_estructurada(rng, pick, place)
        vistas.add(etiqueta.split()[1])
    assert vistas <= set(kit.familias_entrenamiento())
    assert len(vistas) > 5


def test_entorno_mezcla_estructuradas_segun_la_proporcion():
    from gym_env.entorno import EntornoE6
    env = EntornoE6(muestreo="kit")
    try:
        env.fijar_p_estructuradas(1.0)
        env.reset(seed=0)
        assert env.etiqueta.startswith("est ")
        env.fijar_p_estructuradas(0.0)
        env.reset(seed=1)
        assert env.etiqueta.startswith("kit ")
    finally:
        env.close()


def test_curriculo_estructuradas_interpola():
    from training.entrenar_sac import CurriculoEstructuradas
    c = CurriculoEstructuradas({"p_inicial": 0.1, "p_final": 0.5, "fraccion": 0.5}, 1000)
    c.num_timesteps = 0
    assert c.valor() == pytest.approx(0.1)
    c.num_timesteps = 250
    assert c.valor() == pytest.approx(0.3)
    c.num_timesteps = 900
    assert c.valor() == pytest.approx(0.5)


def test_las_configs_v5_cargan():
    a, b, c = cargar_config("sac_v5a"), cargar_config("sac_v5b"), cargar_config("sac_v5c")
    assert a["sac"]["algoritmo"] == "TQC" and a["entrenamiento"]["pasos_totales"] == 12000000
    assert a["estructuradas"]["p_final"] == 0.5 and a["entrenamiento"]["guardar_buffer"] is True
    assert b["sac"]["net_arch"] == [512, 512] and a["sac"]["net_arch"] == [256, 256]
    assert c["estructuradas"]["p_inicial"] == 0.5
    assert Path("shared_scenarios/kit_validacion_v5.yaml").exists()


def test_muestreo_ponderado_y_exclusion_de_familias():
    from gym_env import kit
    rng = np.random.default_rng(3)
    pick, place = np.array([0.0, -0.3, 0.05]), np.array([0.3, 0.0, 0.1])
    cuentas = {}
    for _ in range(600):
        etiqueta, _ = kit.muestrear_estructurada(rng, pick, place, excluir=("J",), pesos={"N": 4.0})
        letra = etiqueta.split()[1]
        cuentas[letra] = cuentas.get(letra, 0) + 1
    assert "J" not in cuentas
    assert cuentas["N"] > 2 * cuentas["A"]


def test_pares_combinados_cambian_pick_y_place_a_la_vez_y_son_resolubles():
    from gym_env.entorno import EntornoE6
    cfg = {"radio_m": 0.04, "paso_m": 0.01, "p_fijos": 0.0}
    env = EntornoE6(muestreo="kit", pares_combinados=cfg)
    try:
        nom = env.par_nominal
        combinados = 0
        for s in range(12):
            env.reset(seed=s)
            dp = np.abs(env.p_pick[:2] - np.array(nom["pick"][:2]))
            dl = np.abs(env.p_meta[:2] - np.array(nom["place"][:2]))
            assert dp.max() <= 0.04 + 1e-9 and dl.max() <= 0.04 + 1e-9
            combinados += dp.max() > 0 and dl.max() > 0
        assert combinados >= 3
    finally:
        env.close()


def test_pares_fijos_si_p_fijos_es_uno():
    from gym_env.entorno import EntornoE6
    env = EntornoE6(muestreo="kit", pares_combinados={"radio_m": 0.04, "paso_m": 0.01, "p_fijos": 1.0})
    try:
        env.reset(seed=0)
        assert np.allclose(env.p_pick, env.par_nominal["pick"]) and np.allclose(env.p_meta, env.par_nominal["place"])
    finally:
        env.close()


def test_las_configs_v6_cargan_y_v5_no_cambia():
    a, b, c = cargar_config("sac_v6a"), cargar_config("sac_v6b"), cargar_config("sac_v6c")
    assert a["entrenamiento"]["pasos_totales"] == 6000000 and a["estructuradas"]["fraccion"] == 1.0
    assert a["entorno"]["pares_combinados"]["radio_m"] == 0.04 and a["entorno"]["estructuradas_familias"] is None
    assert b["entorno"]["estructuradas_familias"]["excluir"] == ["J"]
    assert c["entorno"]["recompensa"]["sigma_pos_m"] == 0.01 and c["entorno"]["recompensa"]["precision"] == 10.0
    v5 = cargar_config("sac_v5a")
    assert v5["entorno"]["pares_combinados"] is None and v5["entrenamiento"]["pasos_totales"] == 12000000


def test_resumen_familias_agrupa_la_prueba_grande():
    from tools.resumen_familias import grupo
    assert grupo("PG-C est C n=3 par=N9") == "PG par no visto"
    assert grupo("PG-C est C n=3 par=N1") == "PG par visto"
    assert grupo("S-C Portal par=N0") == "S prueba"
    assert grupo("SP-D Pasillo par=N2") == "SP entrenadas"
