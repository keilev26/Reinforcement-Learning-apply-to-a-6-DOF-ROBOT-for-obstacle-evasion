# EDT — PyBullet entrena / ROS 2 evalúa **(RUTA ADOPTADA)**

**Proyecto:** Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de **6 GDL**
**Curso:** Proyecto Mecatrónico · FIM–UNI
**Equipo:** 2 personas · **Duración:** 10 semanas
**Manipulador:** DOBOT Magician E6 — **6 grados de libertad, no redundante** (invariante del proyecto)

> **Cambio de robot en la semana 5 (2026-09-22).** Las semanas 1-4 se trabajaron con el UR5e. El
> profesor dispone de un Magician E6 físico, y el proyecto pasa a ese robot para que la política
> sea desplegable en él. El alcance obligatorio sigue siendo **algoritmo de RL y simulación**; la
> prueba en el robot real es **trabajo adicional** fuera de las 15 semanas (sección 10). Motivo y
> detalle: `semana-05/evaluacion-magician-e6.md` y `semana-05/propuesta-migracion-magician-e6.md`.

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
| Modelo del robot | `rl6gdl_e6_description`: URDF corregido del Magician E6, generado desde el oficial de Dobot con `tools/gen_modelo_e6.py`. Fuente única para ambos motores |
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
| Paquetes UR (`ur_description` 3.5.1, `ur_simulation_gz` 2.5.0, `ur_moveit_config`) | Instalado. Usados en las semanas 1-4; ya no son el robot del proyecto |
| Modelo del Magician E6 (`rl6gdl_e6_description`) | **Generado y probado** el 2026-09-22: carga en PyBullet, pasa `check_urdf`, 9 pruebas |
| MoveIt 2 con el E6 en Jazzy | **Configuración propia hecha** el 2026-09-22: `planning_e6.launch.py`, SRDF generado desde la matriz de colisiones. Contrato v2.0 verificado: 19/19 variantes, 0 colisiones |
| Gazebo Harmonic con el E6 | **Hecho** el 2026-09-22: `rl6gdl_e6_gazebo` con `gz_ros2_control`; la tarea del contrato se **ejecuta** en los 8 escenarios sin colisión (`semana-05/3.8-gazebo-magician-e6.md`) |
| `gymnasium` 1.3.0, `stable-baselines3` 2.9.0, `torch` 2.14.0+cpu | Instalado en `.venv/` |
| **`pybullet`** | Instalado en `.venv/` — **es el simulador de entrenamiento de esta ruta** |
| GPU NVIDIA | No requerida. `nvidia-smi` no responde en esta máquina; torch quedó en versión CPU |

> El entorno está completo. El detalle operativo pendiente está en `semana-03/nota-tecnica-entorno.md`:
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
| 1.1 | Celda de *machine tending* **de escritorio** para el E6 (escala ~1:2): layout, robot montado sobre la mesa, envolvente de seguridad | A | 1 |
| 1.2 | **Biblioteca de componentes CAD individuales** a escala de escritorio, cada uno exportable por separado: centro CNC, mesa de piezas, utillaje, prensa, carro de transporte, pieza en tránsito, y obstáculos primitivos (prisma, cilindro, esfera). Diseñados para poder fabricarse (trabajo adicional) | A | 1-2 |
| 1.3 | Geometría de colisión simplificada por componente de celda, separada de la geometría visual. La del robot ya está hecha (3.16) | A | 2 |
| 1.4 | Exportación a URDF/SDF con convención de anclaje que permita componer escenarios | A + B | 2-3 |
| 1.5 | Parámetros de Denavit-Hartenberg del **Magician E6**; cinemática directa e inversa. Se derivan del URDF oficial y se contrastan con él | A | 2 |
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

### E2 — Entregable electrónico: electrónica de control e integración del Magician E6

