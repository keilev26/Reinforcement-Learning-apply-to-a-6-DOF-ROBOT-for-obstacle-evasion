# Semana 7 — Todo lo realizado

**Rama:** `feature/magician-e6-evaluacion`

Documento único de la semana: reúne todo lo hecho, con método, resultados y cómo reproducirlo. De
lo que la EDT asignaba a la semana 7 (1.4, 1.6, 1.7, 3.3 y la validación de distancias), casi todo
se adelantó a la semana 6 (`../semana-06/resumen-semana-06.md`). Esta semana cierra 1.3 y 1.4 en
su parte de código y **adelanta de la semana 8** el generador de escenarios (3.12), la
**equivalencia entre motores (3.13, compuerta 1)** y la recompensa formal (3.4).

---

## 0. Resumen

| Paquete | Estado | Resultado clave |
|---|---|---|
| **3.13** Equivalencia PyBullet ↔ MoveIt ↔ Gazebo *(sem. 8-9)* | **Hecho: compuerta 1 superada** | Cinemática igual a 4.6·10⁻⁸ m (MoveIt) y 8.5·10⁻⁷ m (Gazebo); escena idéntica al contrato en los tres motores |
| **3.12** Generador de escenarios *(sem. 8)* | **Hecho** | Una sola expansión del contrato para los tres motores; los 19 mundos de Gazebo, verificados contra el contrato |
| **1.3** Geometría de colisión por componente | **Hecho en código** | La colisión de cada componente es su primitiva envolvente del contrato |
| **1.4** Exportación URDF/SDF con convención de anclaje | **Hecho en código** | 10 componentes exportados, anclados en su centro geométrico. El CAD se enchufa como visual en cuanto esté en `cad/` |
| **3.4** Recompensa formal *(sem. 8)* | **Hecho: recompensa v1** | El potencial de precisión da los **primeros éxitos del proyecto**: 11 de 19 variantes con 1 semilla y 300 000 pasos |
| Pendientes de la semana 6 | Hecho | Orientación de la política de prueba medida; commits subidos |

---

## 1. Pendientes de la semana 6 (cerrados)

- **Orientación de la política de 300 000 pasos (recompensa v0).** En el mejor punto de cada
  episodio llega a 4.5-7.7 mm de la meta, pero con 0.15-0.17 rad de error angular, el triple de
  la tolerancia. **La precisión que falta es de orientación, no de posición.** Registrado en
  `../semana-06/3.2-3.3-entorno-y-mdp.md` y punto de partida de la sección 4.
- La evaluación periódica del entrenamiento registra ahora también el error de orientación.
- Commits `fe493e1`, `04d1d82` y `4a93a2c` subidos a la rama.

---

## 2. Paquete 3.13 — Equivalencia entre motores (compuerta 1)

**Criterio de la EDT:** el mismo escenario cargado en los motores debe coincidir en geometría,
posición, escala y límites articulares. Si no coincide, se detiene el entrenamiento.

**Método.** Con Gazebo y MoveIt levantados sobre la variante 2:
- `equivalencia_ros.py` (ROS) recoge la cinemática directa de MoveIt en 200 configuraciones
  aleatorias, los límites de velocidad, la escena de planificación y, para 6 configuraciones libres
  de colisión, el estado que alcanza Gazebo y **las poses de los eslabones que reporta el propio
  Gazebo** (`gz model`);
- `evaluation/verificar_equivalencia.py` (`.venv`) carga lo mismo en PyBullet y compara.

| Comprobación | Resultado |
|---|---|
| Límites de velocidad: PyBullet vs MoveIt | Diferencia 0 |
| Cinemática directa: PyBullet vs MoveIt (KDL), 200 configuraciones × 7 marcos | Error máx. **4.6·10⁻⁸ m** y 5.8·10⁻⁷ rad |
| Cinemática directa: PyBullet vs **Gazebo**, 6 configuraciones × 6 eslabones | Error máx. **8.5·10⁻⁷ m** y 7.3·10⁻⁶ rad (al nivel de los 6 decimales que imprime Gazebo) |
| Escena: contrato vs PyBullet vs MoveIt (descontando el margen de 2 mm) vs SDF de Gazebo | Diferencia máx. **< 10⁻¹⁷** en dimensiones, posición y orientación de los 4 objetos |
| Geometría de colisión del robot: PyBullet vs FCL | Error máx. 1.14 mm, con signo conocido (paquete 3.11) |

**Veredicto: compuerta 1 superada.** Los tres motores ven el mismo robot y la misma escena; la
única diferencia es la ya caracterizada en distancias (≤ 1.14 mm), cubierta por el margen de 2 mm
de la línea base.

Hallazgos laterales:
- Al convertir el URDF a SDF, Gazebo **suma la masa del efector a Link6** (0.1527 + 0.1 kg), lo
  esperable al unir eslabones fijos. No afecta a la cinemática.
- Límites articulares en Gazebo: `gz model` no los expone; salen del mismo URDF por construcción.

Datos: `results/equivalencia_ros_20260929_1920.json`, `results/equivalencia_escenario_2.yaml`,
`results/equivalencia_mundo_gazebo_escenario_2.sdf`.

