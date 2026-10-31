# Resultados de `sac_v2` (castigo por quedarse quieto, ~4.6 M de pasos) y del control `sac_v1_5m`

Corridas lanzadas el 2026-10-28 a las 17:53 en la PC potente (4 en paralelo, `barridos/v2_24h.yaml`). **Se
detuvieron antes de los 5 M**: las cuatro llegaron a 4.60-4.65 M de pasos (última escritura el 2026-10-29 entre
las 11:20 y las 11:29, unas 17.5 h) y **no tienen `modelo_final.zip`**. Se evaluó `mejor.zip` de cada una, que
se elige por validación de 200 escenas y no depende de que el entrenamiento termine. Los puntos elegidos están
entre los 3.95 M y los 4.6 M de pasos, y la validación de las últimas 10 evaluaciones es estable salvo la
semilla 1 de `sac_v2` (mínimo 0.685, una caída puntual).

Archivos en `results/`: `politica_<corrida>_4.6M_pc_{evaluacion,contrato}.csv`, `mejor_*_4.6M_pc.json`,
`validacion_*_4.6M_pc.csv`, `comparacion_sac_v2_4.6M_vs_RRTConnect.txt` y
`comparacion_sac_v1_5m_4.6M_vs_RRTConnect.txt`.

## 1. Resultado principal

| Corrida | Validación (200) | Evaluación (100) | Colisión | Contrato (19) | Fallos del contrato |
|---|---|---|---|---|---|
| `sac_v2` semilla 0 | 0.925 | **0.92** | 0 % | 17/19 | 3, 8 |
| `sac_v2` semilla 1 | 0.925 | **0.91** | 1 % | 17/19 | 3, 8 |
| `sac_v2` semilla 2 | 0.930 | **0.92** | 0 % | 18/19 | 8 |
| **`sac_v2` media** | | **0.917** | | | |
| Control `sac_v1_5m` semilla 0 | 0.975 | **0.96** | 0 % | 17/19 | 3, 8 |
| `sac_v1` a 1 M (referencia anterior) | | 0.66 | 2 % | | |
| RRT-Connect | | 0.987 | 0 % | | |

Dos conclusiones:

1. **Entrenar 5 veces más pasos fue lo que cambió el resultado**: de 0.66 a 0.92-0.96. A 1 M de pasos la
   validación de estas corridas era 0.43-0.69, igual que `sac_v1`; el salto ocurre entre 1 M y 3 M de pasos.
2. **El castigo por quedarse quieto no mejoró nada y quedó por debajo del control**: 0.917 (3 semillas) frente
   a 0.96 (1 semilla). Cuatro puntos son cuatro escenas de cien y el control es una sola semilla, así que
   **no es concluyente**, pero la dirección es contraria a la hipótesis. Las tres semillas de `sac_v2` son muy
   parecidas entre sí (0.91-0.92), lo que sugiere que la diferencia no es solo ruido de semilla.

## 2. Cómo fallan ahora

| | `sac_v2` (25 fallos entre 3 semillas) | Control (4 fallos) |
|---|---|---|
| Modo | tiempo agotado (solo 1 de los 25 fue colisión) | tiempo agotado |
| Distancia final a la meta (mediana, semilla 0) | **323 mm** | **17 mm** |
| Error de orientación (mediana) | 0.25 rad | 0.016 rad |

- Con `sac_v1` a 1 M los fallos eran *casi-éxitos* parados cerca de la meta (52 mm). Con el control a 5 M
  siguen siendo casi-éxitos (17 mm). **Con `sac_v2` los fallos ocurren lejos de la meta**: la política no se
  queda parada al final, sino que no logra rodear el obstáculo y sigue moviéndose. Es coherente con un
  castigo que obliga a moverse siempre, pero no se ha probado que esa sea la causa.
- **El obstáculo grande sigue siendo lo difícil.** Éxito por factor de tamaño k (≤0.8 / 0.8-1.2 / 1.2-1.6 /
  1.6-2.0): `sac_v2` 1.00 / 0.97 / 0.97-1.00 / 0.67-0.71; control 1.00 / 1.00 / 0.97 / 0.86. Casi todos los
  fallos son con k > 1.6 (antes con `sac_v1` era 0.40 en ese tramo).
- Dos escenas fallan en las cuatro corridas: `E074 prisma k=1.87` y `E085 esfera k=1.95`, ambas obstáculos
  muy grandes. Siete escenas fallan en las tres semillas de `sac_v2`.
- **Fuera de distribución** (escenarios 3 y 8 del contrato) siguen fallando en casi todas: el 8 en las cuatro
  corridas y el 3 en tres.

## 3. Contra RRT-Connect (100 escenas pareadas, Wilcoxon, α = 0.05)

| Métrica | `sac_v2` (3 semillas) | RRT-Connect | Veredicto |
|---|---|---|---|
| Éxito | ≈ 0.92 | 0.987 | línea base mejor (p = 7.6e-3) |
| Cómputo por episodio | 12.9 ms | 98.9 ms | política mejor (≈ 7.7×), p = 6e-17 |
| Tiempo de ejecución | 1.31 s | 2.05 s | política mejor, p = 8e-16 |
| Longitud cartesiana | 0.538 m | 0.596 m | política mejor, p = 8e-6 |
| Longitud articular | 2.54 rad | 2.52 rad | línea base mejor, p = 0.03 |
| Distancia mínima al obstáculo | 23 mm | 4 mm | política mejor, p = 6e-17 |

El control da lo mismo en las métricas de calidad (cómputo 12.9 ms, ejecución 1.32 s, holgura 23 mm).

