# Pares recoger/depositar candidatos y piezas altas del kit

## 1. Pares candidatos (`tools/pares_candidatos.py`, salida `shared_scenarios/pares_kit.yaml`)

Recoger z = 0.05 m y depositar z = 0.10 m, orientación (π, 0, 0), como el par nominal N0. Mapa: `kit-obstaculos/08_pares_candidatos.png`.

Cada par se verifica con la celda base (CNC y bandeja): cinemática inversa libre de colisión en recoger y depositar, holgura a los límites articulares, número de condición del jacobiano (6×6) en ambos puntos, recta articular libre y RRT-Connect propio (no MoveIt/OMPL, 8 s de límite) en ocho combinaciones del kit.

| Par | Recoger (mm) | Depositar (mm) | L (mm) | Holgura a límites | Cond. jacobiano | Combinaciones resueltas (de 8) |
|---|---|---|---|---|---|---|
| N0 (nominal) | (0, −300) | (300, 0) | 424 | 38° | 16.6 | 8 |
| N1 | (−60, −300) | (300, 0) | 469 | 41° | 16.7 | 8 |
| N2 | (60, −300) | (300, 0) | 384 | 41° | 16.7 | 8 |
| N3 | (0, −250) | (300, 0) | 391 | 19° | 20.0 | 8 |
| N4 | (0, −350) | (300, 0) | 461 | 43° | 18.2 | 8 |
| N5 | (0, −300) | (300, −60) | 384 | 38° | 16.8 | 6 (sin IK en Q y R) |
| N6 | (0, −300) | (300, 60) | 469 | 38° | 16.8 | 7 (sin IK en N) |
| N7 | (0, −300) | (250, 0) | 391 | 24° | 17.9 | 8 |
| N8 | (0, −300) | (350, 0) | | | | descartado: sin IK libre (el efector choca con el CNC) |
| N9 | (−60, −340) | (340, 60) | 566 | 58° | 18.5 | 8 |
| N10 | (60, −260) | (260, −60) | 283 | 25° | 18.1 | 5 (sin IK en M, Q y R) |

- La distancia L varía de 283 a 566 mm; el entorno hoy la fija en 424 mm para normalizar la recompensa.
- Ningún par queda cerca de una singularidad (condición ≤ 20); N3, N7 y N10 son los de menor holgura a los límites articulares.
- «Sin IK» significa que una pieza de la combinación estorba en recoger o depositar con ese par: la combinación no sirve para ese par, no que el par sea malo.
- Reserva: el RRT-Connect puede usar otra rama de cinemática inversa que la política.
- Qué haría falta en el entorno para entrenar con pares: sortear recoger y depositar en `reset`, recalcular `L` y `q_pick_ref` por episodio, y volver a medir RRT-Connect y LazyPRM\* con cada par.

## 2. Piezas altas en la macro de SolidWorks

Se añadieron cinco piezas a `Macros_para_SW2020/MesaE6_macro_SW2020.bas` y a `generar_mesa_e6.vbs` (mismo código en ambos), con el mismo criterio de montaje (inserto M6 de 8 mm en la cara inferior, agujeros a paso 50 mm):

| Pieza | Medidas (mm) | Agujeros de montaje |
|---|---|---|
| T01 Muro alto | 175×25×350 | 2 (±50) |
| T02 Columna alta | 75×75×350 | 1 abajo y 1 arriba (apilable, pilar de portal) |
| T03 Poste alto | D30×450 | 1 |
| T04 Tabique largo | 275×25×300 | 3 (−100, 0, 100) |
| T05 Cilindro alto | D60×300 | 1 |

La macro pasa de 24 a 29 piezas. **No se pudo probar sin SolidWorks**: ejecutarla y revisar `registro_generacion.txt` (esperado: «Fallos: 0»). Si fallara, el bloque nuevo está al final de `BuildObstacles`, después de R09, y no modifica las 24 piezas anteriores. Las renders de estas piezas (`05_catalogo_piezas_altas.png`, `06_combinacion_*`) usan mallas simples, no los STEP.
