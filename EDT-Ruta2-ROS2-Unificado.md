# EDT — Ruta 2: todo unificado en ROS 2 + Gazebo **(RECOMENDADA)**

**Proyecto:** Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de **6 GDL**
**Curso:** Proyecto Mecatrónico · FIM–UNI
**Equipo:** 2 personas · **Duración:** 10 semanas
**Manipulador:** UR5e — **6 grados de libertad, no redundante** (invariante del proyecto)

---

## 1. Resumen de la ruta

Se construye un **entorno Gymnasium propio sobre ROS 2 + Gazebo/`ros2_control`**, de modo que la política de refuerzo y los planificadores clásicos de OMPL compartan **el mismo simulador, el mismo URDF de 6 GDL y el mismo verificador de colisiones**.

**La razón para elegir esta ruta no es que sea más difícil, sino que la unificación es una ganancia metodológica real:** elimina la objeción de comparar métodos entrenados y medidos en motores de física distintos. Que además implique construir un entorno Gym sobre ROS 2 —trabajo de semanas y no de días— es una consecuencia, no el objetivo.

**Ventaja adicional frente al estado del arte:** el Paper 4 (Fidalgo Astorquia et al., 2025) logra paridad entre métodos solo mediante adaptadores ROS/MoveIt. Esta ruta la logra en el propio motor de física, lo que constituye un protocolo de comparación más estricto que el del antecedente más cercano.

---

## 2. Stack técnico

| Capa | Herramienta |
|---|---|
| Simulador único | Gazebo Harmonic + `ros2_control` (ROS 2 Jazzy) |
| Entorno de aprendizaje | Entorno Gymnasium propio, arquitectura de 3 capas (tarea / robot / simulación) |
| Algoritmo | Stable-Baselines3 — SAC desde cero |
| Línea base | MoveIt 2 + OMPL (RRT-Connect, RRT*) |
| Modelo del robot | `ur_description` / `ur_simulation_gz` — UR5e de 6 GDL |
| CAD de celda | FreeCAD / SolidWorks → URDF/SDF, cargado como escena de Gazebo |
| Análisis | NumPy, SciPy (Wilcoxon), Matplotlib |

**Precedente del patrón:** `gym-gazebo2` y `ros_gazebo_gym` documentan la arquitectura de 3 capas (entorno de simulación / entorno de robot / entorno de tarea). Se adopta ese patrón, no ese código.

## 3. Estado de requisitos previos

| Requisito | Estado actual |
|---|---|
| Ubuntu 24.04 + ROS 2 Jazzy | **Instalado** |
| Gazebo Harmonic + `ros_gz`, `ros_gz_bridge`, `ros_gz_sim` | **Instalado** |
| `ompl` | **Instalado** |
| MoveIt 2 | Falta instalar |
| Paquetes UR (`ur_description`, `ur_simulation_gz`) | Faltan |
| `gymnasium`, `stable-baselines3`, `torch` | Faltan |
| GPU NVIDIA | Opcional. Acelera la red de SAC, pero la física de Gazebo corre en CPU |

> La base de esta ruta ya está instalada en la máquina. La semana 1 consiste en instalar cuatro cosas, no en montar un stack desde cero.

---

## 4. Paquetes de trabajo

> **Persona B** es quien ya tiene experiencia en ROS 2, y por eso toma la ruta crítica de las semanas 1-2.

### E1 — Entregable de diseño mecánico

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| A.1 | Diseño CAD de la celda de machine tending de CNC: pedestal, centro CNC, mesa de piezas, utillaje, obstáculos móviles (prensas, carros, piezas en tránsito) | A | 1-2 |
| A.2 | Parámetros de Denavit-Hartenberg del UR5e (6 GDL); cinemática directa e inversa | A | 2 |
| A.3 | Envolvente de trabajo y análisis de alcanzabilidad de las poses de recogida y depósito | A | 2-3 |
| A.4 | Análisis de singularidades de muñeca; justificación formal del espacio de acción Δq | A | 3 |
| B.2 | Importar la celda CAD a URDF/SDF y montarla como escena de Gazebo con geometría de colisión simplificada | B | 2 |

