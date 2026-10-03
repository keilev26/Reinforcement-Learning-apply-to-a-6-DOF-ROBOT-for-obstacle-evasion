# Entrenamiento en la PC potente (paquetes 3.5 a 3.7)

Todo lo necesario para pasar de "una corrida a mano" a entrenar varias semillas y configuraciones en
paralelo, sin improvisar. Se preparó sin entrenar nada: la CPU de este portátil está ocupada y ya se
midió que la GPU de aquí no ayuda.

## Qué se preparó

| Pieza | Para qué |
|---|---|
| `training/benchmark_pc.py` | Mide en 5-8 min qué configuración conviene en la máquina: velocidad de simulación y cuándo satura, coste de actualizar la red en CPU y GPU, núcleos y RAM. Recomienda dispositivo y número de corridas en paralelo |
| `training/lanzar_barrido.py` + `training/barridos/*.yaml` | Lanza un conjunto de corridas con N en paralelo, omite las ya completadas, guarda un registro por corrida y resume los resultados |
| `shared_scenarios/validacion.yaml` | 50 escenas de **validación**, con semilla 2000: distintas de las de entrenamiento y de las 100 de evaluación (se comprobó que no hay ninguna repetida) |
| Callback `Validacion` en `training/entrenar_sac.py` | Cada 50 000 pasos evalúa en esas 50 escenas y guarda `mejor.zip` (el mejor punto) |
| `--set clave=valor` y `--etiqueta` | Cambian un hiperparámetro desde la línea de comandos y distinguen las carpetas |
| `requirements-entrenamiento.txt` | Versiones exactas de las dependencias |

## Por qué un conjunto de validación propio

Durante el entrenamiento la política oscila de una evaluación a otra, y elegir el modelo final es una
decisión que no debe tomarse mirando las 100 escenas de evaluación, porque eso las "contaminaría" y el
resultado final saldría optimista.

- **Validación (50 escenas):** se usa para elegir el mejor punto y comparar configuraciones.
- **Evaluación (100 escenas) y variantes del contrato:** se usan **una sola vez por modelo elegido**,
  para el resultado que se reporta.

Criterio del "mejor": mayor éxito en validación; a igualdad, menos colisiones; a igualdad, menor error
final. Con 50 escenas la resolución es del 2 %, así que diferencias de uno o dos puntos son ruido.

## Pasos en la PC nueva

```bash
git clone git@github.com:keilev26/Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion.git
cd Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-entrenamiento.txt
pip install torch==2.14.1
.venv/bin/python -m pytest -q
```

- `pybullet` se compila al instalarlo: necesita `build-essential` y puede tardar unos minutos.
- Con GPU NVIDIA, instalar PyTorch con CUDA: `pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu130`
  (o la variante que corresponda al driver).
- Las pruebas deben dar **90 aprobadas**. Si alguna falla, no entrenar todavía.

```bash
.venv/bin/python -m training.benchmark_pc
```

Dura unos 5-8 minutos y deja `results/benchmark_pc_<equipo>_<fecha>.yaml`. **No tocar el equipo mientras
corre**: mide rendimiento. Cómo leerlo:

- **`simulacion_pasos_por_s`** y su eficiencia: cuántos procesos de simulación a la vez rinden de verdad
  (por debajo del 70 % de eficiencia, otro proceso más no ayuda).
- **`actualizacion`**: milisegundos por actualización de la red, por dispositivo y tamaño. Una corrida de
  SAC hace una actualización por paso, así que su velocidad es aproximadamente
  `1000 / (ms_actualización + ms_simulación / entornos)`.
- **`recomendacion`**: dispositivo para la red base, corridas en paralelo y horas estimadas.

En este portátil, medido con la CPU libre: ~110 pasos/s con una corrida sola y ~70-95 con varias, es
decir 3-4 horas por millón de pasos. La actualización de la red es secuencial, así que **más núcleos no
aceleran una corrida: se usan para correr varias a la vez**. La GPU solo compensa con redes o lotes
grandes.

