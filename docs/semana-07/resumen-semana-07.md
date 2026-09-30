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
| **3.4** Recompensa formal *(sem. 8)* | **En experimento** | Sección 4 |
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

## 4. Paquete 3.4 — Recompensa formal

*(En curso: se completa al terminar los experimentos.)*

---

## 5. Estado del cronograma

- Semana 7: 1.3, 1.4, 3.12 y 3.13 marcados como realizados.
- **La ruta crítica baja de 14 a 13 semanas**: el proyecto gana una semana de holgura antes de la
  sustentación. Ahora pasa por la cadena de RL, empezando por **3.4** (recompensa) →
  3.5 → 3.6 → 3.7.

## 6. Reproducir

```bash
# 3.13 (con Gazebo + MoveIt corriendo: ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py escenario:=2)
python3 ros2_ws/src/rl6gdl_planning/scripts/equivalencia_ros.py --variante 2
.venv/bin/python -m evaluation.verificar_equivalencia results/equivalencia_ros_<fecha>.json \
    /tmp/rl6gdl_e6_escenario_2.sdf

# 1.3, 1.4 y 3.12
.venv/bin/python tools/exportar_escenarios.py [--mundos]
.venv/bin/python -m pytest
```
