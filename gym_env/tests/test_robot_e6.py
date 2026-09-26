"""Pruebas del modelo del Magician E6 tal como lo ve el entorno de entrenamiento."""

import xml.etree.ElementTree as ET

import numpy as np
import pybullet as p
import pytest

from gym_env.robot_e6 import (PAQUETE, RUTA_URDF, autocolisiones, cargar_e6, fijar_q,
                              pares_excluidos)

# Ficha técnica oficial: rangos articulares en grados y velocidad máxima
RANGOS_FICHA_GRADOS = [360, 135, 154, 160, 173, 360]
VELOCIDAD_FICHA = np.deg2rad(120.0)


@pytest.fixture(scope="module")
def modelo():
    cliente = p.connect(p.DIRECT)
    yield cargar_e6(cliente)
    p.disconnect(cliente)


def test_seis_articulaciones_de_revolucion(modelo):
    assert len(modelo.articulaciones) == 6


def test_limites_de_posicion_coinciden_con_la_ficha(modelo):
    # J1 y J6 van a ±6.27 rad en el URDF oficial: 0.7° por debajo de ±360°
    np.testing.assert_allclose(np.rad2deg(modelo.q_max), RANGOS_FICHA_GRADOS, atol=0.8)
    np.testing.assert_allclose(modelo.q_min, -modelo.q_max)


def test_velocidad_maxima_de_la_ficha(modelo):
    np.testing.assert_allclose(modelo.v_max, VELOCIDAD_FICHA, atol=1e-4)


def test_masa_total_de_la_ficha():
    # Del URDF y no de PyBullet: con base fija, PyBullet reporta masa 0 para la base
    raiz = ET.parse(RUTA_URDF).getroot()
    masa = sum(float(m.get("value")) for m in raiz.iter("mass"))
    assert masa == pytest.approx(7.2, abs=1e-3)


def test_se_excluyen_solo_los_pares_adyacentes():
    cadena = ["base_link", "Link1", "Link2", "Link3", "Link4", "Link5", "Link6"]
    adyacentes = {frozenset(par) for par in zip(cadena, cadena[1:])}
    assert pares_excluidos() == adyacentes


def test_el_motor_respeta_la_exclusion(modelo):
    """Tras simular, ningún contacto del motor puede provenir de un par excluido."""
    excluidos = pares_excluidos()
    nombre = {i: n for n, i in modelo.eslabones.items()}
    rng = np.random.default_rng(1)
    for _ in range(200):
        fijar_q(modelo, rng.uniform(modelo.q_min, modelo.q_max))
        p.performCollisionDetection(physicsClientId=modelo.cliente)
        for c in p.getContactPoints(modelo.cuerpo, modelo.cuerpo, physicsClientId=modelo.cliente):
            assert frozenset((nombre[c[3]], nombre[c[4]])) not in excluidos


def test_reposo_sin_autocolision(modelo):
    fijar_q(modelo, np.zeros(6))
    assert autocolisiones(modelo) == []


def test_detecta_autocolision(modelo):
    """La geometría de colisión debe detectar las posturas plegadas del brazo."""
    rng = np.random.default_rng(2)
    encontradas = 0
    for _ in range(300):
        fijar_q(modelo, rng.uniform(modelo.q_min, modelo.q_max))
        encontradas += bool(autocolisiones(modelo))
    # Medido: 28 % de 2000 posturas aleatorias tienen alguna autocolisión
    assert 0.15 < encontradas / 300 < 0.45


def test_piezas_de_colision_son_convexas():
    """Condición de equivalencia PyBullet <-> FCL: cada pieza debe ser ya su propia envolvente."""
    trimesh = pytest.importorskip("trimesh")
    for f in sorted((PAQUETE / "meshes" / "collision").glob("*.stl")):
        m = trimesh.load(f)
        assert m.is_watertight, f.name
        assert m.volume == pytest.approx(m.convex_hull.volume, rel=1e-6), f.name
