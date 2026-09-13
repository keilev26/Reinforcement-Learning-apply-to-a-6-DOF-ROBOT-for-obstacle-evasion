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

**Adoptada: PyBullet entrena / ROS 2 evalúa.** La política se entrena en PyBullet —rápido,
ligero, sobre CPU— y la línea base clásica se mide en ROS 2 + Gazebo + MoveIt 2 + OMPL.
Replica el stack del Paper 1 (Mao et al., 2025), la referencia metodológica directa.

**Condición que sostiene la comparación:** como se entrena en un motor de física y se mide en
otro, el **paquete 3.13 (verificación de equivalencia PyBullet ↔ Gazebo) es obligatorio**, no
opcional. Mismo URDF, mismos límites articulares, misma geometría de colisión, desde una
fuente única.

| Documento | Contenido |
|---|---|
| `EDT.md` | **EDT adoptada** — paquetes de trabajo, cronograma y compuertas |
| `contexto-proyecto-rl-manipulador-6gdl.md` | Documento de contexto consolidado: estado del arte y decisiones |
| `preguntas-profesor.md` | Puntos bloqueantes a confirmar con el curso |
| `docs/nota-tecnica-semana1.md` | Verificación del entorno y hallazgos técnicos |

---

## Estructura del repositorio

| Carpeta | Contenido | Responsable |
|---|---|---|
| `cad/` | Celda base y biblioteca de componentes (E1), planos, exportables | A |
| `ros2_ws/` | Workspace ROS 2: `ur_simulation_gz`, MoveIt 2, configuración de OMPL | B |
| `gym_env/` | Entorno Gymnasium sobre **PyBullet** con el manipulador de 6 GDL | A |
| `geometry/` | Módulo de distancia mínima eslabón-obstáculo + pruebas contra FCL | B |
| `shared_scenarios/` | **Generador de escenarios: compone los 8 a partir de la biblioteca de `cad/`** | B |
| `training/` | Configuraciones de SB3, scripts de entrenamiento SAC | A |
| `evaluation/` | Cálculo de las 5 métricas, protocolo estadístico, gráficos | A + B |
| `results/` | Datos crudos (`raw/`) y figuras exportadas (`figures/`) | A + B |
| `docs/` | Informe, memoria de diseño electrónico (E2), actas de reunión, bibliografía | A + B |

> `shared_scenarios/` y `geometry/` alimentan por igual a la política y a la línea base.
> Si cada integrante define obstáculos o distancias a su manera, la comparación pierde validez
> y el aporte central del proyecto se cae. Todo cambio ahí requiere revisión del compañero.

---

## Entregables del curso

| ID | Entregable | Contenido |
|---|---|---|
| **E1** | Diseño mecánico | Celda base y **biblioteca modular de componentes CAD**, tabla DH, cinemática, alcanzabilidad, singularidades |
| **E2** | Electrónico | Actuadores y reductores, potencia, unidad de cómputo, sensado, comunicación, seguridad, latencia |
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
| **1 — Equivalencia entre motores** | 4 | El mismo escenario cargado en PyBullet y en Gazebo debe coincidir en geometría, posición, escala y límites articulares. Si no coincide, se detiene el entrenamiento hasta resolverlo: entrenar sobre un modelo que no es el que se mide invalida los resultados |
| **2 — Convergencia** | 6 | Si la política no converge con obstáculos variables, reducir el rango de aleatorización y aplicar currículo progresivo |

Son decisiones con fecha. Si se dejan pasar "a ver si mejora", se pierde el proyecto.

---

## Puesta en marcha

> **Ojo:** el shell por defecto es zsh y `source /opt/ros/jazzy/setup.bash` **falla** ahí.
> Usar `setup.zsh`, o envolver en `bash -c '...'`. Ver `docs/nota-tecnica-semana1.md`.

```bash
# ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2 + paquetes UR ya instalados (Ubuntu 24.04)
source /opt/ros/jazzy/setup.zsh      # en bash: setup.bash

# Workspace
cd ros2_ws && colcon build --symlink-install
source install/setup.zsh

# Entorno de Python para el entrenamiento
python3 -m venv .venv && source .venv/bin/activate
pip install gymnasium stable-baselines3 torch pybullet
```

**Estado actual:** entorno completo y verificado el 2026-09-13. Todo lo anterior ya está
instalado en esta máquina; el `.venv/` no se versiona.
