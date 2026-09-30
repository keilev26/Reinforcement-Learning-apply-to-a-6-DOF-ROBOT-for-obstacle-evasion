"""Currículo de escala (3.6): recorta el muestreo de entrenamiento, nunca el de evaluación."""

import re

import numpy as np

from gym_env.entorno import EntornoE6
from gym_env.escena import contrato

C = contrato.cargar()


def escalas(rng, escala_max, n=200):
    out = []
    for _ in range(n):
        etiqueta, obst = contrato.muestrear_entrenamiento(C, rng, escala_max)
        m = re.search(r"k=([\d.]+)", etiqueta)
        if obst:
            out.append(float(m.group(1)))
    return out


def test_el_muestreo_respeta_escala_max():
    ks = escalas(np.random.default_rng(0), 1.0)
    assert ks and max(ks) <= 1.0 + 1e-9 and min(ks) >= 0.6 - 1e-9


def test_sin_curriculo_se_cubre_el_rango_completo():
    assert max(escalas(np.random.default_rng(0), None)) > 1.8


def test_el_entorno_recibe_el_curriculo_como_metodo():
    """SB3 envuelve el entorno en un Monitor: debe ser un método, no un atributo (set_attr falla)."""
    env = EntornoE6()
    env.fijar_escala_max(1.0)
    assert env.escala_max == 1.0
    ks = []
    for i in range(60):
        env.reset(seed=i)
        m = re.search(r"k=([\d.]+)", env.etiqueta)
        if m:
            ks.append(float(m.group(1)))
    env.close()
    assert ks and max(ks) <= 1.0 + 1e-9


def test_la_evaluacion_no_usa_el_curriculo():
    """Las escenas de evaluación son fijas: el currículo no las toca."""
    escenas = contrato.escenas_evaluacion()
    assert len(escenas) == 100
    assert max(o["dims"][0] for _, obst in escenas for o in obst) > 0.1
