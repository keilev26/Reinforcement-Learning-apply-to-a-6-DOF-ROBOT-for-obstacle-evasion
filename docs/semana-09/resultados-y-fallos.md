# Resultados de los entrenamientos hasta ahora y por qué falla la política

Corridas de 1 M de pasos en la PC potente, 3 semillas por configuración, evaluadas en las 100 escenas fijas
de evaluación (política determinista). Línea base: RRT-Connect, 296/300 (98.7 %).

## 1. Resultados

| Configuración | Semilla 0 | Semilla 1 | Semilla 2 | Media | Colisión | Tiempo agotado |
|---|---|---|---|---|---|---|
| `sac_v1` | 0.68 | 0.43 | 0.87 | **0.66** | 2 % | 32 % |
| `sac_v1c` (currículo de tamaño) | 0.43 | 0.43 | 0.40 | 0.42 | 4.7 % | 53 % |
| RRT-Connect (referencia) | | | | 0.99 | 0 % | 0 % |

- El currículo no ayudó: bajó la media de 0.66 a 0.42. Los barridos exploratorios (lr, γ, τ, red, lote) fueron
  peores o iguales que la base.
- Pareado contra RRT-Connect (Wilcoxon): la línea base gana en éxito (p = 5e-11); la política gasta 19 ms de
  cómputo por episodio frente a 98 ms, y deja 30 mm de holgura mínima frente a 4 mm; el tiempo de ejecución no
  difiere (p = 0.87).
- Entre semillas de la misma configuración hay mucha varianza (0.43 a 0.87), así que una semilla sola no
  prueba una mejora.

## 2. Cómo falla: casi nunca choca, se queda sin tiempo

| Modo de fallo (`sac_v1`, 300 episodios) | Frecuencia |
|---|---|
| Éxito | 66 % |
| Tiempo agotado (300 pasos sin llegar) | 32 % |
| Colisión | 2 % |

La política **no es peligrosa, es indecisa**: en los episodios fallidos el TCP queda a una mediana de
**52 mm** de la meta (la tolerancia es 5 mm y 0.05 rad) y a una mediana de 24 mm del obstáculo.

## 3. De qué depende el fallo

**Tamaño del obstáculo** (éxito de `sac_v1`, escala k):

| k | ≤ 0.8 | 0.8-1.2 | 1.2-1.6 | 1.6-2.0 |
|---|---|---|---|---|
| Éxito | 0.83 | 0.79 | 0.61 | **0.40** |

El obstáculo grande cierra el camino directo y obliga a rodearlo. En `sac_v1c` el efecto es peor (0.71 → 0.14).

**Posición:** el éxito cae de 0.85 (obstáculo a menos de 3 cm del centro del rango) a 0.62 (a 6-10 cm), es decir,
cuando el obstáculo queda más desplazado respecto al camino nominal.

**Forma:** cilindro 0.65, esfera 0.72, prisma 0.60. La diferencia es menor que el efecto del tamaño; en la
combinación forma × tamaño las celdas tienen pocos casos y no conviene sacar conclusiones finas.

**Fuera de distribución:** los escenarios 3 y 8 del contrato dan 0 % y el 7 entre 0 y 67 %. El entrenamiento
nunca los vio; RRT-Connect los resuelve.

## 4. Diagnóstico con rollouts (`sac_v1`, semilla 2, `mejor.zip`)

Se reprodujeron 13 episodios fallidos y 6 exitosos, midiendo el movimiento articular normalizado por paso
(0 = parado, 1 = velocidad máxima).

| | Episodios exitosos | Episodios fallidos |
|---|---|---|
| Duración | 51-87 pasos | 300 pasos (11 de 13) |
| Movimiento medio | 0.38-0.46 | 0.12-0.18 (bajo) |
| Fracción de los últimos 100 pasos casi parado (< 10 % de la velocidad) | 0.01-0.06 | ≥ 0.80 en 6 de 13; 0.37-0.65 en otros 3 |

Lectura:
- **La política llega y se detiene antes de terminar.** En 6 de los 13 fallos pasa el 80-100 % de los últimos
  100 pasos prácticamente quieta. Varios quedan a 5-13 mm de la meta (E007, E055, E081, E061), cerca de las
  tolerancias de 5 mm y 0.05 rad, o a 3-29 mm del obstáculo.
- **Hay dos tipos de fallo.** Choque temprano (2 de 13: terminan en 130-210 pasos a 29-37 cm de la meta) y
  "parálisis" cerca del obstáculo o de la meta (el resto).
- **Es coherente con la recompensa.** Quedarse quieto cuesta −0.01 por paso (término de tiempo). Acercarse al
  obstáculo cuesta hasta −1.0 por paso (proximidad) y chocar −10. La política determinista aprendió que, a pocos
  centímetros del obstáculo, esperar es más barato que arriesgarse. El tiempo se agota y no hay castigo
  proporcional a eso.

Esto apoya la hipótesis que motiva `sac_v2` (castigo de 0.05 por paso por quedarse quieto) **pero no la
demuestra**: es una semilla, una muestra de 13 y observación, no un experimento. Lo pone a prueba `sac_v2`.
También quedan abiertas dos explicaciones: la precisión final (5 mm / 0.05 rad es exigente y varios fallos son
casi-éxitos) y el sesgo del muestreo (los obstáculos grandes están poco representados en el entrenamiento).

## 5. Qué se espera de `sac_v2` y qué no

- Si la parálisis es la causa principal: menos episodios agotados, menor longitud media de los fallos y menor
  distancia final a la meta.
- No debería arreglar por sí solo los escenarios fuera de distribución ni los obstáculos grandes, que dependen
  de lo que se vea en el entrenamiento (`sac_v3`, pendiente de avisar a Leonardo).
- El control `sac_v1_5m` separa el efecto de entrenar 5 veces más del efecto del castigo.

## 6. Alcance y reservas

- Todo es simulación con percepción ideal.
- Los porcentajes por tamaño y posición salen de 300 episodios (3 semillas); cada celda tiene 40-100 casos.
- El diagnóstico de la sección 4 usa una sola semilla (la mejor) y 19 episodios.
- Método: tablas calculadas sobre `results/politica_sac_v1*_s*_1M_pc_evaluacion.csv`; rollouts con
  `training/runs/sac_v1_s2_20261013_2021/mejor.zip`. El script del diagnóstico no se guardó en el repo.
