# Evaluación del DOBOT Magician E6 como robot del proyecto

**Fecha:** 2026-09-22 · **Rama:** `feature/magician-e6-evaluacion`
**Motivo:** el profesor propone entrenar la política en simulación y probarla en vivo en su Magician E6.
**Estado:** evaluación técnica. **La decisión de adoptar el robot es del equipo.**

---

## 0. Resumen

| Pregunta | Respuesta | Cómo se verificó |
|---|---|---|
| ¿Hay modelo 3D / URDF? | **Sí, oficial de Dobot**: URDF con 7 mallas STL y configuración de MoveIt | Clonado y cargado |
| ¿Hay entrenamientos de RL previos con el E6? | **No se encontró ninguno** publicado | Búsqueda web |
| ¿Se puede entrenar en nuestro entorno (PyBullet)? | **Sí**. Carga en 0.7 s y simula a ~8 000 pasos/s con consulta de distancia | Probado en el `.venv` |
| ¿Se puede simular en ROS 2? | **MoveIt sí** (10/10 planificaciones en Jazzy tras parchear 1 archivo). **Gazebo todavía no**: el paquete oficial usa Gazebo Classic | Probado en esta máquina |
| ¿Se puede mandar la política al robot real? | **Sí**: `ServoJ` recibe posiciones articulares en streaming (33 Hz recomendado) y hay un driver ROS 2 Jazzy comunitario que ya lo usa | Documentación oficial y código |
| ¿Cambia el plan? | **Sí, sobre todo la escala**: el E6 alcanza 0.45 m, el UR5e 0.85 m. La celda y los 8 escenarios se deben rediseñar | Sección 5 |

---

## 1. El robot

Fuente: ficha oficial de Dobot. Entre paréntesis, lo que dice el URDF oficial.

| Parámetro | Magician E6 | UR5e (plan actual) |
|---|---|---|
| GDL | 6 | 6 |
| Alcance | **450 mm** | 850 mm |
| Carga útil | **750 g** (RoboDK dice 0.5 kg) | 5 kg |
| Masa | 7.2 kg | 20.6 kg |
| Repetibilidad | ±0.1 mm | ±0.03 mm |
| Velocidad articular máx. | **120 °/s = 2.09 rad/s**, todas (URDF: 300, marcador; MoveIt: 2.36) | 180 °/s |
| Velocidad TCP máx. | 0.5 m/s | 1 m/s |
| Detección de colisiones | Sí, integrada | Sí |
| Comunicación | Ethernet TCP/IP y Modbus TCP | RTDE |

Rangos articulares (coinciden ficha y URDF):

| J1 | J2 | J3 | J4 | J5 | J6 |
|---|---|---|---|---|---|
| ±360° (±6.27 rad) | ±135° (±2.356) | ±154° (±2.688) | ±160° (±2.793) | ±173° (±3.019) | ±360° (±6.27) |

Es un **cobot de escritorio para educación e investigación**, no un robot industrial. Eso define la
sección 5.

---

## 2. Modelos 3D y trabajos previos

### 2.1 Repositorios

