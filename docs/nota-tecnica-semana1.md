# Nota técnica — Semana 1: verificación del entorno

Fecha de verificación: 2026-09-06 · Máquina: Ubuntu 24.04.4 LTS

## 1. Software instalado y verificado

| Componente | Versión / estado |
|---|---|
| ROS 2 | Jazzy |
| Gazebo | Harmonic (`gz`), con `ros_gz`, `ros_gz_bridge`, `ros_gz_sim` |
| MoveIt 2 | 2.12.4 — 28 paquetes, incluye `moveit_planners_ompl` y `moveit_ros_benchmarks` |
| Universal Robots | `ur_description` 3.5.1, `ur_simulation_gz` 2.5.0, `ur_robot_driver` 3.8.0, `ur_moveit_config` |
| OMPL | Instalado |
| Gymnasium | 1.3.0 |
| Stable-Baselines3 | 2.9.0 |
| PyTorch | 2.14.0+cpu — **CUDA no disponible en esta máquina** |

Entorno de Python en `.venv/` (no versionado).

## 2. Trampa del shell — importante

El shell por defecto del equipo es **zsh**, y `source /opt/ros/jazzy/setup.bash` **falla** ahí:
intenta resolver `setup.sh` relativo al directorio de trabajo en vez de a `/opt/ros/jazzy`,
porque depende de `BASH_SOURCE`, que zsh no define.

```
/opt/ros/jazzy/setup.bash:.:11: no such file or directory: .../setup.sh
```

**Soluciones:** usar `source /opt/ros/jazzy/setup.zsh` en zsh, o envolver en bash:
`bash -c 'source /opt/ros/jazzy/setup.bash && <comando>'`.

## 3. Invariante de 6 GDL — VERIFICADO en el modelo real

URDF generado desde `ur_description` con `ur_type:=ur5e`. **6 articulaciones revolutas**, ninguna
adicional. Confirma el invariante del proyecto sobre el modelo que se usará, no sobre la hoja de datos.

| Articulación | Tipo | Vel. máx (rad/s) | Esfuerzo (N·m) |
|---|---|---|---|
| `shoulder_pan_joint` | revolute | π | 150 |
| `shoulder_lift_joint` | revolute | π | 150 |
| `elbow_joint` | revolute | π | 150 |
| `wrist_1_joint` | revolute | π | 28 |
| `wrist_2_joint` | revolute | π | 28 |
| `wrist_3_joint` | revolute | π | 28 |

> Estos límites son entrada directa del entregable **E1** (diseño mecánico) y acotan el
> espacio de acción Δq del MDP.

Reproducir con:

```bash
bash -c 'source /opt/ros/jazzy/setup.bash && \
  xacro $(ros2 pkg prefix ur_description)/share/ur_description/urdf/ur.urdf.xacro \
  ur_type:=ur5e name:=ur5e > /tmp/ur5e.urdf'
```

## 4. Hallazgo para el paquete B.4 — configuración de OMPL

`ur_moveit_config/config/ompl_planning.yaml` **solo declara el plugin y los adaptadores; no define
`planner_configs`.** Es decir, el paquete de UR no deja RRT-Connect ni RRT\* listos para seleccionar.

Las configuraciones sí existen en
`/opt/ros/jazzy/share/moveit_configs_utils/default_configs/ompl_defaults.yaml`:

```yaml
RRTConnect:
  type: geometric::RRTConnect
  range: 0.0              # si es 0.0, OMPL lo fija en setup()

RRTstar:
  type: geometric::RRTstar
  range: 0.0
  goal_bias: 0.05
  delay_collision_checking: 1
```

**Trabajo concreto de B.4:** escribir un `ompl_planning.yaml` propio que declare `planner_configs`
con RRT-Connect y RRT\*, y asociarlos al grupo de planificación `ur_manipulator`, fijando
explícitamente `range` y `goal_bias` en lugar de dejarlos en 0.0.

> Dejar `range: 0.0` hace que OMPL elija el valor en tiempo de ejecución, lo que introduce una
> variable no controlada en la comparación contra la política aprendida. **Para el protocolo
> experimental hay que fijarlo y documentarlo.**

## 5. BUG confirmado — desajuste de nombre entre URDF y SRDF

Al levantar `ur_sim_moveit.launch.py`, `move_group` y RViz emiten:

```
Error: Semantic description is not specified for the same robot as the URDF
```

**Causa raíz localizada.** Los dos paquetes construyen el nombre del robot de forma distinta:

| Archivo | Línea | Nombre asignado |
|---|---|---|
| `ur_simulation_gz/launch/ur_sim_control.launch.py` | 84-85 | `name:=` **`"ur"`** — literal, no depende de `ur_type` |
| `ur_moveit_config/launch/ur_moveit.launch.py` | 120 | `.robot_description_semantic(..., {"name": ur_type})` → **`"ur5e"`** |

Verificado en el sistema corriendo:

```
/robot_state_publisher  robot_description           → robot name="ur"
/move_group             robot_description_semantic  → robot name="ur5e"
```

**Los nombres no pueden coincidir para ningún valor de `ur_type`**: uno está fijo en `"ur"` y el otro
sigue a `ur_type`. Es un defecto de empaquetado de la combinación `ur_simulation_gz` +
`ur_moveit_config` en Jazzy, no un error de configuración local.

**Estado del sistema pese al error:** la simulación levanta y opera. Se verificó
`/joint_states` publicando las 6 articulaciones, controladores `joint_state_broadcaster` y
`scaled_joint_trajectory_controller` **activos**, y el grupo de planificación `ur_manipulator`
presente en el SRDF cargado.

**Acción para el paquete B.1.** El equipo va a construir de todos modos su propia configuración de
MoveIt para incorporar la celda como escena, así que la corrección se absorbe ahí: en el launch
propio, pasar el **mismo** nombre al URDF y al SRDF. No parchear los paquetes del sistema.

> Conviene verificar la planificación de extremo a extremo antes de dar por cerrada la semana 1.
> Si el desajuste llegara a afectar la validación del modelo cinemático, contaminaría todas las
> métricas de la línea base.

## 6. Pendiente de la semana 1

- Confirmar que `moveit_ros_benchmarks` corre y qué métricas entrega (asunto `warehouse_mongo`).
- Aclarar en qué máquina está la GPU: aquí `nvidia-smi` no responde y torch quedó en versión CPU.
