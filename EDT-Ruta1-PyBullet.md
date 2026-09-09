# EDT — Ruta 1: PyBullet entrena / ROS 2 evalúa

**Proyecto:** Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de **6 GDL**
**Curso:** Proyecto Mecatrónico · FIM–UNI
**Equipo:** 2 personas · **Duración:** 10 semanas
**Manipulador:** UR5e — **6 grados de libertad, no redundante** (invariante del proyecto)

---

## 1. Resumen de la ruta

Se entrena la política en **PyBullet** (rápido, ligero, CPU) y se evalúa la línea base clásica en **ROS 2 + Gazebo + MoveIt 2 + OMPL**. Es el stack que hoy declara el documento de contexto en sus decisiones cerradas, y replica exactamente el del Paper 1 (Mao et al., 2025), la referencia metodológica directa del proyecto.

**Naturaleza de la ruta:** dos simuladores, dos motores de física, un puente de equivalencia entre ambos.

---

## 2. Stack técnico

| Capa | Herramienta |
|---|---|
| Entrenamiento | PyBullet + Gymnasium + Stable-Baselines3 (SAC) |
| Línea base | ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2 + OMPL (RRT-Connect, RRT*) |
| Modelo del robot | URDF del UR5e (6 GDL), compartido entre ambos motores |
| CAD de celda | FreeCAD / SolidWorks → URDF/SDF |
| Análisis | NumPy, SciPy (Wilcoxon), Matplotlib |

## 3. Estado de requisitos previos

| Requisito | Estado actual |
|---|---|
| Ubuntu 24.04 + ROS 2 Jazzy | Instalado |
| Gazebo Harmonic + `ros_gz` | Instalado |
| `ompl` | Instalado |
| MoveIt 2 | **Falta instalar** |
| Paquetes UR (`ur_description`, `ur_simulation_gz`) | **Faltan** |
| `pybullet`, `gymnasium`, `stable-baselines3`, `torch` | **Faltan** |
| GPU NVIDIA | No requerida por esta ruta (entrenamiento viable en CPU) |

---

## 4. Paquetes de trabajo

> **Persona B** es quien ya tiene experiencia en ROS 2.

### E1 — Entregable de diseño mecánico

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 1.1 | Diseño CAD de la celda de machine tending de CNC: pedestal, centro CNC, mesa de piezas, utillaje, obstáculos móviles | A | 1-2 |
| 1.2 | Parámetros de Denavit-Hartenberg del UR5e (6 GDL); cinemática directa e inversa | A | 2 |
| 1.3 | Envolvente de trabajo y análisis de alcanzabilidad de las poses de recogida y depósito | A | 2-3 |
| 1.4 | Análisis de singularidades de muñeca; justificación del espacio de acción Δq | A | 3 |
| 1.5 | Exportación del CAD a URDF/SDF con geometría de colisión simplificada | A + B | 3 |

**Entregable:** memoria de diseño mecánico con planos, tabla DH, ecuaciones de cinemática, mapa de alcanzabilidad y modelo exportable.

### E2 — Entregable electrónico (reformulado: arquitectura de sensado y comunicaciones)

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 2.1 | Arquitectura de control de celda: controlador UR5e, PLC, bus de comunicación, jerarquía de mando | A | 4 |
| 2.2 | Especificación de instrumentación que produciría el vector de observación (LiDAR 3D, cámaras de profundidad, escáner de seguridad) | A | 4 |
| 2.3 | Presupuesto de latencia: sensado + inferencia + ejecución vs. período de control | A | 5 |
| 2.4 | Cadena de seguridad: paro de emergencia, enclavamientos, categoría de seguridad | A | 5 |

**Entregable:** documento de arquitectura electrónica con diagrama de bloques, selección justificada de sensores y análisis de latencia.

### E3 — Entregable de software y control

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 3.1 | **Contrato de escenarios y definición formal de las 5 métricas** (antes de codificar) | A + B | 1 |
| 3.2 | Entorno Gymnasium sobre PyBullet con el UR5e de 6 GDL | A | 2-3 |
| 3.3 | Formulación del MDP: acción Δq acotada, observación por descriptores geométricos | A | 3 |
| 3.4 | Función de recompensa multiobjetivo: colisión, autocolisión, alcance de meta, suavidad | A | 4 |
| 3.5 | Entrenamiento SAC desde cero — escenarios 1 y 2 | A | 5 |
| 3.6 | Aleatorización de dominio (posición, escala, forma) e integración de escenarios 4-5-6 | A | 6 |
| 3.7 | Entrenamiento completo: 5 semillas × escenarios núcleo | A | 6-7 |
| 3.8 | Workspace ROS 2: `ur_simulation_gz`, UR5e, `ros2_control`, MoveIt 2 | B | 1-2 |
| 3.9 | Configuración de OMPL: RRT-Connect y RRT* con parámetros documentados | B | 2 |
| 3.10 | `moveit_ros_benchmarks` para tiempo, longitud y tasa de éxito (previendo `warehouse_mongo`) | B | 2-3 |
| 3.11 | **Módulo de distancia mínima eslabón-obstáculo, validado contra FCL** | B | 3-4 |
| 3.12 | Generador paramétrico de escenarios, fuente única para ambos motores | B | 4 |
| 3.13 | **Verificación de equivalencia PyBullet ↔ Gazebo**: mismo URDF, mismos límites articulares, misma geometría de colisión, misma escala | A + B | 4-5 |
| 3.14 | Ejecución batch de la línea base clásica sobre escenarios núcleo | B | 6-7 |
| 3.15 | (Extensión) Subprueba PPO bajo la misma recompensa | A | 8 |

