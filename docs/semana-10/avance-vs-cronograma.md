# Avance frente al cronograma (corte: 2026-10-31)

Calendario del repo: la semana 6 fue del 26-09 al 02-10, así que la semana 10 cerró el 30-10 y hoy empieza
la semana 11 de 15 (la sustentación es la 15). Con semanas lunes-domingo sería el final de la 10. El Gantt
(`tools/gen_cronograma.py`) tiene ahora la línea roja al cierre de la semana 10.

## Resumen

| Frente | Plan hasta la semana 10-11 | Estado |
|---|---|---|
| E3 algoritmo (Caleb) | 3.5, 3.6, 3.7 (5 semillas) y compuerta 2 | **Adelantado, salvo semillas** |
| E3 línea base (Leonardo) | 3.9, 3.10-3.14 | **Hecho** (3.14 se corrió en la semana 6) |
| E4 integración | 4.1-4.3 programados en la semana 12 | **Adelantados**, se repetirán con los modelos finales |
| E2 electrónica (Leonardo) | 2.1-2.4 (semanas 9-10), 2.5-2.6 (semana 11) | **Atrasado: sin evidencia en el repo** |
| 5.4 actas | semanas 5-14 | **Atrasado: `docs/actas/` vacío** |
| Documentación | P1 informe y diapositivas | Hecho (semana 8-9 del calendario) |

## Detalle

- **3.5 y 3.6, hechos.** Primer SAC el 30-09, currículo de tamaño, aleatorización de forma, posición y escala.
- **Compuerta 2 (convergencia, semana 10): superada.** `sac_v2` llega a 0.917 de éxito (3 semillas) y el
  control `sac_v1_5m` a 0.96 (1 semilla), con ≈ 4.6 M de pasos, 0-1 % de colisiones, frente a 0.987 de
  RRT-Connect. Reserva: fuera de distribución (escenarios 3 y 8) sigue fallando.
- **3.7 incompleto.** Se pide 5 semillas del escenario núcleo. Hay 3 de `sac_v1` (1 M), 3 de `sac_v2` y 1 de
  control. El barrido `control_5m.yaml` (semillas 1-4) está listo y sin lanzar.
- **3.14 hecho.** RRT-Connect y LazyPRM* sobre las 19 variantes y las 100 escenas (30-09). Hay que repetirlo si
  cambia el set de escenas (depende de Leonardo y ROS).
- **4.1-4.3 hechos** con `sac_v1` y `sac_v2`: cinco métricas, Wilcoxon pareado y análisis de generalización.
  Se repiten con el modelo final.
- **3.15 (PPO), semana 12:** sin empezar, a tiempo.

## Atrasos que hay que cerrar

1. **E2 completo (2.1-2.8).** 2.1 y 2.2 vencían en la semana 9 y 2.3 y 2.4 en la 10. No hay documento en el repo.
   Si Leonardo los tiene fuera del repositorio, hay que subirlos. Es el mayor riesgo: son 8 paquetes y quedan
   5 semanas.
2. **Actas (5.4).** Ninguna acta desde la semana 5.
3. **5 semillas de 3.7** (≈ 17-21 h de cómputo).

## Adelantos que dan margen

- Las semanas 11-14 de E3/E4 quedan libres para el set nuevo de escenas, el entrenamiento final de 40 h y el
  repaso de métricas.
- La ruta crítica (Gantt regenerado) es 3.16 → … → 3.7 → 4.1 → 4.2 → 5.5 → 5.6: lo que falta en ella son las
  semillas de 3.7 y el paper IEEE (5.5, semanas 12-14).

## Pendientes fuera del cronograma

- Informe y presentación con las cifras vigentes (0.92-0.96 a ≈ 4.6 M, no 0.66).
- Avisar a Leonardo del cambio de contrato (muestreo y set de evaluación nuevos).

## Actualización (2026-11-02)

- Kit físico de obstáculos (24 STEP + 5 piezas altas en la macro de SolidWorks), 28 combinaciones y 10 pares recoger/depositar verificados: `docs/semana-10/pares-y-piezas-altas.md`.
- Entrenamiento `sac_v3`/`sac_v3p` de ≈ 72 h preparado y probado en corto, sin lanzar: `docs/semana-10/entrenamiento-v3.md`. Sigue pendiente el aviso a Leonardo por los conjuntos nuevos de `shared_scenarios/` y las 5 semillas del control (3.7).
