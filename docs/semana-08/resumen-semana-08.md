# Semana 8 — Todo lo realizado

**Rama:** `feature/magician-e6-evaluacion`

Continúa `../semana-07/resumen-semana-07.md`. Esta semana cubre lo que la EDT asigna a las semanas
9-11: la tercera semilla del protocolo (3.5, 3.7) y el currículo (3.6).

---

## 1. Infraestructura

- **GPU habilitada** (ver semana 7, sección 5.4): driver compilado para el kernel, PyTorch con CUDA
  (`2.14.1+cu130`), `.venv` movido a `/data` con un enlace simbólico. `entrenar_sac.py` acepta
  `--dispositivo {auto,cpu,cuda}`.
- **La GPU no ayuda en este proyecto; se entrena en CPU.** Una corrida sola: 181 s en CPU frente a
  183 s en GPU por 20 000 pasos. Dos corridas a la vez en GPU: **35 pasos/s cada una**, frente a
  **~95 en CPU**, unas 2.7 veces más lento (1 M de pasos: ~8 h frente a ~3 h). El proceso
  principal queda al 100 % de un núcleo lanzando núcleos CUDA de una red diminuta (256 × 256,
  lotes de 256, cuatro actualizaciones por iteración), y la latencia de cada lanzamiento domina.
  La suposición de la semana 7 de que serviría para varias corridas en paralelo **era incorrecta**.
  La GPU solo compensaría con redes o lotes mucho mayores.

## 2. Currículo de escala (paquete 3.6)

**Motivo.** La política de 1 M de pasos (semana 7) no resuelve los obstáculos grandes: falla en
5 k = 1.5 y 2.0 en las 19 variantes, y resuelve pocas escenas grandes del conjunto de evaluación.

**Diseño.** El obstáculo máximo **crece linealmente de k = 1.0 a k = 2.0 durante la primera mitad**
del entrenamiento, y después queda en el rango completo del contrato. Solo cambia el muestreo de
**entrenamiento**: las evaluaciones periódicas y finales usan siempre las mismas escenas. Se
implementó en `contrato.muestrear_entrenamiento(escala_max=...)`, `EntornoE6.fijar_escala_max` y
un callback `Curriculo` en `training/entrenar_sac.py`. Configuración: `training/configs/sac_v1c.yaml`,
que hereda de `sac_v1` y solo declara el currículo.

**Error encontrado y corregido antes de entrenar.** La primera implementación fijaba el currículo
con `set_attr`, y una prueba mostró que **no llegaba a los entornos**: con `escala_max = 1.0`
salían obstáculos de k = 1.97. Stable-Baselines3 envuelve cada entorno en un `Monitor`, y
`set_attr` fija el atributo en el envoltorio, no en el entorno. Se cambió a un método
(`env_method("fijar_escala_max")`), que sí se reenvía. Sin la prueba, el experimento habría corrido
como el entrenamiento normal sin avisar. Quedó cubierto por `gym_env/tests/test_curriculo.py`
(4 pruebas; 80 en total).

## 3. Corridas lanzadas (1 M de pasos, CPU, `--hilos 2`, 3 en paralelo)

Se lanzaron primero dos en GPU y se relanzaron en CPU al medir el ritmo (sección 1).

| Corrida | Config | Semilla | Objetivo |
|---|---|---|---|
| `sac_v1_s2_20260930_1005` | `sac_v1` | 2 | **Tercera semilla** del núcleo del protocolo (las semillas 0 y 1 ya están) |
| `sac_v1c_s0_20260930_1005` | `sac_v1c` | 0 | Currículo de escala; se compara con `sac_v1` semilla 0 (misma semilla) |
| `sac_v1c_s1_20260930_1005` | `sac_v1c` | 1 | Segunda semilla del currículo, para comparar con `sac_v1` semilla 1 |

*(Resultados: sección 4, al terminar.)*

## 4. Resultados

*(En curso.)*

## 5. Demostración en vivo (preparación)

Para mostrar los avances se construyeron dos herramientas. Guion completo, con escenas recomendadas y
plan B: `guion-demostracion.md`.

- **`tools/visor_politica.py`**: visor de PyBullet que recorre las 19 variantes del contrato, las 100
  escenas de evaluación o escenas de entrenamiento con el teclado, y ejecuta la política a tiempo
  real. Con `--linea-base` dibuja en amarillo el camino que planificó RRT-Connect para la misma
  escena (datos ya medidos) y deja la política en verde. Verificado: sus resultados coinciden con la
  evaluación (2: éxito a 4.7 mm; 8: 38.9 mm sin llegar; esfera: 4.4 mm).