El E6 existe, con su controlador. El E2 ya no dimensiona los actuadores de un robot hipotético:
**diseña la integración electrónica y de control** que permitiría ejecutar la política en el robot
real, y verifica con el modelo que las trayectorias generadas son físicamente ejecutables. Todo se
resuelve con documentación del fabricante y con el modelo; la medición en el robot es trabajo
adicional (sección 10).

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 2.1 | **Análisis dinámico**: par demandado por las trayectorias de la política y de la línea base (dinámica inversa con `p.calculateInverseDynamics()`), frente al par estimado del modelo | B | 5 |
| 2.2 | **Arquitectura de control del E6**: controlador, interfaz TCP/IP (puerto 29999 de comandos, 30004 de estado cada 8 ms), lazo `ServoJ` a 33 Hz | B | 5 |
| 2.3 | **Efector final**: ventosa o pinza, E/S digitales de la brida, presupuesto de carga útil (0.75 kg incluido el efector) | B | 6 |
| 2.4 | **Unidad de cómputo**: la inferencia de la política debe caber en el período de control de 30 ms. Se mide en la PC del proyecto | B | 6 |
| 2.5 | **Sensado**: cómo se obtendría la pose de los obstáculos en la celda real (plantilla de colocación) y su error; origen de cada componente del vector de observación | B | 7 |
| 2.6 | **Comunicación** PC ↔ controlador: protocolo, frecuencia, *jitter* admisible | B | 7 |
| 2.7 | **Cadena de seguridad**: parada de emergencia, detección de colisión del E6, capa de seguridad de software que filtra cada comando | B | 8 |
| 2.8 | **Presupuesto de latencia del lazo**: lectura de q + inferencia + `ServoJ`, contra el período de 30 ms | B | 8 |

**Entregable:** memoria de diseño electrónico con diagrama de bloques de la integración, análisis
dinámico, esquema de comunicación, cadena de seguridad y presupuesto de latencia.

#### Los dos enganches que hacen que E2 no quede aislado

**Con E3 — el período de control sale del hardware.** Los 30 ms del MDP son el período que Dobot
recomienda para `ServoJ`, y el paso máximo de la acción (0.05 rad) sale de la velocidad articular
del E6. El paquete 2.4 verifica que la inferencia de la política cabe en ese período, y el 2.8 que el
lazo completo también.

**Con E1 — el análisis dinámico usa el modelo del robot.** El par demandado se calcula por
**dinámica inversa sobre las trayectorias que el propio proyecto genera**, con el modelo de
`rl6gdl_e6_description`. Como las masas del modelo son estimaciones (el fabricante no las publica),
el resultado se reporta como estimación y con esa salvedad.

> El E2 conserva el rigor cuantitativo que el curso exige (ecuaciones de dinámica, presupuesto de
> latencia) y deja la integración diseñada para el trabajo adicional con el robot real.

