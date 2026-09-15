# EDT — PyBullet entrena / ROS 2 evalúa **(RUTA ADOPTADA)**

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

*Verificado el 2026-09-13.*

| Requisito | Estado |
|---|---|
| Ubuntu 24.04 + ROS 2 Jazzy | Instalado |
| Gazebo Harmonic + `ros_gz`, `ros_gz_bridge`, `ros_gz_sim` | Instalado |
| `ompl` | Instalado |
| MoveIt 2 (2.12.4, con `moveit_planners_ompl` y `moveit_ros_benchmarks`) | Instalado |
| Paquetes UR (`ur_description` 3.5.1, `ur_simulation_gz` 2.5.0, `ur_moveit_config`) | Instalado |
| `gymnasium` 1.3.0, `stable-baselines3` 2.9.0, `torch` 2.14.0+cpu | Instalado en `.venv/` |
| **`pybullet`** | Instalado en `.venv/` — **es el simulador de entrenamiento de esta ruta** |
| GPU NVIDIA | No requerida. `nvidia-smi` no responde en esta máquina; torch quedó en versión CPU |

> El entorno está completo. El detalle operativo pendiente está en `docs/nota-tecnica-semana1.md`:
> el shell por defecto es zsh y `setup.bash` de ROS 2 falla ahí, hay un desajuste de nombre entre
> URDF y SRDF en los paquetes de Jazzy, y `ur_moveit_config` no declara `planner_configs`.

---

## 4. Paquetes de trabajo

> **Persona A:** diseño de celda y componentes (E1), y la parte de aprendizaje por refuerzo de E3.
> **Persona B:** electrónica de control (E2), y la parte clásica de E3 — ROS 2, OMPL, benchmarks,
> distancia mínima, generador de escenarios y línea base. Es quien ya tiene experiencia en ROS 2.
>
> Los paquetes de E2 se ubican en las semanas 5-8 de la Persona B, cuando sus corridas de línea
> base son desatendidas y tiene holgura real. Las semanas 1-4 siguen ocupadas por la ruta crítica
> de ROS 2.

### E1 — Entregable de diseño mecánico: biblioteca modular de celda

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 1.1 | Celda base de *machine tending* de CNC: layout general, pedestal del robot, envolvente de seguridad | A | 1 |
| 1.2 | **Biblioteca de componentes CAD individuales**, cada uno exportable por separado: centro CNC, mesa de piezas, utillaje, prensa, carro de transporte, pieza en tránsito, y obstáculos primitivos (prisma, cilindro, esfera) | A | 1-2 |
| 1.3 | Geometría de colisión simplificada por componente, separada de la geometría visual | A | 2 |
| 1.4 | Exportación a URDF/SDF con convención de anclaje que permita componer escenarios | A + B | 2-3 |
| 1.5 | Parámetros de Denavit-Hartenberg del manipulador de 6 GDL; cinemática directa e inversa | A | 2 |
| 1.6 | Envolvente de trabajo y análisis de alcanzabilidad de las poses de recogida y depósito | A | 2-3 |
| 1.7 | Análisis de singularidades de muñeca; justificación del espacio de acción Δq | A | 3 |

**Entregable:** memoria de diseño mecánico con planos de la celda y de cada componente, tabla DH, ecuaciones de cinemática, mapa de alcanzabilidad, y la biblioteca exportada.

#### Cobertura verificada: los 8 escenarios salen de la biblioteca

| # | Escenario del protocolo | Se compone como |
|---|---|---|
| 1 | Espacio libre | Celda base sola |
| 2 | Obstáculo prismático único | Celda base + prisma |
| 3 | Tres obstáculos concurrentes | Celda base + prensa + carro + pieza en tránsito |
| 4 | Obstáculo desplazado | Prisma del escenario 2, con **pose** distinta |
| 5 | Obstáculo redimensionado | Prisma del escenario 2, con **escala** distinta |
| 6 | Forma mutada | Prisma sustituido por cilindro o esfera |
| 7 | Paso estrecho | Celda base + dos prismas con holgura parametrizada |
| 8 | Utillaje no visto | Utillaje + prensa + carro en poses ausentes del entrenamiento |