---

## 3. Paquetes 3.12, 1.3 y 1.4 — Generador de escenarios y exportación de componentes

**3.12.** El mundo de Gazebo se generaba dentro del launch. Pasó a `shared_scenarios/contrato.py`
(`mundo_sdf`), junto a la expansión que ya usaban PyBullet y MoveIt. **Las tres vistas de cualquier
escenario salen ahora del mismo código:**

| Motor | Adaptador | Origen de la geometría |
|---|---|---|
| PyBullet | `gym_env/escena.py` | `contrato.celda()` + `contrato.variantes()` |
| MoveIt | `p6_contrato.py` (`cargar`) | Ídem, con el margen de 2 mm |
| Gazebo | `gazebo_e6.launch.py` | `contrato.mundo_sdf()` |

**1.3 y 1.4.** `tools/exportar_escenarios.py` exporta cada componente de la biblioteca a
`cad/exportados/{urdf,sdf}/<componente>.*`, **con el origen en su centro geométrico**, la misma
convención de `pose` del contrato. La colisión es la primitiva envolvente (geometría de colisión
simplificada). Si existe `cad/<componente>.stl`, se usa como visual del URDF. **Hoy la carpeta
`cad/` no tiene los CAD**, así que la visual es la misma primitiva: en cuanto se suban, el
exportador los toma sin cambiar código.

**Verificación (29 pruebas nuevas, 73 en total):**
- los 19 mundos SDF contienen exactamente los objetos, poses y dimensiones del contrato;
- los 10 componentes cargan en PyBullet con su caja envolvente centrada en el origen (< 2 mm);
- Gazebo levantado con el launch refactorizado ejecuta la tarea en 5 k=2.0: 2 tramos, 0 de 729
  estados ejecutados en colisión, TCP a 0.25-0.30 mm.

**Incidencia registrada.** Un primer arranque falló porque había quedado vivo un servidor de
Gazebo de la corrida anterior (dos mundos `celda` a la vez). Fue un problema del script auxiliar de
parada, no del launch.

---

## 4. Paquete 3.4 — Recompensa formal (v1)

### 4.1 Punto de partida

Con la recompensa v0 y 300 000 pasos, la política rodea el obstáculo y llega a 4.5-7.7 mm en
posición, pero con 0.15-0.17 rad de orientación: 0 éxitos (sección 1). Había dos hipótesis:
- **H1:** la orientación pesa poco en la v0 (1 por rad, frente a 10 por L en posición);
- **H2:** falta una señal fuerte cuando posición **y** orientación están ya cerca a la vez.

### 4.2 Diseño experimental

Dos corridas en paralelo, **misma semilla (0)**, 300 000 pasos, que difieren **solo** en la
recompensa. `training/configs/sac_v1a.yaml` y `sac_v1b.yaml` heredan de `sac_v0` y declaran solo el
cambio.

| Experimento | Cambio respecto de la v0 | Hipótesis |
|---|---|---|
| **A** | Orientación 1 → **5** por rad: salir 0.05 rad cuesta como ~11 mm de posición | H1 sola |
| **B** | Orientación 5 **+ potencial de precisión** Φ = exp(−d / 0.02 m) · exp(−θ / 0.10 rad), peso 10 | H1 + H2 |

El término de precisión entra como **diferencia de potencial**, Φ(s′) − Φ(s). Un bono por paso cerca
de la meta pagaría por quedarse rondándola en lugar de terminar; el moldeado por potencial da el
gradiente sin cambiar la política óptima (`gym_env/entorno.py`, `potencial_precision`).

**Rendimiento.** Dos corridas simultáneas con los 6 hilos por defecto de PyTorch saturan la CPU y
bajan a ~37 transiciones/s cada una. Con `--hilos 2` suben a ~95/s cada una: 300 000 pasos en
~55 min.

### 4.3 Resultados (evaluación determinista cada 20 000 pasos)

| Pasos | v0: éxitos / errores típicos | **A** | **B** |
|---|---|---|---|
| 100 000 | 0/4 | 0/4 (21-358 mm, 0.08-0.20 rad) | 0/4 (11-74 mm, 0.035-0.23 rad) |
| 160 000 | 0/4 | 0/4 | **2/4** (1 y esfera) |
| 200 000 | 0/4 | 0/4 (colapsa: 3.1 rad) | **1/4** (el 2, con obstáculo: 46 pasos, 3.5 mm) |
| 220 000-300 000 | 0/4 | 0/4 | **3/4 en 3 de 5 evaluaciones** (1, 2 y esfera) y 2/4 en las otras 2 (1 y esfera) |

Registros completos: `results/entrenamiento_sac_v{0,1a,1b}_300k_evaluaciones.csv`.

**Conclusión: se rechaza H1 sola y se acepta H1 + H2.** Reequilibrar la orientación no basta (A:
0 éxitos e inestable). El potencial de precisión es lo que permite cerrar los últimos milímetros
(B). **Se adopta B como recompensa v1**: `RECOMPENSA_V1` en `gym_env/entorno.py` y
`training/configs/sac_v1.yaml`.