### E3 — Entregable de software y control

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 3.1 | **Contrato de escenarios y definición formal de las 5 métricas** (antes de codificar). **v2.0 a escala del E6** | A + B | 1 |
| 3.2 | Entorno Gymnasium sobre PyBullet con el **Magician E6**: Δt = 30 ms, transición cinemática, 3 subpasos de revisión de colisión por paso | A | 2-3 |
| 3.3 | Formulación del MDP: acción Δq acotada a 0.05 rad, observación de 43 valores calculables en el robot real (sección 4.1) | A | 3 |
| 3.4 | Función de recompensa multiobjetivo: colisión, autocolisión, alcance de meta, suavidad. Longitudes normalizadas por la longitud de la tarea | A | 4 |
| 3.5 | Entrenamiento SAC desde cero — escenarios 1 y 2 | A | 5 |
| 3.6 | Aleatorización de dominio (posición, escala, forma) e integración de escenarios 4-5-6 | A | 6 |
| 3.7 | Entrenamiento completo: 5 semillas × escenarios núcleo | A | 6-7 |
| 3.8 | Workspace ROS 2: `ros2_control`, MoveIt 2 y Gazebo Harmonic. Hecho con el UR5e; **se rehace con el E6** (configuración de MoveIt propia en formato Jazzy, y `gz_ros2_control`) | B | 1-2 |
| 3.9 | Configuración de OMPL: RRT-Connect y RRT* con parámetros documentados. **Se vuelve a medir con el E6** (`longest_valid_segment_fraction` = 0.00067 para conservar 0.014 rad) | B | 2 |
| 3.10 | `moveit_ros_benchmarks` para tiempo, longitud y tasa de éxito (previendo `warehouse_mongo`) | B | 2-3 |
| 3.11 | **Módulo de distancia mínima eslabón-obstáculo, validado contra FCL** | B | 3-4 |
| 3.12 | Generador paramétrico de escenarios: **compone los 8 escenarios a partir de la biblioteca CAD de E1** (pose, escala, orientación por componente). Fuente única para ambos motores | B | 4 |
| 3.13 | **Verificación de equivalencia PyBullet ↔ Gazebo**: mismo URDF, mismos límites articulares, misma geometría de colisión, misma escala | A + B | 4-5 |
| 3.14 | Ejecución batch de la línea base clásica sobre escenarios núcleo | B | 6-7 |
| 3.15 | (Extensión) Subprueba PPO bajo la misma recompensa | A | 8 |
| 3.16 | **Modelo corregido del Magician E6**, fuente única para PyBullet, MoveIt y Gazebo: masas, límites, colisiones convexas y matriz de colisiones permitidas (`tools/gen_modelo_e6.py`) | A | 5 |

> **3.13 es el paquete de trabajo característico de esta ruta.** Como la política se entrena en un motor de física y el clásico se mide en otro, hay que demostrar que ambos modelos son equivalentes. Sin este paquete, la comparación es atacable.

#### Decisiones del MDP fijadas por el E6

Aprobadas el 2026-09-22 (`semana-05/propuesta-migracion-magician-e6.md`, sección 1). Se eligen para
que la política entrenada **pueda ejecutarse** en el robot real sin reentrenar, aunque esa prueba
sea trabajo adicional.

| Decisión | Valor | Motivo |
|---|---|---|
| Período de control Δt | **30 ms** (33 Hz) | Período recomendado por Dobot para `ServoJ` |
| Acción | a ∈ [−1, 1]⁶ → Δq = 0.05 · a rad | 80 % del recorrido máximo en 30 ms a 2.0944 rad/s |
| Transición | **Cinemática**: q ← clip(q + Δq) | El E6 se controla por posición; las masas del modelo son estimaciones |
| Revisión de colisiones | 3 subpasos por paso (≤ 0.017 rad) | Mismo criterio de 0.02 rad que la validación de la línea base (3.9) |
| Observación | q (6), Δq anterior (6), error de posición (3) y de orientación (4) del TCP, distancia mínima (6) y dirección (18) por eslabón: **43 valores** | Solo lo que el robot real puede calcular |
| Episodio | **300 pasos** (9 s) | Tarea de 0.43 m (contrato v2.0): ~4.3 s a 0.1 m/s, el doble de margen para rodear obstáculos |
| Éxito (M1) | **5 mm** y 0.05 rad | 1.2 % de la tarea (0.43 m); en el UR5e, 10 mm eran el 1.5 % |
| Mesa | Obstáculo explícito | El robot está montado sobre ella |

### E4 — Entregable de implementación

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 4.1 | Cálculo de las 5 métricas para ambos métodos | A + B | 8 |
| 4.2 | Protocolo estadístico: medias, desviaciones, prueba de Wilcoxon | A + B | 8 |
| 4.3 | Análisis de generalización — escenario 8, fuera de distribución | A | 8 |
| 4.4 | Tablero comparativo y demo en vivo **en simulación** | B | 9 |
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