> Ningún escenario exige geometría fuera de la biblioteca. Los escenarios 4, 5 y 6 —los ejes de
> variabilidad que sostienen la pregunta de investigación— se obtienen variando **pose, escala y
> morfología** del mismo componente, así que los componentes deben modelarse con esos tres
> parámetros expuestos, no como sólidos fijos.

> **No se diseñan celdas completas por escenario, sino piezas que se componen.** El paquete 3.12 deja de generar primitivas geométricas propias y pasa a **componer los 8 escenarios experimentales a partir de esta biblioteca**. Cada escenario queda definido como una lista de componentes con su pose, escala y orientación — una sola fuente de geometría para todo el proyecto.

### E2 — Entregable electrónico: diseño de la electrónica de control

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 2.1 | **Dimensionamiento de actuadores** para reproducir la envolvente del manipulador de referencia: 150 N·m en hombro y codo, 28 N·m en muñeca, velocidad máxima π rad/s | B | 5 |
| 2.2 | Selección de reductores y transmisión; relación de reducción por articulación | B | 5 |
| 2.3 | Etapa de potencia: drivers de motor, fuente de alimentación, protecciones | B | 6 |
| 2.4 | **Unidad de cómputo y microcontrolador**: debe ejecutar la inferencia de la política SAC dentro del período de control | B | 6 |
| 2.5 | Sensado: encoders por articulación, y la instrumentación que produciría el vector de observación del MDP | B | 7 |
| 2.6 | Arquitectura de comunicación: bus entre articulaciones y con el controlador de celda | B | 7 |
| 2.7 | Cadena de seguridad: paro de emergencia, enclavamientos, categoría de seguridad | B | 8 |
| 2.8 | Presupuesto de latencia del lazo: sensado + inferencia de la política + actuación, contra el período de control | B | 8 |

**Entregable:** memoria de diseño electrónico con diagrama de bloques, cálculos de dimensionamiento, selección justificada de componentes, esquema de comunicación y análisis de seguridad.

#### Los dos enganches que hacen que E2 no quede aislado

**Con E3 — el cómputo tiene que correr la política.** El paquete 2.4 no es una selección genérica de microcontrolador: la unidad elegida debe ejecutar el paso hacia adelante de la red de SAC dentro del período de control. Eso ata el entregable electrónico al resultado del entrenamiento y da contenido real al presupuesto de latencia de 2.8.

**Con E1 — el dimensionamiento sale de la dinámica, no del catálogo.** Los 150 y 28 N·m del URDF son *límites de esfuerzo*, no el par que la tarea realmente exige. El dimensionamiento riguroso se obtiene por **dinámica inversa sobre las trayectorias generadas**, con `p.calculateInverseDynamics()` de PyBullet aplicado a las trayectorias del entrenamiento y de la línea base, para extraer el par demandado real por articulación.

> Esto le da al entregable electrónico las ecuaciones y el rigor cuantitativo que el curso exige, en lugar de una selección por catálogo, y reutiliza datos que el proyecto ya produce.

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
| 3.12 | Generador paramétrico de escenarios: **compone los 8 escenarios a partir de la biblioteca CAD de E1** (pose, escala, orientación por componente). Fuente única para ambos motores | B | 4 |
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

El curso fija **15 semanas: 14 de desarrollo más la sustentación**. Las semanas 1-4 cubrieron la
definición del proyecto y el montaje del entorno, ya ejecutados. **Los paquetes de esta EDT corren
de la semana 5 a la 14**, salvo los cuatro adelantados que aparecen abajo.

El cronograma detallado, fase por fase y paquete por paquete, está en
`Cronograma RL Manipulador 6GDL.xlsx`, generado desde `tools/gen_cronograma.py`.

### Ya ejecutado al cierre de la semana 4

| Paquete | Actividad | Sem |
|---|---|---|
| 3.8 | Workspace ROS 2, MoveIt 2 y `ur_simulation_gz`; simulación levantada y verificada | 1-3 |
| 1.5 | Tabla DH y cinemática directa e inversa | 4 |
| 3.1 | Contrato de escenarios y definición formal de las 5 métricas | 4 |
| 3.9 | Configuración de OMPL con RRT-Connect y RRT\* | 4 |