**Cambia respecto al resultado anterior (`sac_v1`, 1 M):** el tiempo de ejecución ya no es igual, **la política
es más rápida**, y la brecha de éxito pasó de 0.66 contra 0.99 a 0.92-0.96 contra 0.99. Lo que sigue siendo
cierto: la línea base resuelve más escenas, sobre todo con obstáculos grandes y fuera de distribución.

## 4. Qué decir y qué no

- Se puede afirmar: con 5 M de pasos la política resuelve ≈ 92-96 % de las escenas, con 0-1 % de colisiones,
  7-8 veces menos cómputo que RRT-Connect, trayectorias más rápidas y más holgura.
- **No** se puede afirmar que el castigo por quedarse quieto ayude. Con estos datos no ayuda y quizá perjudica.
  Hace falta más de una semilla del control para decidirlo (`extension.yaml`, semillas 1 y 2 de `sac_v1_5m`).
- **No** se puede afirmar que generalice: los obstáculos grandes y las configuraciones nuevas siguen siendo el
  punto débil.
- Las corridas pararon antes de 5 M y se evaluó el mejor punto por validación; reportar las cifras como
  «≈ 4.6 M de pasos» y no como 5 M.
- La evaluación de 100 escenas se usó **una sola vez** por modelo, sobre `mejor.zip`, como en el protocolo.
- Todo es simulación con percepción ideal.

## 5. Siguiente paso sugerido

1. Correr las semillas 1 y 2 del control `sac_v1_5m` (≈ 14-18 h con 2 corridas en paralelo) para saber si el
   castigo ayuda o perjudica con 3 semillas por lado.
2. Si el castigo no ayuda, `sac_v3` sin castigo y con muestreo de obstáculos grandes (hay que avisar a Leonardo,
   porque cambia el contrato compartido).
3. Actualizar el informe y la presentación con estas cifras: el resultado anterior de 0.66 ya no es el vigente.

## 6. Barrido del control (`training/barridos/control_5m.yaml`)

`sac_v1_5m` (sin castigo) con semillas 1, 2, 3 y 4, 5 M de pasos, 4 en paralelo, la misma configuración que
`v2_24h.yaml`. La semilla 0 ya existe (esta sección 1), así que el control quedaría con 5 semillas frente a las 3
de `sac_v2`. Duración estimada ≈ 17-21 h, como el barrido anterior (el anterior se detuvo a ≈ 17.5 h con
≈ 4.6 M de pasos, de modo que conviene dejarlo hasta el final). Para limitar a 2 semillas (≈ 14 h):
`--paralelo 2` y quitar las semillas 3 y 4 del archivo.

```bash
git pull
.venv/bin/python -m training.lanzar_barrido training/barridos/control_5m.yaml --simular
nohup systemd-inhibit --what=sleep:idle .venv/bin/python -m training.lanzar_barrido training/barridos/control_5m.yaml > barrido_control.log 2>&1 &
```

Al terminar: evaluar `mejor.zip` (o `modelo_final.zip` si existe) de cada una con `evaluation.evaluar_politica`
(`--conjunto evaluacion` y `--conjunto contrato`) y comparar con `sac_v2` y con RRT-Connect.

## 7. Lado por el que se rodea un muro alto (escena `L1` de `tools/escenas_demo/lados.yaml`)

Muro de 56 cm (no se puede pasar por encima) en diagonal sobre el camino pick-place; sus extremos quedan a 6 cm
del camino por el lado de la base (`−`) y a 18 cm por el lado contrario (`+`).

| Quién | Resultado | Lateral mínimo / máximo (m) |
|---|---|---|
| Control `sac_v1_5m` | colisión | −0.24 / 0.00 |
| `sac_v2` semillas 0 / 1 / 2 | tiempo / colisión / tiempo | −0.36, −0.12, −0.19 / ≤ +0.02 |
| RRT-Connect propio (5 semillas del azar) | **resuelve las 5** | −0.09 a −0.34 / ≤ +0.05 |

- Las cuatro políticas se desvían hacia `−` y ninguna prueba `+`.
- **El RRT-Connect también pasa por el lado `−` y llega.** Por tanto el lado de la base no es el problema: el fallo
  de la política está en **cómo ejecuta** ese desvío (choca o no termina), no en haber elegido el lado equivocado.
  La suposición inicial de que habría sido mejor el lado contrario **no se confirma**.
- El RRT-Connect es propio (espacio articular, `tools/verificar_resolubilidad.py`), no MoveIt/OMPL. Sus caminos
  son largos (7-11 rad de recorrido articular para 2.25 rad entre extremos) porque solo se suaviza con atajos
  aleatorios; sirven para saber que hay solución, no como referencia de calidad.
- Sigue siendo cierto que casi nunca se entrena con el obstáculo del lado `−` del camino (el obstáculo se centra en
  (0.212, −0.212) ± 0.08 m, es decir, lateral +0.088 ± 0.113 m, y solo ≈ 2.5 % de las escenas lo ponen del otro lado).
  Como el RRT-Connect no usa el lado `+`, **no hay evidencia de que ese sesgo cause este fallo**: queda como una
  hipótesis separada para `sac_v3` (muestreo simétrico, que cambia `aleatorizacion_entrenamiento` y exige avisar a
  Leonardo).
- **Muros más altos** (`L2` 0.96 m y `L3` 1.60 m, imposibles de superar por arriba): la política vuelve a chocar
  (−0.30 m de lateral, a 400 mm de la meta) y el RRT-Connect propio resuelve las 5 semillas del azar de cada una
  (1.0 a 3.4 s), siempre por el lado `−` (lateral −0.13 a −0.38 m). Las alturas 0.96 y 1.60 m dan el mismo
  camino: más allá del alcance del brazo (0.45 m) la altura ya no cambia nada.
- Muros que se extienden más hacia la base (extremos a −0.12 m o más) dejan inalcanzable el punto de recoger.
