# Planificación de movimiento y evasión de obstáculos con RL profundo — manipulador de 6 GDL

Proyecto Mecatrónico · Escuela Profesional de Ingeniería Mecatrónica · FIM–UNI

**Equipo:** 2 personas · **Duración:** 15 semanas (14 de desarrollo + sustentación)
**Manipulador:** DOBOT Magician E6 — **6 grados de libertad, no redundante** (desde la semana 5;
las semanas 1-4 usaron el UR5e)

**Alcance:** algoritmo de RL y evaluación en simulación. La prueba en el E6 físico del profesor es
trabajo adicional fuera de las 15 semanas (`docs/EDT.md`, sección 10).

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
fuente única: `ros2_ws/src/rl6gdl_e6_description/`, generado con `tools/gen_modelo_e6.py`.

| Documento | Contenido |
|---|---|
| `docs/EDT.md` | **EDT adoptada** — paquetes de trabajo, cronograma y compuertas |
| `docs/contexto-proyecto-rl-manipulador-6gdl.md` | Documento de contexto consolidado: estado del arte y decisiones |
| `docs/semana-03/nota-tecnica-entorno.md` | Verificación del entorno y hallazgos técnicos |
| `docs/semana-04/3.1-contrato-escenarios-y-metricas.md` | Paquete 3.1: contrato de escenarios y las 5 métricas |
| `docs/semana-04/3.9-configuracion-ompl.md` | Paquete 3.9: configuración de OMPL y pendientes P1-P6 |
| `docs/semana-04/3.1-propuesta-contrato-v1.1.md` | Corrección del contrato 3.1, aplicada como v1.1, y su verificación |
| `docs/semana-05/evaluacion-magician-e6.md` | Evaluación del Magician E6: modelo, PyBullet, MoveIt y robot real |
| `docs/semana-05/propuesta-migracion-magician-e6.md` | Migración aprobada al E6: MDP, entorno, contrato v2.0, EDT y cronograma |
| `docs/semana-05/3.1-contrato-v2.0.md` | Contrato de escenarios v2.0 para el E6 y su verificación en PyBullet y MoveIt |
| `docs/semana-05/3.8-gazebo-magician-e6.md` | E6 en Gazebo Harmonic: ejecución de la tarea en los 8 escenarios |
| `docs/semana-05/3.9-ompl-magician-e6.md` | OMPL con el E6: comparación de planificadores y `range` |
| `ros2_ws/src/rl6gdl_e6_description/README.md` | Modelo corregido del E6: qué se corrigió respecto del oficial y con qué números |
| `docs/estado-del-arte/` | Las 13 referencias verificadas: `referencias.bib`, lista IEEE e índice (PDFs solo en local) |

---

## Estructura del repositorio

| Carpeta | Contenido | Responsable |
|---|---|---|
| `cad/` | Celda base y biblioteca de componentes (E1), planos, exportables | A |
| `ros2_ws/` | Workspace ROS 2: modelo del E6 (`rl6gdl_e6_description`), Gazebo (`rl6gdl_e6_gazebo`), MoveIt 2 y OMPL (`rl6gdl_planning`) | B |
| `gym_env/` | Entorno Gymnasium sobre **PyBullet** con el Magician E6. `robot_e6.py` carga el modelo | A |
| `geometry/` | Módulo de distancia mínima eslabón-obstáculo + pruebas contra FCL | B |
| `shared_scenarios/` | **Generador de escenarios: compone los 8 a partir de la biblioteca de `cad/`** | B |
| `training/` | Configuraciones de SB3, scripts de entrenamiento SAC | A |
| `evaluation/` | Cálculo de las 5 métricas, protocolo estadístico, gráficos | A + B |
| `results/` | Datos crudos (`raw/`) y figuras exportadas (`figures/`) | A + B |
| `tools/` | Generadores: modelo del E6 (`gen_modelo_e6.py`) y cronograma (`gen_cronograma.py`) | A + B |
| `docs/` | Documentos vivos (contexto, EDT) en la raíz; entregables fechados en `semana-NN/`; actas en `actas/` | A + B |

> `shared_scenarios/` y `geometry/` alimentan por igual a la política y a la línea base.
> Si cada integrante define obstáculos o distancias a su manera, la comparación pierde validez
> y el aporte central del proyecto se cae. Todo cambio ahí requiere revisión del compañero.

---

## Entregables del curso

| ID | Entregable | Contenido |
|---|---|---|
| **E1** | Diseño mecánico | Celda base y **biblioteca modular de componentes CAD**, tabla DH, cinemática, alcanzabilidad, singularidades |
| **E2** | Electrónico | Integración del E6: análisis dinámico, arquitectura de control, efector, cómputo, sensado, comunicación, seguridad, latencia |
| **E3** | Software y control | Entorno Gym, SAC, distancia mínima, OMPL, escenarios |
| **E4** | Implementación | Demo en vivo en simulación, resultados, análisis estadístico, informe |

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
| **1 — Equivalencia entre motores** | 8 | El mismo escenario cargado en PyBullet y en Gazebo debe coincidir en geometría, posición, escala y límites articulares. Si no coincide, se detiene el entrenamiento hasta resolverlo: entrenar sobre un modelo que no es el que se mide invalida los resultados |
| **2 — Convergencia** | 10 | Si la política no converge con obstáculos variables, reducir el rango de aleatorización y aplicar currículo progresivo |

Son decisiones con fecha. Si se dejan pasar "a ver si mejora", se pierde el proyecto.

---

## Puesta en marcha

> **Ojo:** el shell por defecto es zsh y `source /opt/ros/jazzy/setup.bash` **falla** ahí.
> Usar `setup.zsh`, o envolver en `bash -c '...'`. Ver `docs/semana-03/nota-tecnica-entorno.md`.

```bash
# ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2 + paquetes UR ya instalados (Ubuntu 24.04)
source /opt/ros/jazzy/setup.zsh      # en bash: setup.bash

# Workspace
cd ros2_ws && colcon build --symlink-install
source install/setup.zsh

# Entorno de Python para el entrenamiento
python3 -m venv .venv && source .venv/bin/activate
pip install gymnasium stable-baselines3 torch pybullet pyyaml pytest

# Solo para regenerar el modelo del E6 (tools/gen_modelo_e6.py)
pip install trimesh scipy rtree scikit-image fast-simplification
```

Pruebas del modelo del robot: `.venv/bin/python -m pytest` desde la raíz.

**Estado actual:** entorno completo y verificado el 2026-09-13. Todo lo anterior ya está
instalado en esta máquina; el `.venv/` no se versiona.