**Entregable:** memoria de diseño mecánico con planos, tabla DH, ecuaciones de cinemática, mapa de alcanzabilidad y la celda funcionando como escena de simulación.

> El diseño mecánico **no es un anexo**: es la entrada geométrica del experimento. La celda que se diseña es la celda donde se mide.

### E2 — Entregable electrónico (reformulado: arquitectura de sensado y comunicaciones)

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| A.9 | Arquitectura de control de celda: controlador UR5e, PLC, bus de comunicación, jerarquía de mando | A | 4 |
| A.10 | Especificación de la instrumentación que produciría el vector de observación (LiDAR 3D, cámaras de profundidad, escáner de seguridad) | A | 4 |
| A.11 | Presupuesto de latencia: sensado + inferencia de la política + ejecución, contra el período de control | A | 5 |
| A.12 | Cadena de seguridad: paro de emergencia, enclavamientos, categoría de seguridad | A | 5 |

**Entregable:** documento de arquitectura electrónica con diagrama de bloques, selección justificada de sensores y análisis de latencia.

> Este entregable convierte el supuesto de percepción ideal de una **limitación** en una **decisión de diseño con ruta de realización identificada**, y responde por adelantado la objeción "asumes percepción perfecta, eso no existe".

### E3 — Entregable de software y control

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| C.1 | **Contrato de escenarios y definición formal de las 5 métricas** — antes de escribir código que las consuma | A + B | 1 |
| B.1 | Workspace ROS 2: instalar MoveIt 2, `ur_simulation_gz`, UR5e de 6 GDL, `ros2_control` | B | 1 |
| B.3 | **Capas de robot y simulación del entorno Gym**: servicios de reset, sincronización de tiempo de simulación, control de paso, modo headless | B | 3-4 |
| A.5 | **Capa de tarea del entorno Gym**: reset de episodio, condiciones de terminación, cálculo de recompensa | A | 3-4 |
| A.6 | Formulación del MDP: acción Δq acotada y su mapeo a `ros2_control`; espacio de observación | A | 3 |
| A.7 | Función de recompensa multiobjetivo: colisión, autocolisión, alcance de meta, suavidad de movimiento | A | 4-5 |
| B.4 | Configuración de OMPL: RRT-Connect y RRT* con parámetros documentados | B | 2 |
| B.5 | `moveit_ros_benchmarks` para tiempo de cómputo, longitud de trayectoria y tasa de éxito (previendo el problema de `warehouse_mongo`) | B | 2-5 |
| B.6 | **Módulo analítico de distancia mínima eslabón-obstáculo, validado contra FCL** — es la observación del MDP y 2 de las 5 métricas | B | 2-4 |
| B.7 | Generador paramétrico de escenarios: posición, escala y forma. **Fuente única** para RL y clásico | B | 6 |
| A.8 | Entrenamiento SAC desde cero: 3 semillas sobre los escenarios núcleo (5 si el cronograma lo permite) | A | 5-7 |
| A.13 | (Extensión) Subprueba PPO bajo la misma recompensa | A | — |

> **B.6 y B.7 son de uso compartido:** alimentan al RL y al clásico por igual. Se acuerdan en C.1 antes de que cada quien escriba código que los consuma. Si cada uno define obstáculos o distancias a su manera, la comparación pierde validez y el aporte central del proyecto se cae.

### E4 — Entregable de implementación

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| C.2 | Cálculo de las 5 métricas para ambos métodos; protocolo estadístico (medias, desviaciones, Wilcoxon) | A + B | 8 |
| C.3 | Análisis de generalización — escenario 8, fuera de distribución | A | 8 |
| C.4 | Tablero comparativo y demo en vivo con obstáculos propuestos durante la sustentación | B | 9 |
| C.5 | Informe final y repositorio reproducible | A + B | 9-10 |
| C.6 | Slides y ensayo de sustentación | A + B | 10 |