Más la fase de documentación: planteamiento del problema, estado del arte, y esta EDT con su
cronograma.

### Desarrollo, semanas 5 a 14

| Sem | Persona A | Persona B | Hito verificable |
|---|---|---|---|
| 5 | Celda base y biblioteca CAD (1.1, 1.2) | Workspace consolidado; benchmarks OMPL (3.10) | Componentes exportables |
| 6 | Geometría de colisión; entorno Gym (1.3, 3.2) | Distancia mínima (3.11) | `env.step()` funcionando |
| 7 | Exportación URDF; alcanzabilidad; MDP (1.4, 1.6, 1.7, 3.3) | Distancia mínima validada vs FCL | Distancias validadas |
| 8 | Recompensa v1 (3.4) | Generador de escenarios (3.12) | **Equivalencia PyBullet↔Gazebo verificada** (3.13) |
| 9 | Entrenamiento escenarios 1-2 (3.5) | **E2: actuadores y reductores** (2.1, 2.2) | Curva de aprendizaje que sube |
| 10 | Aleatorización de dominio (3.6, 3.7) | Línea base batch (3.14) · **E2: potencia y cómputo** (2.3, 2.4) | **Compuerta: ¿converge?** |
| 11 | Entrenamiento 5 semillas (3.7) | Barrido del clásico · **E2: sensado y comunicación** (2.5, 2.6) | Datos crudos completos |
| 12 | Escenario 8 y extensión PPO (3.15, 4.3) | Métricas y estadística (4.1, 4.2) · **E2: seguridad y latencia** (2.7, 2.8) | 5 métricas tabuladas; E2 cerrado |
| 13 | Informe (4.5) | Tablero y demo (4.4) | Borrador de informe |
| 14 | Slides (4.6) · Paper IEEE | Paper IEEE | Paper y defensa listos |
| **15** | **Sustentación** | **Sustentación** | Proyecto presentado |

> El entregable documentario del curso es un **paper en formato IEEE**. El informe final es la base
> de la tesis posterior.

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

## 8. Fundamento de la elección

Se adopta esta ruta por **cobertura experimental y bajo riesgo técnico**: el entrenamiento arranca en la semana 3, no depende de GPU, y replica exactamente el stack del Paper 1 (Mao et al., 2025), la referencia metodológica directa del proyecto. El tiempo ahorrado en infraestructura se invierte en experimentos: caben las 5 semillas y los 8 escenarios completos.

**El precio a pagar está identificado y tiene mitigación asignada.** Entrenar en un motor de física y medir la línea base en otro es atacable en la sustentación. Por eso el **paquete 3.13 (verificación de equivalencia PyBullet ↔ Gazebo) no es opcional**: es la condición que sostiene la validez de toda la comparación. Debe ejecutarse en la semana 4 y documentarse en el informe, reportando explícitamente las diferencias residuales entre motores.

> Respuesta preparada para la sustentación: *«el supuesto de equivalencia entre motores está verificado y cuantificado en la sección X; el mismo URDF, los mismos límites articulares y la misma geometría de colisión alimentan ambos pipelines desde una fuente única»*.

---

## 9. Compuertas de decisión

| Compuerta | Semana | Criterio |
|---|---|---|
| **1 — Equivalencia entre motores** | 8 | El mismo escenario cargado en PyBullet y en Gazebo debe coincidir en geometría, posición, escala y límites articulares. Si no coincide, se detiene el entrenamiento hasta resolverlo: entrenar sobre un modelo que no es el que se mide invalida los resultados |
| **2 — Convergencia** | 10 | Si la política no converge al introducir aleatorización de dominio, reducir el rango y aplicar currículo progresivo. Si aun así falla, el resultado es la caracterización de dónde falla, que también responde la pregunta de investigación |

Son decisiones con fecha. Si se dejan pasar «a ver si mejora la próxima semana», se pierde el proyecto.
