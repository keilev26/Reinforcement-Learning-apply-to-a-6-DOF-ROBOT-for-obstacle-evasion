# Planificación de movimiento y evasión de obstáculos con RL profundo — manipulador de 6 GDL

Proyecto Mecatrónico · Escuela Profesional de Ingeniería Mecatrónica · FIM–UNI

**Equipo:** 2 personas · **Duración:** 10 semanas
**Manipulador:** UR5e — **6 grados de libertad, no redundante**

Sistema de planificación de movimiento reactivo basado en una política de control continuo
aprendida con Soft Actor-Critic, para evasión de obstáculos en celdas de manufactura,
contrastado estadísticamente contra RRT-Connect y RRT\* bajo condiciones equivalentes.

---

## Pregunta de investigación

¿Bajo qué régimen de variabilidad geométrica del entorno una política de movimiento aprendida
por refuerzo conserva desempeño suficiente para operar sin reprogramación, y a partir de qué
punto la replanificación clásica sigue siendo necesaria?

## Las 5 métricas

Tasa de éxito · número de colisiones · longitud de trayectoria · tiempo de ejecución ·
distancia mínima a los obstáculos.

---

## Ruta de arquitectura

**Adoptada: Ruta 2 — todo unificado en ROS 2 + Gazebo.** La política y los planificadores de
OMPL comparten simulador, URDF y verificador de colisiones, lo que da paridad experimental
estricta.

| Documento | Contenido |
|---|---|
| `EDT-Ruta2-ROS2-Unificado.md` | **EDT adoptada** — paquetes de trabajo, cronograma y compuertas |
| `EDT-Ruta1-PyBullet.md` | Plan B: PyBullet entrena / ROS 2 evalúa |
| `EDT-Ruta3-IsaacSim.md` | Evaluada y descartada para 10 semanas |
| `contexto-proyecto-rl-manipulador-6gdl.md` | Documento de contexto consolidado: estado del arte y decisiones |
| `preguntas-profesor.md` | Puntos bloqueantes a confirmar con el curso |

---

## Estructura del repositorio

| Carpeta | Contenido | Responsable |
|---|---|---|
| `cad/` | Diseño de la celda de machine tending (E1), planos, exportables | A |
| `ros2_ws/` | Workspace ROS 2: `ur_simulation_gz`, MoveIt 2, configuración de OMPL | B |
| `gym_env/` | Entorno Gymnasium sobre Gazebo (capas tarea / robot / simulación) | A + B |
| `geometry/` | Módulo de distancia mínima eslabón-obstáculo + pruebas contra FCL | B |
| `shared_scenarios/` | **Generador paramétrico de escenarios — FUENTE ÚNICA** | B |
| `training/` | Configuraciones de SB3, scripts de entrenamiento SAC | A |
| `evaluation/` | Cálculo de las 5 métricas, protocolo estadístico, gráficos | A + B |
| `results/` | Datos crudos (`raw/`) y figuras exportadas (`figures/`) | A + B |
| `docs/` | Informe, arquitectura de sensado (E2), actas de reunión, bibliografía | A + B |

> `shared_scenarios/` y `geometry/` alimentan por igual a la política y a la línea base.
> Si cada integrante define obstáculos o distancias a su manera, la comparación pierde validez
> y el aporte central del proyecto se cae. Todo cambio ahí requiere revisión del compañero.

---

## Entregables del curso

| ID | Entregable | Contenido |
|---|---|---|
| **E1** | Diseño mecánico | Celda CAD, tabla DH, cinemática, alcanzabilidad, singularidades |
| **E2** | Electrónico (reformulado) | Arquitectura de sensado y comunicaciones, latencia, seguridad |
| **E3** | Software y control | Entorno Gym, SAC, distancia mínima, OMPL, escenarios |
| **E4** | Implementación | Demo en vivo, resultados, análisis estadístico, informe |

---

## Flujo de trabajo

- `main` protegida. Una rama por tarea, nombrada con el ID de la EDT: `feature/B6-distancia-minima`.
- **Pull request con revisión cruzada obligatoria.** Sin autoaprobación.
- Mensajes de commit referenciando el ítem de EDT: `[B.4] configurar RRT-Connect en OMPL`.
- Reunión semanal corta con acta en `docs/actas/` — decisiones, bloqueos y estado de compuertas.

**Regla dura:** nada reproducible vive solo en Google Drive. Si está en Drive y no en el
repositorio, no cuenta como resultado del proyecto.

---

## Compuertas de decisión

| Compuerta | Semana | Criterio |
|---|---|---|
| **1 — Velocidad de entrenamiento** | 4 | Medir pasos/segundo en Gazebo headless. Si no alcanza para 3 semillas en las semanas 5-7, el backend de entrenamiento pasa a PyBullet esa misma semana |
| **2 — Convergencia** | 6 | Si la política no converge con obstáculos variables, reducir el rango de aleatorización y aplicar currículo progresivo |

Son decisiones con fecha. Si se dejan pasar "a ver si mejora", se pierde el proyecto.

---

## Puesta en marcha

```bash
# ROS 2 Jazzy + Gazebo Harmonic ya instalados (Ubuntu 24.04)
source /opt/ros/jazzy/setup.bash

# Workspace
cd ros2_ws && colcon build --symlink-install
source install/setup.bash

# Entorno de Python para el entrenamiento
python3 -m venv .venv && source .venv/bin/activate
pip install gymnasium stable-baselines3 torch
```