> 3.8, 3.9 y 1.5 se hicieron con el UR5e. **Conservan su marca de realizado** (el trabajo existió y
> sus hallazgos se trasladan) y suman una barra programada en las semanas 5-6 para rehacerlos con el
> E6. Lo mismo el contrato 3.1, que pasa a la v2.0.

### Desarrollo, semanas 5 a 14

| Sem | Persona A | Persona B | Hito verificable |
|---|---|---|---|
| 5 | **Modelo del E6 (3.16, hecho)** · DH del E6 (1.5) · celda de escritorio y biblioteca (1.1, 1.2) · contrato v2.0 (3.1, con B) | **MoveIt 2 con el E6** (3.8) · OMPL con el E6 (3.9) | El E6 carga en PyBullet y planifica en MoveIt desde la misma fuente |
| 6 | Geometría de colisión; entorno Gym (1.3, 3.2) | **Gazebo Harmonic con el E6** (3.8) · benchmarks (3.10) · distancia mínima (3.11) | `env.step()` funcionando; contrato v2.0 con sus 8 escenarios válidos |
| 7 | Exportación URDF; alcanzabilidad; MDP (1.4, 1.6, 1.7, 3.3) | Distancia mínima validada vs FCL | Distancias validadas |
| 8 | Recompensa v1 (3.4) | Generador de escenarios (3.12) | **Equivalencia PyBullet↔Gazebo verificada** (3.13) |
| 9 | Entrenamiento escenarios 1-2 (3.5) | **E2: análisis dinámico y arquitectura de control** (2.1, 2.2) | Curva de aprendizaje que sube |
| 10 | Aleatorización de dominio (3.6, 3.7) | Línea base batch (3.14) · **E2: efector y cómputo** (2.3, 2.4) | **Compuerta: ¿converge?** |
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
| El cambio al E6 consume las semanas 5-6 | Medio | El modelo (3.16) ya está hecho y MoveIt ya se verificó con el E6. Lo que queda es portar, no investigar |
| Masas y par del E6 son estimaciones | Bajo para el RL, medio para E2 | La transición del MDP es cinemática y no depende de ellas. En E2 se reportan como estimación |
| La celda de escritorio deja pasos estrechos en relación con el tamaño de los eslabones | Medio | Contrato v2.0 verificado automáticamente antes de entrenar |

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

---

## 10. Trabajo adicional: prueba en el Magician E6 real (fuera de las 15 semanas)

El alcance obligatorio termina en el algoritmo de RL y su evaluación en simulación. La prueba en el
robot real **no está en el cronograma**, pero el diseño la deja preparada: el MDP usa el período y
los límites del E6 (sección 4), y el E2 diseña la integración. Si hay tiempo y acceso al robot:

| ID | Paquete | Qué exige |
|---|---|---|
| A.1 | Caracterizar `ServoJ`: retardo, error de seguimiento, velocidad de TCP | Sesión con el robot. Firmware del controlador ≥ V4.4.0.0 |
| A.2 | Verificar `tool0` y la cinemática: `GetPose()` contra el modelo en ≥ 5 posturas, error < 1 mm | Ídem |
| A.3 | Aleatorización para la transferencia: retardo 0-1 pasos, fracción alcanzada 0.85-1.0, ruido en q, error de pose del obstáculo ±5 mm | Datos de A.1; reentrenar |
| A.4 | Puente política → `ServoJ` con capa de seguridad (detiene el robot si el estado siguiente viola límites o d_min < 1 cm) | Diseño de 2.2 y 2.7 |
| A.5 | Maqueta física de la celda, obstáculos fabricados y plantilla de colocación | Biblioteca de 1.2 |
| A.6 | Validación: escenarios 1, 2, 4, 6 y 8, 10 episodios por método. **Demostración de transferencia**, sin inferencia estadística | A.1-A.5 |

Detalle en `semana-05/propuesta-migracion-magician-e6.md`, secciones 1.3 a 1.5.
