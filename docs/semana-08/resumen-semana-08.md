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
