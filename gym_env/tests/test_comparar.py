import numpy as np

from evaluation.comparar import comparar, por_escena


def filas(n_escenas, metodo, rng, L=0.6, t=100.0, d=0.004, exito=True, repeticiones=1):
    out = []
    for e in range(n_escenas):
        for _ in range(repeticiones):
            out.append({"variante": f"E{e:03d}", "planner": metodo, "exito": str(exito),
                        "L_cart_m": L + rng.normal(0, 0.01), "L_art_rad": 2.5 + rng.normal(0, 0.05),
                        "t_computo_ms": t + rng.normal(0, 1), "t_ejecucion_s": 2.0 + rng.normal(0, 0.05),
                        "d_min_obstaculos_m": d + rng.normal(0, 0.0005)})
    return out


def test_detecta_direccion_y_no_inventa_diferencias():
    rng = np.random.default_rng(0)
    base = por_escena(filas(40, "RRTConnect", rng, repeticiones=3))
    politica = por_escena(filas(40, "SAC", rng, L=0.78, t=10.0, d=0.029))
    r = {x["metrica"]: x for x in comparar(politica, base)}
    assert r["M4 cómputo (ms)"]["veredicto"] == "política mejor"
    assert r["M5 distancia mínima (m)"]["veredicto"] == "política mejor"
    assert r["M3 longitud cartesiana (m)"]["veredicto"] == "línea base mejor"
    assert r["M4 ejecución (s)"]["veredicto"] == "sin diferencia significativa"
    assert r["M1 éxito (fracción)"]["pares_no_nulos"] == 0


def test_escena_sin_exito_queda_fuera_de_las_metricas_continuas():
    rng = np.random.default_rng(1)
    base = por_escena(filas(10, "RRTConnect", rng))
    politica = por_escena(filas(10, "SAC", rng, exito=False))
    r = {x["metrica"]: x for x in comparar(politica, base)}
    assert r["M3 longitud cartesiana (m)"]["pares"] == 0
    assert r["M1 éxito (fracción)"]["pares"] == 10