---

## 5. Alcance experimental (recortado a 10 semanas)

**Núcleo obligatorio** — es lo que responde la pregunta de investigación:

| # | Escenario | Por qué es núcleo |
|---|---|---|
| 1 | Espacio libre | Control experimental |
| 2 | Obstáculo prismático único | Maniobra base |
| 4 | Obstáculo desplazado | **Eje de variabilidad: posición** |
| 5 | Obstáculo redimensionado | **Eje de variabilidad: escala** |
| 6 | Forma mutada | **Eje de variabilidad: morfología** |
| 8 | Utillaje no visto en entrenamiento | **Escenario decisivo: fuera de distribución** |

**3 semillas**, 100 episodios de evaluación con política determinista.

**Extensión si el cronograma lo permite:** escenarios 3 (tres obstáculos) y 7 (paso estrecho), subir a 5 semillas, subprueba PPO.

Declarar este recorte explícitamente en el informe como decisión de alcance.

---

## 6. Cronograma con compuertas de decisión

| Sem | Persona A | Persona B | Hito verificable | Entregable |
|---|---|---|---|---|
| 1 | CAD celda v1; contrato de escenarios (C.1) | Instalar MoveIt 2 + paquetes UR; contrato (C.1) | UR5e de 6 GDL moviéndose en Gazebo; primer PR revisado | E1 |
| 2 | CAD + tabla DH + cinemática | Celda CAD importada a Gazebo; OMPL configurado; arranca distancia mínima | Trayectoria planificada esquivando un obstáculo | E1, E3 |
| 3 | Capa de tarea del Gym; MDP; alcanzabilidad | Capas de robot y simulación del Gym; distancia mínima validada vs FCL | `env.reset()` / `env.step()` con política aleatoria | E1, E3 |
| 4 | Recompensa v1; arquitectura de sensado | **Medición de pasos/segundo en Gazebo headless** | **COMPUERTA 1: decisión de backend con el dato en la mano** | E2, E3 |
| 5 | Entrenamiento escenarios 1-2; latencia y seguridad | Batch de línea base automatizado | Curva de aprendizaje que sube; clásico corriendo sin supervisión | E2, E3 |
| 6 | Aleatorización de dominio en entrenamiento | Generador paramétrico de escenarios 4-5-6 | **COMPUERTA 2: ¿converge con obstáculos variables?** | E3 |
| 7 | Escenario 8 (OOD); barrido de 3 semillas | Barrido completo de la línea base | Datos crudos completos en `/results` | E3, E4 |
| 8 | Análisis de generalización | Cálculo de métricas y estadística | Las 5 métricas tabuladas: RL vs RRT-Connect vs RRT* | E4 |
| 9 | Redacción del informe | Tablero comparativo y montaje de la demo | Borrador completo de informe | E4 |
| 10 | Slides y ensayo | Slides y ensayo | Defensa ensayada con la demo funcionando | E4 |

### Compuertas — son decisiones con fecha, no revisiones opcionales

**COMPUERTA 1 (semana 4) — velocidad de entrenamiento.**
Medir pasos por segundo alcanzables en Gazebo headless con la celda cargada. Si el ritmo no permite completar el entrenamiento de 3 semillas dentro de las semanas 5-7, se cambia el backend de entrenamiento a PyBullet **esa misma semana**, manteniendo la evaluación en Gazebo. La decisión se toma con el dato medido, no por intuición.

**COMPUERTA 2 (semana 6) — convergencia con obstáculos variables.**
Si la política no converge al introducir aleatorización de dominio, se reduce el rango de aleatorización y se aplica currículo progresivo. Si aun así falla, el resultado es la **caracterización de dónde falla**, que también responde la pregunta de investigación.

