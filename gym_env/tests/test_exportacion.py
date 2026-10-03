import xml.etree.ElementTree as ET

import numpy as np
import pybullet as p
import pytest

from gym_env.escena import contrato

C = contrato.cargar()
VARIANTES = [(n, et, obst) for n in C["escenarios"] for et, obst in contrato.variantes(C, n)]


@pytest.mark.parametrize("n,etiqueta,obst", VARIANTES, ids=[v[1] for v in VARIANTES])
def test_mundo_gazebo_igual_al_contrato(n, etiqueta, obst):
    et, sdf = contrato.mundo_sdf(C, n, etiqueta)
    assert et == etiqueta
    mundo = ET.fromstring(sdf).find("world")
    esperados = {o["id"]: o for o in contrato.celda(C) + obst}
    modelos = mundo.findall("model")
    assert {m.get("name") for m in modelos} == set(esperados)
    for m in modelos:
        o = esperados[m.get("name")]
        pose = [float(v) for v in m.find("pose").text.split()]
        np.testing.assert_allclose(pose, o["pose"], atol=1e-5)
        g = m.find("link/collision/geometry")
        if o["forma"] == "caja":
            dims = [float(v) for v in g.find("box/size").text.split()]
        elif o["forma"] == "cilindro":
            dims = [float(g.find("cylinder/length").text), float(g.find("cylinder/radius").text)]
        else:
            dims = [float(g.find("sphere/radius").text)]
        np.testing.assert_allclose(dims, o["dims"], atol=1e-5)


@pytest.mark.parametrize("nombre", list(C["biblioteca"]))
def test_componente_urdf_anclado_en_su_centro(nombre, tmp_path):
    ruta = tmp_path / f"{nombre}.urdf"
    ruta.write_text(contrato.componente_urdf(C, nombre))
    c = p.connect(p.DIRECT)
    b = p.loadURDF(str(ruta), useFixedBase=True, physicsClientId=c)
    lo, hi = p.getAABB(b, -1, physicsClientId=c)
    p.disconnect(c)
    np.testing.assert_allclose(np.add(lo, hi) / 2, 0.0, atol=2e-3)
    ET.fromstring(contrato.componente_sdf(C, nombre))