## Lanzar

```bash
.venv/bin/python -m training.lanzar_barrido training/barridos/nucleo.yaml --simular
nohup .venv/bin/python -m training.lanzar_barrido training/barridos/nucleo.yaml > barrido.log 2>&1 &
.venv/bin/python -m training.lanzar_barrido training/barridos/nucleo.yaml --resumen
```

`--simular` muestra los comandos sin ejecutarlos. `--paralelo N` fija las corridas simultáneas (por
defecto, núcleos ÷ (entornos + hilos), con el valor del benchmark como guía). Si el barrido se
interrumpe, volver a lanzarlo **omite las corridas completas** y repite las demás.

| Barrido | Corridas | Pasos | Para qué |
|---|---|---|---|
| `exploratorio.yaml` | 8, semilla 0: base, tasa de aprendizaje 1e-4 y 1e-3, red 512×2 y 256×3, lote 1024, γ = 0.995, τ = 0.01 | 300 000 | Orientarse antes de gastar horas. Una semilla es indicativa, no concluyente |
| `nucleo.yaml` | `sac_v1` y `sac_v1c` × semillas 0, 1 y 2 | 1 M | **El núcleo del protocolo** (3 semillas) |
| `extension.yaml` | `sac_v1` y `sac_v1c` × semillas 3 y 4 | 1 M | La extensión (5 semillas) |

Orden recomendado: explorar → si un cambio mejora claramente la validación, crear
`training/configs/sac_v2.yaml` con `base: sac_v1c` y solo ese cambio, y usarlo en `nucleo.yaml` → lanzar
el núcleo → evaluar.

## Qué deja cada corrida (`training/runs/<config>_<etiqueta>_s<semilla>_<fecha>/`)

| Archivo | Contenido |
|---|---|
| `mejor.zip`, `mejor.json` | El mejor punto según validación, y su paso y métricas |
| `validacion.csv` | Éxito, colisiones y error en las 50 escenas de validación, cada 50 000 pasos |
| `evaluaciones.csv` | Evaluación en 4 variantes del contrato, cada 20 000 pasos (seguimiento visual) |
| `modelo_<paso>.zip` | Punto de control cada 20 000 pasos, para reanudar con `--desde` |
| `modelo_final.zip`, `estado.json` | El modelo al terminar y los pasos totales |
| `config.yaml`, `tensorboard/` | La configuración exacta usada (con los `--set`) y las curvas |

La validación cuesta ~4 % del tiempo. Para desactivarla: `--set evaluacion.validacion=null`.

## Al terminar

```bash
.venv/bin/python -m evaluation.evaluar_politica training/runs/<corrida>/mejor.zip --conjunto evaluacion
.venv/bin/python -m evaluation.evaluar_politica training/runs/<corrida>/mejor.zip --conjunto contrato
.venv/bin/python -m evaluation.comparar results/linea_base_evaluacion_20260930_0648_metricas.csv --planner RRTConnect \
    <csv semilla 0> <csv semilla 1> <csv semilla 2>
```

Reportar `mejor.zip` **y** `modelo_final.zip` de cada semilla, para que se vea cuánto cambia la elección.
Copiar los resultados a `results/` con nombres que indiquen configuración, semilla y pasos, y
documentarlos en el resumen semanal. Commit y `git pull --rebase origin main` antes de subir.

## Límites y precauciones

- El estimado de RAM por corrida (1.5 GB) es conservador; el benchmark lo usa para limitar el
  paralelismo. Vigilar con `htop` la primera hora.
- Con un solo semillero por configuración, el barrido exploratorio no distingue una mejora real del ruido
  entre semillas (hubo diferencias notables entre semillas con la misma configuración).
- La recompensa no tiene penalización de sacudida (jerk): si se añade, hay que reentrenar todo el núcleo.
- El currículo y la configuración base se eligieron con datos de este portátil; la comparación entre
  ellos con 3 semillas es precisamente el resultado pendiente.
