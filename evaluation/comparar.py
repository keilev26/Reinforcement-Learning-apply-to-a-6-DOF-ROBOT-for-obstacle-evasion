"""Protocolo estadístico (metricas.yaml 2.1): política frente a línea base, pareado POR ESCENA.

Entradas: el CSV de métricas de la línea base sobre el conjunto de evaluación y uno o más CSV de
la política (uno por semilla). Por cada escena:
  política    = media entre semillas (determinista: un episodio por semilla)
  línea base  = media entre consultas (estocástica: varias consultas por escena)
Éxito: fracción de episodios exitosos. M3, M4 y M5: media sobre los episodios EXITOSOS; una escena
entra en la comparación de esas métricas solo si ambos métodos tienen al menos un éxito en ella.

Prueba: rangos con signo de Wilcoxon, pareada por escena, bilateral, α = 0.05. Se reporta la
dirección (qué método es mejor) junto al valor p. Los pares con diferencia 0 se descartan
(convención de Wilcoxon), y se dice cuántos quedan.

Uso: .venv/bin/python -m evaluation.comparar results/linea_base_evaluacion_<f>_metricas.csv \\
         --planner RRTConnect results/politica_<...>_s0.csv results/politica_<...>_s1.csv
"""
import argparse
import csv
from collections import defaultdict

import numpy as np
from scipy.stats import wilcoxon

METRICAS = [  # (columna, nombre, mejor si es...)
    ("exito", "M1 éxito (fracción)", "mayor"),
    ("L_cart_m", "M3 longitud cartesiana (m)", "menor"),
    ("L_art_rad", "M3 longitud articular (rad)", "menor"),
    ("t_computo_ms", "M4 cómputo (ms)", "menor"),
    ("t_ejecucion_s", "M4 ejecución (s)", "menor"),
    ("d_min_obstaculos_m", "M5 distancia mínima (m)", "mayor"),
]


def por_escena(filas: list[dict]) -> dict[str, dict[str, float]]:
    grupos = defaultdict(list)
    for f in filas:
        grupos[f["variante"]].append(f)
    out = {}
    for esc, fs in grupos.items():
        ok = [f for f in fs if f["exito"] == "True"]
        d = {"exito": len(ok) / len(fs)}
        for col, _, _ in METRICAS[1:]:
            vals = [float(f[col]) for f in ok if f[col] not in ("", "None", "inf", "nan")]
            d[col] = float(np.mean(vals)) if vals else np.nan
        out[esc] = d
    return out


def comparar(politica: dict, base: dict, alfa: float = 0.05) -> list[dict]:
    comunes = sorted(set(politica) & set(base))
    res = []
    for col, nombre, mejor in METRICAS:
        pares = [(politica[e][col], base[e][col]) for e in comunes
                 if np.isfinite(politica[e][col]) and np.isfinite(base[e][col])]
        a, b = (np.array(x) for x in zip(*pares)) if pares else (np.array([]), np.array([]))
        dif = a - b
        n_no_nulos = int(np.sum(dif != 0))
        if n_no_nulos >= 6:
            p = float(wilcoxon(a, b).pvalue)
        else:
            p = np.nan
        med = float(np.median(dif)) if len(dif) else np.nan
        if not np.isfinite(p) or p >= alfa:
            veredicto = "sin diferencia significativa"
        else:
            politica_mejor = (med > 0) == (mejor == "mayor")
            veredicto = "política mejor" if politica_mejor else "línea base mejor"
        res.append({"metrica": nombre, "pares": len(pares), "pares_no_nulos": n_no_nulos,
                    "mediana_politica": float(np.median(a)) if len(a) else np.nan,
                    "mediana_linea_base": float(np.median(b)) if len(b) else np.nan,
                    "mediana_diferencia": med, "p": p, "veredicto": veredicto})
    return res


def leer(ruta):
    with open(ruta) as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("linea_base")
    ap.add_argument("politica", nargs="+", help="un CSV por semilla")
    ap.add_argument("--planner", default="RRTConnect")
    a = ap.parse_args()
    base = por_escena([f for f in leer(a.linea_base) if f["planner"] == a.planner])
    politica = por_escena([f for ruta in a.politica for f in leer(ruta)])
    res = comparar(politica, base)
    print(f"Política ({len(a.politica)} semillas) frente a {a.planner}, {len(set(base) & set(politica))} escenas pareadas\n")
    print(f"{'métrica':<30}{'pares':>6}{'≠0':>5}{'política':>11}{'línea base':>12}{'dif. med.':>11}{'p':>10}   veredicto")
    for r in res:
        print(f"{r['metrica']:<30}{r['pares']:>6}{r['pares_no_nulos']:>5}{r['mediana_politica']:>11.3f}"
              f"{r['mediana_linea_base']:>12.3f}{r['mediana_diferencia']:>11.3f}{r['p']:>10.2e}   {r['veredicto']}")


if __name__ == "__main__":
    main()