> Si una compuerta se deja pasar "a ver si mejora la próxima semana", se pierde el proyecto. Quien detecte que un hito no se cumple lo dice en la reunión semanal, no después.

---

## 7. Por qué el Plan B es barato

Los cuatro componentes propios —módulo de distancia mínima (B.6), generador de escenarios (B.7), banco de evaluación (C.2) y función de recompensa (A.7)— se implementan **por encima del simulador, detrás de una interfaz**. Si la Compuerta 1 obliga a cambiar el backend de entrenamiento a PyBullet, ese trabajo **no se pierde**: solo se cambia la capa de simulación.

Más aún, el cambio se reporta como **resultado de transferencia sim-to-sim**, no como fracaso: la política entrenada en un motor y evaluada en otro es un dato experimental legítimo y publicable.

---

## 8. Riesgos y contingencias

| Riesgo | Señal temprana | Contingencia |
|---|---|---|
| **Gazebo demasiado lento para entrenar** | Compuerta 1, semana 4 | Backend de entrenamiento a PyBullet; evaluación sigue en Gazebo. Se reporta como sim-to-sim |
| SAC no converge con obstáculos variables | Compuerta 2, semana 6 | Reducir rango de aleatorización; currículo progresivo. El fallo caracterizado también es resultado |
| Complejidad del entorno Gym sobre ROS 2 | Semana 3 sin `env.step()` funcionando | La ruta crítica está dividida entre A.5 y B.3; si se atrasa, simplificar a control por posición sin `ros2_control` intermedio |
| `warehouse_mongo` rompe `moveit_ros_benchmarks` | Semana 2 | Extraer métricas con scripts propios sobre la API de MoveIt 2. Ya está previsto que 2 de las 5 métricas son propias |
| El CAD de celda se vuelve un fin en sí mismo | Semana 3 sin URDF exportado | Congelar el CAD en el detalle mínimo que la simulación necesita: geometría de colisión, no estética |
| Alcance excesivo | Semana 7 sin datos crudos | Recortar a escenarios 1, 2, 6 y 8 con 3 semillas |

---

## 9. Ventajas y desventajas

**A favor**
- **Paridad experimental estricta:** mismo motor de física, mismo URDF de 6 GDL, mismo verificador de colisiones para ambos métodos. Cierra la objeción más seria contra el diseño experimental.
- **Supera al antecedente más cercano** (Paper 4), que logra paridad solo vía adaptadores.
- Aprovecha directamente la experiencia en ROS 2 de uno de los integrantes.
- La celda CAD del entregable mecánico entra directo como escena: ningún entregable es decorativo.
- Peso ingenieril genuino y verificable, sin inflar artificialmente el stack.
- La infraestructura base ya está instalada en la máquina.
- No depende de GPU.

**En contra**
- Gazebo entrena más lento que PyBullet. Es el riesgo principal, mitigado por la Compuerta 1 y un Plan B barato.
- Construir el entorno Gym sobre ROS 2 es la tarea más compleja del proyecto; ocupa la ruta crítica de las semanas 3-4.

---

## 10. Recomendación de reparto

Esta EDT usa la **división por stack**: Persona A concentra diseño de celda, sensado y aprendizaje por refuerzo; Persona B concentra infraestructura de simulación, planificación clásica y geometría.

Se prefiere sobre la división por capa porque:
1. **Reparte los entregables del curso** — cada integrante tiene entregables identificables y defendibles en la sustentación.
2. **Aprovecha la asimetría de experiencia** — quien sabe ROS 2 toma la ruta crítica inicial.
3. **Evita el bloqueo mutuo** — ambos producen desde la semana 1 y confluyen en la semana 2.
4. **Divide la ruta crítica** — el entorno Gym se parte entre A.5 y B.3 en vez de recaer sobre una sola persona.

---

**Rutas alternativas:** ver `EDT-Ruta1-PyBullet.md` (Plan B de esta ruta) y `EDT-Ruta3-IsaacSim.md`.
