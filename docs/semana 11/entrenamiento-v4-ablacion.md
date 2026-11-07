# Entrenamiento v4: ablación para evitar la divergencia

Las cuatro corridas de v3 (16 M de pasos) divergieron: la pérdida del crítico llegó a 10^5, la entropía de `sac_v3` s1 subió a 2.9 y la validación cayó a 0 % antes de los 5 M de pasos. Los mejores puntos estaban entre 0.7 y 3.3 M. Detalle en `informe-entrenamiento-v3.md`.

Esta tanda prueba, una cosa a la vez, qué evita la divergencia y si mejora el éxito. Cada corrida usa 4 M de pasos y la validación del kit cada 100 000 pasos, como v3.

## Brazos

| Brazo | Config | Cambio respecto a `sac_v3` | Semillas |
|---|---|---|---|
| A | `sac_v3` | Referencia: los primeros 4 M de `validacion.csv` de las corridas v3 s0 y s1 ya existentes. Se corren además dos semillas con parada activa (s2, s3) para comprobar que el colapso se repite y que la parada funciona. | 2, 3 (nuevas) |
| B | `sac_v4b` | TQC (`sb3-contrib`) en lugar de SAC, con 25 cuantiles y 2 descartados por red. | 0, 1 |
| C | `sac_v4c` | Entropía acotada (α ≤ 0.1), tasa de aprendizaje 1e-4, lote 512, τ = 0.002. | 0, 1 |
| D | `sac_v4d` | C más un búfer fijo de demostraciones de RRT-Connect (728 episodios), mezclado al 50 % en cada lote. | 0, 1 |

La parada automática está activa en todos los brazos. En `sac_v3` (A, semillas 2 y 3) y en `sac_v4c` y `sac_v4d` se para si `critic_loss > 10` durante 5 lecturas seguidas; en TQC (`sac_v4b`) solo rige la regla por validación, porque su pérdida tiene otra escala. Las reglas están en `entrenamiento.parada`:

- `critic_loss`: umbral de la pérdida del crítico (nulo = no se usa).
- `lecturas`: lecturas consecutivas sobre el umbral, una cada 5 000 pasos (con media móvil).
- `validacion_ratio` y `validaciones`: se para si la validación queda por debajo de `ratio × mejor` durante ese número de validaciones seguidas.

Al parar, `estado.json` guarda `detenida_por` y el paso. `mejor.zip` siempre se conserva.

## Criterios de decisión (fijados antes de correr)

- **Estable:** la corrida no se detiene y su validación final es al menos el 50 % de su máximo.
- **Mejora:** el máximo de validación llega a 0.80 y no hay colapsos.
- **Descartar las demostraciones** si el éxito del brazo D no supera al del brazo C.
- La comparación final de los mejores modelos es sobre el kit de evaluación de 196 escenas (`kit_evaluacion.yaml`), que nunca se usa para elegir el mejor punto. Esa evaluación decide la conclusión, no la validación.

## Preparar la PC

```
git pull
.venv/bin/pip install -r requirements-entrenamiento.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml --simular
```

`--simular` debe imprimir ocho comandos. Las demostraciones ya vienen en `training/demos/kit_rrt.npz`. Si hubiera que regenerarlas:

```
PYTHONPATH=. .venv/bin/python -m tools.generar_demos
```

## Lanzar

```
nohup systemd-inhibit --what=sleep:idle .venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml > barrido_v4.log 2>&1 &
```

El barrido usa `paralelo: 4` con 2 hilos por corrida. El orden es C0, B0, D0, C1, B1, D1, A2 y A3, así que la primera tanda es C0, B0, D0 y C1, y la segunda las cuatro restantes. A unas 4.4 h por millón de pasos con cuatro corridas en paralelo, son unas 17.6 h por tanda y unas 35 h en total.

En un portátil de 7.6 GB, dos corridas a la vez llegan a 6.8 GB de memoria y hay riesgo de que el sistema mate el proceso. Allí se usa `--paralelo 1`, con unas 14 h por corrida a 80 pasos/s.

Una corrida detenida no se puede retomar sin perder el búfer de repetición, porque `guardar_buffer` está desactivado. Para poder retomarla, añadir `--set entrenamiento.guardar_buffer=true`.

Para seguirlas:

```
.venv/bin/python -m training.lanzar_barrido training/barridos/v4_ablacion.yaml --resumen
```

## Evaluar al terminar

```
for m in training/runs/sac_v4*_s*_2*/mejor.zip; do
  .venv/bin/python -m evaluation.evaluar_politica $m --archivo shared_scenarios/kit_evaluacion.yaml
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto evaluacion
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto contrato
done
.venv/bin/python -m tools.resumen_kit training/runs/sac_v4*_s*_2*/mejor_metricas_kit_evaluacion.csv
```

## Lo observado en la prueba en el portátil

`sac_v4c` semilla 0 corrió hasta 2.6 M de pasos antes de pararse a mano. La validación subió sin colapsos de 57 % a 82 % y la pérdida del crítico se mantuvo por debajo de 1.4, sin divergencia. En el kit de evaluación, su mejor punto obtuvo 43.9 %: 76 % en las escenas sorteadas (R), pero 14 % y 7 % en las composiciones estructuradas (S y SP). Esas composiciones nunca se usan en el entrenamiento, para poder medir la generalización. Este resultado no se incluye en el paper, porque la corrida es parcial.

## Archivos

- `training/entrenar_sac.py`: TQC, `AcotarEntropia`, `ParadaDivergencia`, `BufferConDemos`, `GuardarBuffer`, opción `--buffer`.
- `training/configs/sac_v0.yaml` (claves nuevas con valores que no cambian lo anterior), `sac_v4b.yaml`, `sac_v4c.yaml`, `sac_v4d.yaml`.
- `training/barridos/v4_ablacion.yaml` y `training/lanzar_barrido.py`.
- `tools/generar_demos.py` y `training/demos/kit_rrt.npz`.
- Pruebas: `gym_env/tests/test_entrenamiento.py`.