| Repositorio | Qué aporta | ROS | Útil para |
|---|---|---|---|
| [Dobot-Arm/DOBOT_6Axis_ROS2_V4](https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4) (**oficial**) | URDF `me6_robot.xacro`, mallas STL, `me6_moveit`, driver `dobot_bringup_v4`, Gazebo | Humble | **Fuente única del modelo** |
| [Dobot-Arm/TCP-IP-Python-V4](https://github.com/Dobot-Arm/TCP-IP-Python-V4) (**oficial**) | SDK Python para E6 y manual completo de comandos (en chino, en `assets/`) | — | Despliegue en el robot real |
| [WChamorro/simple_dobot_me6_ROS2_driver](https://github.com/WChamorro/simple_dobot_me6_ROS2_driver) | Driver ROS 2 con **comando de velocidad articular vía ServoJ**, `/joint_states`, par y corriente | **Jazzy** | Referencia directa para ejecutar la política |
| [IntoTheVoid-61/DOBOT-Magician-E6-ROS2](https://github.com/IntoTheVoid-61/DOBOT-Magician-E6-ROS2) | E6 con MoveIt Task Constructor para evitar obstáculos (deshierbe) | Jazzy | Ejemplo de MoveIt + E6 en Jazzy |
| [RoboDK – Magician E6](https://robodk.com/robot/Dobot/Magician-E6) | Modelo descargable para RoboDK | — | Solo visualización |

> Ojo: varios resultados de búsqueda de "Dobot Magician URDF" son del **Magician original** (brazo
> de 4 ejes de escritorio), que es otro robot. No confundir.

### 2.2 Aprendizaje por refuerzo con el E6

**No se encontró ningún trabajo publicado** de RL, sim-to-real o evasión de obstáculos aprendida con
el Magician E6. Lo más cercano es IntoTheVoid-61, que evita obstáculos con planificación clásica.

Para el proyecto tiene dos lecturas: no hay de dónde copiar hiperparámetros ni recompensas, pero el
despliegue en el E6 **sería una contribución propia**, y refuerza el vacío del estado del arte.

---

## 3. ¿Se puede entrenar en nuestro entorno? — Sí

Prueba con el URDF oficial convertido a URDF plano (rutas absolutas, sin bloques de Gazebo) en el
`.venv` del proyecto:

| Prueba | Resultado |
|---|---|
| Carga en PyBullet con autocolisión | OK, 0.71 s |
| Límites articulares leídos | Correctos (tabla de la sección 1) |
| Distancia máxima hombro → brida (20 000 muestras de cinemática directa) | 0.512 m |
| Simulación con control de posición + `getClosestPoints` contra un obstáculo | **~8 000 pasos/s** en CPU |

### Problemas del URDF oficial que hay que corregir antes de entrenar

1. **Masas e inercias irreales.** Los 7 eslabones suman **0.94 kg**; el robot pesa 7.2 kg. Si el
   control es cinemático (acción Δq con control de posición) casi no afecta; si se simula dinámica,
   sí.
2. **Límites de velocidad y par de marcador** (`velocity="300"`, `effort="300"`). Hay que poner
   **2.09 rad/s** (ficha oficial), no el 2.36 de `joint_limits.yaml` de MoveIt.
3. **Mallas de colisión pesadas**: 368 000 triángulos en total (143 000 solo la base). Además,
   PyBullet usa la **envolvente convexa** de la malla en cuerpos móviles, mientras que MoveIt usa la
   malla real con FCL: **la misma escena daría distancias mínimas distintas en cada motor**, lo que
   rompe la compuerta 1 (equivalencia). Solución: generar **mallas de colisión simplificadas o
   primitivas (cápsulas) una sola vez** y usar esas mismas en ambos motores.
4. `gravity=false` en las etiquetas de Gazebo de todos los eslabones.

---

## 4. ¿Se puede simular en ROS 2? — MoveIt sí, Gazebo pendiente

### 4.1 MoveIt 2 en Jazzy — verificado

El paquete oficial `me6_moveit` compila en Jazzy, pero `move_group` **se cae al arrancar**:

```
terminate called after throwing an instance of 'rclcpp::ParameterTypeException'
  what():  expected [string_array] got [string]
```

Causa: `ompl_planning.yaml` está en formato de Humble (`planning_plugin` como texto y adaptadores
`default_planner_request_adapters/...`). Jazzy espera `planning_plugins` como lista y separa
`request_adapters` de `response_adapters`. **Reescribiendo solo ese archivo**:

- `move_group` arranca (`You can start planning now!`).
- **10/10 planificaciones** RRT-Connect a metas articulares aleatorias, sin escena.

Depende de tres paquetes del repositorio oficial: `cra_description`, `dobot_rviz` y `me6_moveit`.

### 4.2 Gazebo — no verificado, requiere portar

El paquete `dobot_gazebo` usa **Gazebo Classic** (`gazebo_ros2_control/GazeboSystem`,
`libgazebo_ros2_control.so`), que **no existe en Jazzy**. Hay que portar el bloque `ros2_control`
del URDF a `gz_ros2_control/GazeboSimSystem` (Gazebo Harmonic), igual que hace `ur_simulation_gz`
con el UR5e. Es trabajo acotado, pero **no está hecho ni probado**.

### 4.3 Robot real

| Canal | Dato |
|---|---|
| Puerto 29999 | Comandos (`MovJ`, `ServoJ`, `EnableRobot`...) |
| Puerto 30004 | Estado en tiempo real, **cada 8 ms** (1440 bytes) |
| `ServoJ(J1..J6, t, aheadtime, gain)` | Seguimiento articular en línea; frecuencia recomendada **33 Hz (30 ms)**; `t` ∈ [0.004, 3600] s |

`ServoJ` **sí está soportado en el E6**. (Un resumen automático de búsqueda afirmaba lo contrario;
se comprobó en el manual oficial que la nota "Magician E6 no soporta este comando" corresponde a
`SetToolPower`, no a `ServoJ`.)

El manual advierte que `ServoJ` respeta los límites de velocidad: si el paso pedido es mayor que lo
que se alcanza en `t`, el robot no llega. Con 30 ms y 2.09 rad/s, **el paso máximo por acción es
≈ 0.063 rad por articulación**.

---

## 5. Qué cambia en el plan

### 5.1 Decisión de fondo: un robot o dos

Una política es específica del robot: **no se puede entrenar con el UR5e y ejecutar en el E6**. Hay
tres caminos:

| Opción | Qué implica | Recomendación |
|---|---|---|
| **A. Cambiar todo al E6** | Un solo URDF para PyBullet, MoveIt, Gazebo y el robot real | **Recomendada** |
| B. UR5e para la tesis y E6 aparte | Duplica escenarios, entrenamiento y línea base | No: no cabe en 10 semanas |
| C. Quedarse con el UR5e | Se pierde la demo real | Solo si no hay acceso garantizado al robot |

La opción A además cumple mejor la regla del contrato de **fuente única de geometría**, y el
entregable E4 ("demo en vivo") pasa a ser **en un robot real**.

### 5.2 Cambios concretos si se adopta el E6

| Área | Cambio | Paquetes afectados |
|---|---|---|
| **Contrato de escenarios** | Toda la celda a escala de escritorio. Hoy: pedestal de 0.75 m, `p_pick` a 0.559 m y `p_place` a 0.539 m de la base: **fuera del alcance del E6**. Se rediseña como **v2.0**, lo que resuelve de paso las 9 variantes infactibles pendientes de la v1.2 | 3.1, 1.1, 1.2 |
| **Obstáculos** | Del orden de 5-10 cm, no 20 × 20 × 40 cm. Se mantiene la regla de volumen igual en el escenario 6 | 3.1 |
| **Umbral de éxito M1** | 10 mm sobre una tarea de ~0.66 m era 1.5 %; en el E6 la tarea medirá ~0.3 m. Revisar | 3.1 (`metricas.yaml`) |
| **Carga útil** | 750 g: la pieza del *machine tending* debe ser pequeña y ligera | 1.1, 2.x |
| **Modelo** | URDF corregido (sección 3) y mallas de colisión compartidas por ambos motores | 1.5, 3.13 |
| **Tabla DH (1.5)** | Rehacer para el E6. Se deriva del URDF oficial | 1.5 |
| **MDP** | Periodo de control **30 ms** (33 Hz, lo que acepta `ServoJ`); acción Δq acotada a ±0.063 rad | Entorno Gym |
| **Línea base** | Portar `rl6gdl_planning`: grupo `me6_group` en vez de `ur_manipulator`, formato Jazzy, y recalcular `longest_valid_segment_fraction`: la extensión del espacio del E6 es 20.8 rad (UR5e: 28.8), así que para conservar ~0.014 rad hay que usar **0.00067** en lugar de 0.0005 | 3.9 |
| **Gazebo** | Portar a `gz_ros2_control` (sección 4.2) | 3.8 |
| **Supuesto de percepción ideal** | En el robot real no hay simulador que diga dónde está el obstáculo. Se conserva el supuesto **colocando los obstáculos en poses medidas** (plantilla o marcas en la mesa) y declarándolo | 3.1 §6, E2 |
| **E2 (electrónica)** | El robot y su controlador ya existen. E2 se centra en la integración: red, parada de emergencia, lazo de 33 Hz, latencia real, sensado de la pose del obstáculo | 2.x |
| **Seguridad en la demo** | Obstáculos blandos (espuma) la primera vez, velocidad reducida, detección de colisiones activada, E-stop a mano | 4.x (nuevo) |
| **Cronograma** | Añadir en la fase 4: driver/puente política → `ServoJ`, validación sim-to-real y protocolo de la demo | Gantt |

### 5.3 Lo que no cambia

- La pregunta de investigación, las 5 métricas, SAC y la arquitectura PyBullet entrena / ROS 2 evalúa.
- La compuerta 1 (equivalencia PyBullet ↔ Gazebo) sigue siendo obligatoria, y con el robot real se
  suma una tercera pata: simulación ↔ robot.
- Las lecciones de 3.9 (validación independiente de colisiones, resolución fina, RRT\* no viable) se
  trasladan, pero **hay que volver a medirlas** con el E6.

---

## 6. Preguntas para el profesor

1. ¿Cuánto acceso tendremos al robot: sesiones fijas o solo la demo final?
2. ¿Firmware del controlador? El SDK V4 exige **V4.4.0.0 o superior**.
3. ¿Tiene pinza o ventosa? El driver comunitario soporta la ventosa ES01.
4. ¿La demo en vivo puede usar obstáculos reales en la mesa, o solo virtuales?
5. ¿Acepta que la celda de *machine tending* pase a ser una maqueta de escritorio?

---

## 7. Cómo reproducir las pruebas

```bash
S=<carpeta temporal>
git clone --depth 1 https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4.git $S/dobot
mkdir -p $S/ws/src && cd $S/ws/src
ln -s $S/dobot/cra_description $S/dobot/dobot_rviz $S/dobot/me6_moveit .
# reemplazar me6_moveit/config/ompl_planning.yaml por el formato Jazzy (anexo A)
cd .. && source /opt/ros/jazzy/setup.zsh && colcon build --symlink-install
source install/setup.zsh && ros2 launch me6_moveit move_group.launch.py
```

### Anexo A — `ompl_planning.yaml` en formato Jazzy (el usado en la prueba)

```yaml
planning_plugins:
  - ompl_interface/OMPLPlanner
request_adapters:
  - default_planning_request_adapters/ResolveConstraintFrames
  - default_planning_request_adapters/ValidateWorkspaceBounds
  - default_planning_request_adapters/CheckStartStateBounds
  - default_planning_request_adapters/CheckStartStateCollision
response_adapters:
  - default_planning_response_adapters/AddTimeOptimalParameterization
  - default_planning_response_adapters/ValidateSolution
  - default_planning_response_adapters/DisplayMotionPath
planner_configs:
  RRTConnectkConfigDefault:
    type: geometric::RRTConnect
    range: 0.0
me6_group:
  planner_configs:
    - RRTConnectkConfigDefault
```

> `range: 0.0` es solo para la prueba de humo. Para la línea base se debe fijar como en el paquete 3.9.

---

## Fuentes

- Ficha oficial: https://www.dobot-robots.com/products/education/magician-e6.html
- RoboDK: https://robodk.com/robot/Dobot/Magician-E6
- ROS 2 oficial: https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4
- SDK TCP/IP oficial: https://github.com/Dobot-Arm/TCP-IP-Python-V4
- Driver Jazzy comunitario: https://github.com/WChamorro/simple_dobot_me6_ROS2_driver
- E6 + MoveIt en Jazzy: https://github.com/IntoTheVoid-61/DOBOT-Magician-E6-ROS2