> **3.13 es el paquete de trabajo característico de esta ruta.** Como la política se entrena en un motor de física y el clásico se mide en otro, hay que demostrar que ambos modelos son equivalentes. Sin este paquete, la comparación es atacable.

### E4 — Entregable de implementación

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 4.1 | Cálculo de las 5 métricas para ambos métodos | A + B | 8 |
| 4.2 | Protocolo estadístico: medias, desviaciones, prueba de Wilcoxon | A + B | 8 |
| 4.3 | Análisis de generalización — escenario 8, fuera de distribución | A | 8 |
| 4.4 | Tablero comparativo y demo en vivo | B | 9 |
| 4.5 | Informe final | A + B | 9-10 |
| 4.6 | Slides y ensayo de sustentación | A + B | 10 |

---

## 5. Cronograma

| Sem | Persona A | Persona B | Hito verificable |
|---|---|---|---|
| 1 | CAD celda v1; contrato de escenarios | Instalar MoveIt 2 y paquetes UR; contrato de escenarios | UR5e visible en Gazebo |
| 2 | CAD + DH + alcanzabilidad | `ur_simulation_gz` + OMPL configurado | Trayectoria planificada con RRT-Connect |
| 3 | Entorno Gym en PyBullet + MDP | Módulo de distancia mínima | `env.step()` funcionando; distancias validadas vs FCL |
| 4 | Recompensa v1; arquitectura de sensado | Generador de escenarios; benchmarks | **Equivalencia PyBullet↔Gazebo verificada** |
| 5 | Entrenamiento escenarios 1-2 | Batch de línea base automatizado | Curva de aprendizaje que sube |
| 6 | Aleatorización de dominio; escenarios 4-5-6 | Corridas de línea base | **Compuerta: ¿converge con obstáculos variables?** |
| 7 | Entrenamiento 5 semillas | Barrido completo del clásico | Datos crudos completos |
| 8 | Escenario 8 (OOD); extensión PPO | Métricas y estadística | 5 métricas tabuladas |
| 9 | Informe | Tablero y demo | Borrador de informe completo |
| 10 | Slides y ensayo | Slides y ensayo | Defensa ensayada |

---

## 6. Riesgos específicos de esta ruta

| Riesgo | Impacto | Contingencia |
|---|---|---|
| **Objeción metodológica por doble motor de física** | Alto — ataca el núcleo del aporte | Paquete 3.13 obligatorio y documentado en el informe. Reportar explícitamente las diferencias residuales entre motores |
| Divergencia entre el URDF de PyBullet y el de Gazebo | Medio | Fuente única de URDF en el repositorio; prueba automatizada que compara límites y geometría |
| Doble mantenimiento de escenarios | Medio | El generador paramétrico (3.12) emite para ambos motores desde una sola definición |
| `warehouse_mongo` rompe `moveit_ros_benchmarks` | Bajo | Extraer métricas con scripts propios sobre la API de MoveIt 2 |
| El proyecto se percibe poco ingenieril | Medio | El peso está en E1, E2, 3.11 y 3.13, no en el simulador. Debe hacerse explícito en la sustentación |

---

## 7. Ventajas y desventajas

**A favor**
- La más rápida de levantar: el entrenamiento arranca en la semana 3.
- Replica exactamente el stack del Paper 1, lo que refuerza el argumento de "misma formulación + los tres elementos ausentes".
- **Mayor cobertura experimental:** al ahorrar tiempo de infraestructura, caben las 5 semillas y los 8 escenarios completos, no solo el núcleo recortado.
- No requiere GPU.
- Menor riesgo técnico: PyBullet es predecible y rápido para entrenar.

**En contra**
- **Hueco metodológico:** entrenar y comparar en motores distintos es atacable en la sustentación, y obliga al paquete 3.13.
- Doble infraestructura de escenarios que mantener.
- Es la ruta que se percibe más ligera para un proyecto de 10 semanas.

---

## 8. Cuándo elegir esta ruta

Elegir la Ruta 1 si se prioriza **cobertura experimental y bajo riesgo técnico** sobre pureza metodológica, o si la Compuerta 1 de la Ruta 2 demuestra que Gazebo es demasiado lento para entrenar. En ese segundo caso, esta ruta **es** el Plan B de la Ruta 2 y el cambio cuesta poco, porque los módulos propios están detrás de una interfaz independiente del simulador.

**Rutas alternativas:** ver `EDT-Ruta2-ROS2-Unificado.md` (recomendada) y `EDT-Ruta3-IsaacSim.md`.
