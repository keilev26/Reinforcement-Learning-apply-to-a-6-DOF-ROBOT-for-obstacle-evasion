# Siguiente entrenamiento: `sac_v2` (castigo por quedarse quieto, 5 M de pasos, ~24 h)

Todo está preparado y probado en corto; **no se ha lanzado el entrenamiento largo**. Se lanza en la PC potente.

## Qué cambia respecto a `sac_v1`

| Cambio | Dónde | Efecto |
|---|---|---|
| Castigo por quedarse quieto | `gym_env/entorno.py` (`castigo_quieto`, `RECOMPENSA_V2`) | Resta `0.05` por paso cuando el movimiento articular es casi nulo y el TCP no está en la meta |
| 5 M de pasos en vez de 1 M | `training/configs/sac_v2.yaml` | Cinco veces más experiencia por semilla |
| Validación con 200 escenas | `shared_scenarios/validacion_200.yaml` | El criterio del "mejor punto" tiene resolución de 0.5 % en vez de 2 % |
| Evaluación de seguimiento y puntos de control cada 100 000 pasos | `sac_v2.yaml` | Con 5 M de pasos serían 250 puntos de control cada 20 000 |

No cambian: red 256×256, lr 3e-4, γ = 0.99, τ = 0.005, lote 256, búfer de 1 M, 4 entornos por corrida, el
muestreo de obstáculos del entrenamiento, el contrato, las 100 escenas de evaluación ni el protocolo.

### El castigo

```
movimiento = ‖Δq‖ / (Δq_max · √6)            en [0, 1]
castigo    = 0.05 · max(0, 1 − movimiento / 0.1)     si el TCP está a más de 10 mm de la meta
```

- Parado del todo: −0.05 por paso. A velocidad ≥ 10 % de la máxima: 0.
- Es 5 veces el castigo de tiempo (−0.01), pero 20 veces menor que el máximo de proximidad (−1.0). Un paso
  parado cuesta menos que acercarse peligrosamente al obstáculo, de modo que no empuja a chocar.
- Se apaga cerca de la meta (≤ 10 mm) para no castigar el ajuste fino final.
- Los valores por defecto (`quieto: 0.0`) dejan `sac_v0`/`sac_v1` exactamente como antes.

**Hipótesis (no demostrada):** los fallos de `sac_v1` son tiempo agotado a 3-7 cm de la meta. Quedarse quieto
costaba solo −0.01 por paso, mientras acercarse al obstáculo costaba hasta −1.0, y así la política puede
preferir esperar. Si la hipótesis es cierta, el largo medio de episodio de los fallos baja y el éxito sube.
Si no, el castigo no ayuda y se descarta con evidencia.

## Qué corridas se lanzan (`training/barridos/v2_24h.yaml`)

| Corrida | Config | Semilla | Para qué |
|---|---|---|---|
| 1-3 | `sac_v2` | 0, 1, 2 | El resultado: castigo + 5 M, con las mismas 3 semillas que `sac_v1` |
| 4 | `sac_v1_5m` | 0 | **Control**: `sac_v1` sin castigo, también a 5 M |

La corrida 4 separa dos efectos que de otro modo se confundirían: *más pasos* y *castigo*. Sin ella, una
mejora de `sac_v2` frente a `sac_v1` (1 M) no se sabría atribuir. Es una sola semilla, así que es indicativa:
la variación entre semillas de `sac_v1` fue grande (0.43 a 0.87).

"4 procesos en paralelo" se interpretó como **4 corridas simultáneas**, cada una con sus 4 entornos de
simulación (`n_entornos: 4`, ya era así). Para otra combinación, editar el barrido.

## Por qué ~21 h y no más

Medido en la PC potente con `sac_v1` (4 corridas en paralelo, `--hilos 2`, `dispositivo auto`): **1 M de
pasos en 3 h 40 min ≈ 75 pasos/s por corrida** (300 en total). Con 2 en paralelo fueron 109 pasos/s cada una.

| Concepto | Horas |
|---|---|
| 5 M de pasos a 75 pasos/s (incluye la validación de 50 escenas de entonces, ~4 %) | ≈ 18.5 |
| Validación ampliada: 150 escenas más × 100 validaciones × ~0.5 s por escena | ≈ +2.5 |
| **Total estimado** | **≈ 21 h** |

