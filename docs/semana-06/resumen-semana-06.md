# Semana 6 — Resumen de lo realizado

**Fechas:** 2026-09-26 a 2026-10-02 · **Rama:** `feature/magician-e6-evaluacion`
**Hito de la EDT:** `env.step()` funcionando → **cumplido**

Resumen de todo lo hecho en la semana. El detalle de cada paquete está en los documentos
enlazados de esta misma carpeta.

---

## 1. Paquetes realizados

| Paquete | Qué se entregó | Resultado clave | Documento |
|---|---|---|---|
| **3.2** Entorno Gym | `gym_env/entorno.py` (`EntornoE6`) | Pasa `check_env` de Gymnasium y SB3; ~1 000 transiciones/s | `3.2-3.3-entorno-y-mdp.md` |
| **3.3** MDP *(adelantado de la sem. 7)* | Acción, transición, observación de 43 valores y fin de episodio, todo desde `metricas.yaml` | Un controlador en línea recta resuelve el espacio libre en 32 pasos; los obstáculos lo detienen | `3.2-3.3-entorno-y-mdp.md` |
| **3.11** Distancia mínima *(adelantado de la sem. 7-8)* | `geometry/distancia.py` + referencia en FCL | 48 216 pares frente a FCL: error medio 0.76 mm, máx. 1.14 mm | `3.11-distancia-minima.md` |
| **3.10** Banco de pruebas | `benchmark_linea_base.py` + `evaluation/` | Mismas métricas en entorno y evaluador; línea base: 189/190 éxitos, 0 colisiones | `3.10-banco-de-pruebas.md` |
| **1.6** Alcanzabilidad | `tools/analisis_cinematico_e6.py` + figura | `p_pick` y `p_place` dentro de la zona fiable | `1.6-1.7-alcanzabilidad-y-singularidades.md` |
| **1.7** Singularidades *(adelantado de la sem. 7)* | Ídem + figura | Muñeca singular en J5 = 0°; el camino de la tarea no baja del 80 % de la manipulabilidad | `1.6-1.7-alcanzabilidad-y-singularidades.md` |
| Preparación de **3.5** | `training/entrenar_sac.py`, `configs/sac_v0.yaml`, `evaluation/evaluar_politica.py` | ~150 transiciones/s entrenando; inferencia de 0.28 ms por paso | `3.2-3.3-entorno-y-mdp.md`, sección 4 |

**No realizados:** 1.3 y 1.4 (geometría de colisión y exportación de los CAD de la celda). Dependen
de los CAD de Leonardo, que no están en el repositorio.

## 2. Hallazgos de la semana

1. **Tres errores de método en la evaluación de la línea base, corregidos antes de generar datos:**
   - LazyPRM\* aparecía con 0 % de éxito porque se castigaba que agote el presupuesto de 5 s, cosa
     que hace por diseño.
   - La meta articular de 0.01 rad dejaba el TCP a más de 5 mm en el 14 % de los planes.
   - PyBullet cuenta como choque roces de < 1 mm que FCL ve como contacto justo. Se resolvió con
     un margen de planificación de 2 mm.
2. **PyBullet y FCL difieren como mucho 1.14 mm** en distancias, con signo conocido: PyBullet es
   conservador con las mallas del robot. Esto explica la diferencia de contactos que quedó
   pendiente en el contrato v2.0.
3. **Con 4 entornos en paralelo, `gradient_steps: 1` da un cuarto de las actualizaciones estándar
   de SAC.** Se corrigió a `-1`.
4. **Señal temprana de entrenamiento** (300 000 pasos, recompensa v0):
   - la política **rodea el obstáculo sin chocar**, con una trayectoria de 0.55 m (RRT-Connect:
     0.58 m);
   - **llega en posición** (hasta 4.5 mm);
   - **falla en orientación**: 0.15-0.17 rad, frente a una tolerancia de 0.05 rad;
   - resultado: 0 éxitos.

   Es el diagnóstico de partida de la recompensa formal (3.4).
5. **Decisión abierta para 4.2:** con política determinista, todos los episodios de una variante
   son idénticos, así que repetir 100 veces no aporta información. Se recomienda que la
   variabilidad salga de las semillas y de variantes muestreadas.

## 3. Estado del cronograma

- Realizados en la semana 6: 1.6, 1.7, 3.2, 3.3, 3.10 y 3.11.
- Ruta crítica: 14 semanas. Ahora pasa por **1.3 → 1.4 → 3.12** (los CAD de la celda).
- Pruebas automáticas: **44**, todas pasan (`.venv/bin/python -m pytest`).

## 4. Commits de la semana

| Commit | Contenido |
|---|---|
| `fe493e1` | Entorno Gym, distancia mínima y banco de la línea base |
| `04d1d82` | Alcanzabilidad, singularidades y cadena de entrenamiento SAC |
| `4a93a2c` | Señal temprana de 300 000 pasos |
