import json
from pathlib import Path

import pytest
import yaml

from gym_env.escena import contrato
from training import lanzar_barrido
from training.entrenar_sac import Validacion, aplicar_cambios, cargar_config, criterio_mejor

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