- **`tools/demo_gazebo.sh <escenario> [variante]`**: un solo comando que levanta Gazebo con ventana, el
  E6, los controladores y MoveIt, ejecuta recoger → depositar y mide; permite repetir y al salir cierra
  todo el grupo de procesos. **Rechaza etiquetas mal escritas**, que el launch aceptaba usando en
  silencio la primera variante. Probado de punta a punta: 0 de 842 estados en colisión, sin errores y sin
  procesos sobrantes al salir.
- **Colores en la escena de PyBullet** (celda gris, obstáculo naranja, efector azul): solo cambian lo
  visual; las 80 pruebas siguen pasando.

Límite declarado: la política entrenada **no corre en Gazebo/ROS** (no existe el nodo puente); en vivo
se ve en PyBullet.

## 6. Análisis de pares y limpieza del código

- **Análisis de pares** (`tools/analisis_pares.py`, documento `analisis-pares.md`): por dinámica inversa, los movimientos de la
  política exigen un par casi igual al de RRT-Connect y como máximo el 44 % del límite estimado del URDF. El entrenamiento es
  cinemático y no impone límite de par ni de sacudida; las masas y los límites son estimaciones. Es la versión preliminar del
  paquete 2.1.
- **Código sin comentarios:** se eliminaron los comentarios y docstrings de todo el Python, YAML y shell versionados (55
  archivos). Se comprobó que el árbol sintáctico de cada archivo Python y el contenido de cada YAML son idénticos; la
  documentación vive solo en `docs/`.
- **README:** el flujo de trabajo ya describe el trabajo directo en `main`.
- **Entrenamiento:** el relanzamiento de la tercera semilla y del currículo desde los 780 000 pasos quedó **sin hacer** por falta de
  CPU; los modelos de 780 000 pasos siguen en `training/runs/`.

## 7. Las 5 métricas y el análisis de generalización (4.1 y 4.3)

Documento: `generalizacion-y-metricas.md`; herramienta: `tools/analisis_generalizacion.py`.

- **Tabla de las 5 métricas** para política (2 semillas), RRT-Connect y LazyPRM\*, en las 100 escenas y en las 19
  variantes, con intervalos de Wilson. Política: 44 % y 43 % de éxito (IC 95 % de 35 a 54); línea base: 98.7 % y 99 %.
- **El tamaño del obstáculo es el factor dominante**: la política pasa de 68 % (k de 0.6 a 0.9) a 17 % (k de 1.8 a 2.0);
  RRT-Connect no se ve afectado. La forma importa (prisma 32 %, cilindro 43 %, esfera 55 %); la posición no.
- **Las dos semillas coinciden**: 42 escenas las resuelven ambas, 3 una y 55 ninguna, así que los fallos son sistemáticos.
- **Fuera de la distribución de entrenamiento (escenarios 3, 7 y 8) la política resuelve 0 de 5 variantes**; dentro, 9 de 14.
- **Corrección a una afirmación anterior**: no es cierto que muchas fallas queden a 5-10 mm de la meta. Subir la
  tolerancia a 10 mm añade 0 y 3 puntos; los fallos son sobre todo escenas en las que la política no llega (84 y 91 %).
  Corregido también en `../semana-07/resumen-semana-07.md`.

## 8. Preparación del entrenamiento para la PC potente

Documento: `entrenamiento-pc-potente.md`.

- **Conjunto de validación propio** (`shared_scenarios/validacion.yaml`, 50 escenas, semilla 2000) y callback que guarda el
  **mejor punto** de cada corrida, de modo que el modelo no se elige mirando las 100 escenas de evaluación.
- **`training/lanzar_barrido.py`** y tres barridos: exploratorio (8 corridas de 300 000 pasos), núcleo (6 corridas de 1 M:
  `sac_v1` y `sac_v1c` × 3 semillas) y extensión (semillas 3 y 4). Omite lo ya completado y resume los resultados.
- **`training/benchmark_pc.py`**: mide en 5-8 min dispositivo, paralelismo y velocidad esperados en la máquina nueva.
- `--set` y `--etiqueta` en el entrenamiento; `requirements-entrenamiento.txt` con las versiones exactas.
- Se verificó que `evaluacion.yaml` sigue **idéntico byte a byte** tras refactorizar su generador. 90 pruebas pasan.
- **No se entrenó nada**: la CPU de este equipo está ocupada y la tercera semilla y el currículo siguen en 780 000 pasos.