### 4.4 La política B en las 19 variantes del contrato

`evaluation/evaluar_politica.py`, política determinista, un episodio por variante (todos son
idénticos; ver la decisión abierta de la semana 6). Datos: `results/politica_sac_v1b_300k_metricas.csv`.

| Escenario | Éxito | Colisiones | Observación |
|---|---|---|---|
| 1, 2, 6 (las 3 formas) | **5/5** | 0 | |
| 4 desplazado | 3/5 | 0 | Falla dy=+0.08 y d=(+0.06, +0.06) |
| 5 redimensionado | 3/4 | 0 | Falla k=2.0, el obstáculo más grande |
| 3 tres obstáculos | 0/1 | 0 | Prensa, carro y pieza en tránsito: nunca vistos al entrenar |
| 7 paso estrecho | 0/3 | 0 | Postes nunca vistos al entrenar. Además, la holgura (13-38 mm) cae dentro del umbral de proximidad de 20 mm |
| **8 fuera de distribución** | 0/1 | **1** | **Primer dato de la pregunta de generalización**: con 300 000 pasos, la política no generaliza al utillaje no visto |
| **Total** | **11/19** | 1 | |

**Comparación preliminar con RRT-Connect** en las 11 variantes resueltas. Es una sola semilla con
30 % del entrenamiento previsto: **no tiene valor estadístico**, solo muestra hacia dónde apunta.

| Métrica | Política (SAC, v1) | RRT-Connect | Lectura |
|---|---|---|---|
| M4 cómputo | **11-22 ms** por episodio | 68-118 ms | 5-7 veces menos |
| M5 holgura | **8.5-39 mm** (mediana 29) | 2.5-10.5 mm (mediana 3.8) | La política deja mucho más margen |
| M3 longitud cartesiana | 0.56-0.93 m | 0.48-0.73 m | La política es 4-70 % más larga (mediana +29 %) |
| M4 ejecución | 1.1-2.4 s | 1.3-2.5 s | **No comparable todavía** (4.5) |

### 4.5 Problema de paridad detectado en M4 (decisión pendiente)

En varias variantes la política **ejecuta más rápido** que la línea base aunque su trayectoria es
más larga. La causa: la línea base respeta el límite de aceleración de 4.72 rad/s² (TOTG), mientras
que la transición cinemática del entorno **solo limita la velocidad**: la política pasa de reposo a
0.05 rad/paso en un solo paso. La condición de paridad de `metricas.yaml` exige los mismos límites
para ambos métodos, así que **el tiempo de ejecución de la política no es comparable tal como
está**.

| Opción | Efecto |
|---|---|
| **A. Limitar la aceleración en el entorno:** \|Δq_t − Δq_t−1\| ≤ 4.72 · 0.03² = 0.0042 rad | Paridad estricta y fiel al robot real (`ServoJ` también está limitado). Hay que reentrenar. **Recomendada** |
| B. Mantener el entorno y reportar M4 ejecución con la salvedad | Sin reentrenar, pero la métrica pierde validez |

Es decisión del equipo. Conviene tomarla **antes** de los entrenamientos largos de 3.5.

### 4.6 Qué sigue (3.5-3.7)

- Entrenar con `sac_v1` hasta 1 M de pasos y 3 semillas, después de decidir 4.5.
- Las fallas en 5 k=2.0, 4 dy=+0.08 y 7 apuntan al **currículo** (3.6): más peso a los obstáculos
  grandes y cercanos a la tarea, sin tocar las variantes del escenario 8.

---

## 5. Estado del cronograma

- Semana 7: 1.3, 1.4, 3.4, 3.12 y 3.13 marcados como realizados.
- **La ruta crítica baja de 14 a 13 semanas**: el proyecto gana una semana de holgura antes de la
  sustentación. Ahora pasa por la cadena de RL: 3.5 → 3.6 → 3.7.
- **Decisiones pendientes para el equipo:** paridad de aceleración en M4 (sección 4.5, conviene
  decidirla antes de 3.5) y repetición de episodios en el protocolo estadístico (semana 6).

## 6. Reproducir

```bash
# 3.13 (con Gazebo + MoveIt corriendo: ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py escenario:=2)
python3 ros2_ws/src/rl6gdl_planning/scripts/equivalencia_ros.py --variante 2
.venv/bin/python -m evaluation.verificar_equivalencia results/equivalencia_ros_<fecha>.json \
    /tmp/rl6gdl_e6_escenario_2.sdf

# 1.3, 1.4 y 3.12
.venv/bin/python tools/exportar_escenarios.py [--mundos]
.venv/bin/python -m pytest

# 3.4 (los dos experimentos en paralelo, ~55 min)
.venv/bin/python -m training.entrenar_sac --config sac_v1a --pasos 300000 --semilla 0 --hilos 2 &
.venv/bin/python -m training.entrenar_sac --config sac_v1b --pasos 300000 --semilla 0 --hilos 2 &
.venv/bin/python -m evaluation.evaluar_politica training/runs/sac_v1b_s0_<fecha>/modelo_final.zip
```