Quedan ~3 h de margen sobre las 24 h. En 24 h caben unos 6.5 M de pasos; se dejaron 5 M porque es lo
acordado y el margen cubre que otra tarea use la CPU. La estimación **no está medida con esta
configuración**: revisar el ritmo a la hora de lanzar (ver abajo) y, si va más lento, la corrida igualmente
guarda `mejor.zip` y un punto de control cada 100 000 pasos.

## Cómo lanzar en la PC potente

```bash
git pull
.venv/bin/python -m pytest -q
.venv/bin/python -m training.lanzar_barrido training/barridos/v2_24h.yaml --simular
nohup systemd-inhibit --what=sleep:idle .venv/bin/python -m training.lanzar_barrido training/barridos/v2_24h.yaml > barrido_v2.log 2>&1 &
```

Comprobar a los 30-60 minutos:

```bash
.venv/bin/python -m training.lanzar_barrido training/barridos/v2_24h.yaml --resumen
tail -n 3 training/runs/sac_v2_s0_*/validacion.csv
```

El ritmo se calcula con los pasos de `tensorboard` o con la hora de `validacion.csv` (una fila cada 50 000
pasos): a 75 pasos/s deben salir ≈ 11 min por fila más la validación. Si una fila tarda más de ~20 min,
algo va lento (CPU ocupada, GPU compartida).

Si el barrido se interrumpe, volver a lanzarlo omite las corridas ya completas, pero **una corrida
interrumpida se repite desde cero**: el búfer de experiencia no se guarda. `--desde modelo_<paso>.zip`
reanuda los pesos, no el búfer.

## Qué mirar al terminar

1. `--resumen` del barrido: éxito en las 200 escenas de validación de cada corrida.
2. Evaluar `mejor.zip` **y** `modelo_final.zip` de cada una en las 100 escenas de evaluación y en el contrato
   (una sola vez por modelo), como en `docs/semana-08/entrenamiento-pc-potente.md`.
3. Comparar con `sac_v1` (1 M) y con el control `sac_v1_5m`.
4. Indicadores de la hipótesis: largo medio de episodio de los fallos, `ep_len_mean` en TensorBoard, y la
   distancia final a la meta de los fallos (en `sac_v1` era de 3-7 cm).

## Qué no se hizo (y por qué)

- **Muestreo de obstáculos más grandes (`sac_v2a`)**: cambia el contrato compartido con Leonardo
  (`aleatorizacion_entrenamiento`). Se deja para un `sac_v3` si el castigo no basta, avisándole antes.
- **Más de 3 semillas de `sac_v2`**: las 4 plazas paralelas se repartieron entre 3 semillas y un control.
- **Búfer mayor a 1 M**: con 5 M de pasos el búfer descarta lo más antiguo. Se mantuvo para no mezclar cambios.

## Pendiente para `sac_v3` (apuntado)

- Muestreo del factor de tamaño `k` de los obstáculos de 0.8 a 2.0 con más peso arriba y sin escenario vacío
  (`sac_v2a` del plan). **Modifica `aleatorizacion_entrenamiento` del contrato compartido con Leonardo:
  avisarle antes de tocarlo.** No tocar `evaluacion`, `validacion` ni el contrato base.
- Obstáculos más variados; el escenario 8 sigue siendo fuera de distribución limpio.
- Se decide según el resultado de `sac_v2`: si el castigo por quedarse quieto no basta, se prueba esto.

## Verificación hecha

- Pruebas: 25 aprobadas en `test_entorno.py` y `test_entrenamiento.py` (incluye el castigo y que la validación
  de 200 contiene a la de 50 y no repite ninguna escena de la evaluación).
- El barrido y los comandos se ven con `--simular`.
- Prueba de humo de 6 000 pasos en CPU del portátil con `sac_v2`: terminó sin errores, la validación de 200 escenas corrió dos veces y escribió `validacion.csv` y `mejor.zip` (éxito 0 es lo esperado con 6 000 pasos). No sirve para medir ritmo: el portátil tenía la CPU ocupada.
