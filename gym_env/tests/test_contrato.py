"""Pruebas del contrato de escenarios v2.0 tal como lo compone PyBullet."""

import math

import numpy as np
import pybullet as p
import pytest

from gym_env.escena import Escena, contrato
from gym_env.robot_e6 import cargar_e6

C = contrato.cargar()
Z_MESA = -0.005          # cara superior de la mesa de trabajo
SUSPENDIDOS = {"pieza_transito"}


@pytest.fixture(scope="module")
def escena():
    cliente = p.connect(p.DIRECT)
    yield Escena(cargar_e6(cliente), C)
    p.disconnect(cliente)


def test_version():
    assert C["version"] == "2.0"


def test_primitivos_de_igual_volumen():
    b = C["biblioteca"]
    prisma = math.prod(b["prisma"]["dim"])
    cilindro = math.pi * b["cilindro"]["radio"] ** 2 * b["cilindro"]["altura"]
    esfera = 4 / 3 * math.pi * b["esfera"]["radio"] ** 3
    assert cilindro == pytest.approx(prisma, rel=0.01)
    assert esfera == pytest.approx(prisma, rel=0.01)


def _base(o) -> float:
    """z de la cara inferior del objeto (solo giros en yaw, como en el contrato)."""
    z = o["pose"][2]
    if o["forma"] == "caja":
        return z - o["dims"][2] / 2
    if o["forma"] == "cilindro":
        return z - o["dims"][0] / 2
    return z - o["dims"][0]


@pytest.mark.parametrize("n", range(1, 9))
def test_obstaculos_apoyados_en_la_mesa(n):
    """Los obstáculos son fabricables: se apoyan en la mesa, salvo la pieza en tránsito."""
    for etiqueta, obstaculos in contrato.variantes(C, n):
        for o in obstaculos:
            if o["id"].split("_", 1)[1] in SUSPENDIDOS:
                continue
            assert o["pose"][3] == 0 and o["pose"][4] == 0, f"{etiqueta}: {o['id']} inclinado"
            assert _base(o) == pytest.approx(Z_MESA, abs=1e-3), f"{etiqueta}: {o['id']}"


def test_tool0_sobre_el_tcp_con_herramienta_hacia_abajo():
    tcp = [0.1, -0.2, 0.05]
    np.testing.assert_allclose(contrato.tool0_desde_tcp(C, tcp, [math.pi, 0, 0]),
                               [0.1, -0.2, 0.05 + C["efector"]["largo_m"]], atol=1e-9)


def test_reposo_sin_colision(escena):
    escena.poner_obstaculos([])
    assert escena.en_colision(np.zeros(6)) == []


@pytest.mark.parametrize("n", range(1, 9))
def test_tarea_factible_en_todas_las_variantes(escena, n):
    T = C["tarea_nominal"]
    for etiqueta, obstaculos in contrato.variantes(C, n):
        escena.poner_obstaculos(obstaculos)
        for k in ("p_pick", "p_place"):
            q = escena.ik_tcp(T[k]["pos"], T[k]["rpy"], T["q_inicial_rad"])
            assert q is not None, f"{etiqueta}: {k} sin cinemática inversa libre de colisión"
