# Proyecto Mecatrónico — Documento de contexto consolidado

**Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de 6 GDL**

Curso de Proyecto Mecatrónico · Escuela Profesional de Ingeniería Mecatrónica · FIM–UNI
Estudiantes: Caleb Camargo Saavedra (20210011C) · [NOMBRE DEL COMPAÑERO] ([CÓDIGO])

> Este documento consolida el estado final del planteamiento del proyecto. Está pensado para retomar el trabajo en una sesión nueva sin perder contexto: contiene la definición, el alcance, las decisiones ya tomadas (y las alternativas descartadas, para no reabrirlas), el estado del arte verificado, los aportes redactados, la defensa preparada y los pendientes.

---

## PARTE I — CONTEXTO Y DECISIONES

### 1. Contexto del curso

El curso exige un proyecto de investigación o innovación tecnológica que involucre al menos dos áreas de la especialidad mecatrónica, con rigor científico explícito (ecuaciones y modelos matemáticos en informes y diapositivas), criterios de diseño fundamentados, validación descrita de los resultados, y demostración tangible del producto final. Contempla penalización si el proyecto resulta «netamente tecnológico y poco ingenieril».

**Restricciones asumidas:**
- **Proyecto en equipo de dos personas** (actualizado; originalmente se planteó individual).
- **Plazo de desarrollo: 10 semanas.**
- Sin cliente formal (se pierde el puntaje adicional del Artículo 14), salvo que se consiga uno vía entrevista con un integrador (ver Parte VI).
- Sin hardware físico: el proyecto es íntegramente de software y simulación.
- La «demostración tangible» se resolverá como demo en vivo del simulador con métricas comparativas en tiempo real.

### 2. Campos requeridos en el formato de entrega

El Excel del curso pide, en este orden:

Apellidos y Nombres · Código · Sección · Celular · Correo · **Área de desarrollo** · **Realidad Problemática** · **Problema** · **Proyecto Tentativo** · **Papers 1 a 5 con descripción** · **Aporte a nivel de Paper** · **Tesis 1 a 3** · **Aporte a nivel de tesis** · **Productos 1 a 3 con descripción** · **Aporte a nivel de producto** · **Aporte del trabajo** · **Patente 1** · **Patente 2**

### 3. Alternativas exploradas y descartadas

Registro breve para no reabrir discusiones ya cerradas.

| Alternativa | Motivo del descarte |
|---|---|
| RL + HER en panda-gym (reach/push/pick-and-place) | HER está muy trillado; el aporte habría sido solo reimplementación |
| Estudio de degradación de HER ante ruido de percepción | Buen tema, pero fuera del eje de planificación de trayectorias |
| Agarre adaptativo de fruta frágil (arándano, uva) | La magulladura es fenómeno de tejido biológico, no simulable con fidelidad; además baja eficiencia por ciclo |
| Paletizado adaptativo de sacos con contenido granular | Sólido, pero es problema de control adaptativo, no de planificación |
| Seguridad humano-robot con SSM predictivo (ISO/TS 15066) | El ángulo predictivo ya está publicado (trabajos tipo STAP); campo saturado |
| Seguimiento de producto en faja transportadora | Resuelto comercialmente hace décadas (ABB PickMaster, FANUC iRPickTool) |

### 4. Decisiones cerradas

- **Algoritmo:** Soft Actor-Critic (SAC), entrenado desde cero, sin demostraciones expertas.
- **Espacio de acción:** incrementos articulares acotados (Δq), no aceleraciones ni acciones cartesianas (evita singularidades de muñeca).
- **Observación:** descriptores geométricos analíticos de distancia mínima entre eslabones y obstáculos. **Sin visión artificial.**
- **Percepción:** ideal, declarada explícitamente como supuesto.
- **Línea base:** RRT-Connect y RRT* vía OMPL/MoveIt 2.
- **Obstáculos dinámicos:** elementos móviles genéricos de la celda (prensas, piezas en tránsito, carros). **No se modela al operario humano**; queda excluida la colaboración humano-robot y su marco normativo.
- **Robot:** manipulador industrial no redundante de 6 GDL. El proyecto trata sobre **un manipulador de 6 GDL**, no sobre un modelo comercial concreto.
  - Se adopta la **mecánica del UR5e como plataforma de referencia**: CAD, parámetros de Denavit-Hartenberg, envolvente de trabajo y límites articulares, por la madurez de su modelo URDF y su ecosistema abierto.
  - La **electrónica de control se rediseña** (entregable E2), dimensionada para reproducir esa misma envolvente de pares y velocidades: 150 N·m en hombro y codo, 28 N·m en muñeca, π rad/s.
  - Por construcción, **la simulación sigue siendo válida para el robot rediseñado**, porque conserva sus mismos límites dinámicos.
- **Stack:** PyBullet + Gymnasium + Stable-Baselines3 para entrenamiento; ROS 2 Jazzy + Gazebo Harmonic + MoveIt 2 + OMPL para validación y línea base. Ver `EDT.md`.
  - *Motivo:* replica exactamente el stack del Paper 1 (Mao et al., 2025), la referencia metodológica directa, lo que refuerza el argumento de «misma formulación más los tres elementos ausentes». Es también el de menor riesgo técnico y el que permite arrancar el entrenamiento en la semana 3, dejando margen para las 5 semillas y los 8 escenarios completos dentro del plazo de 10 semanas. No requiere GPU.
  - *Condición obligatoria:* al entrenar en un motor de física y medir la línea base en otro, la comparación solo es válida si ambos modelos son equivalentes. El **paquete 3.13 (verificación de equivalencia PyBullet ↔ Gazebo)** —mismo URDF, mismos límites articulares, misma geometría de colisión y escala, desde una fuente única— es obligatorio y debe documentarse en el informe, reportando las diferencias residuales entre motores.
  - *Alternativas evaluadas y descartadas:* unificar todo en ROS 2 + Gazebo construyendo el entorno Gymnasium sobre `ros2_control` daría paridad estricta, pero a costa de un entorno de entrenamiento sustancialmente más lento y de la tarea más compleja del proyecto en la ruta crítica. Isaac Sim / Isaac Lab se descartó por curva de aprendizaje incompatible con 10 semanas y porque no elimina el trabajo de ROS 2, sino que lo añade encima.
- **Métricas (las «5 métricas» que se repiten en todo el documento):** tasa de éxito, número de colisiones, longitud de trayectoria, tiempo de ejecución, distancia mínima a los obstáculos.

### 4.1 Estructura de entregables del curso

El curso organiza la entrega en cuatro componentes: electrónico, software/control, diseño mecánico e implementación. Al ser un proyecto sin hardware físico, el componente electrónico se reformula. **Ningún entregable es decorativo:** el diseño mecánico produce la geometría que consume la simulación, y el electrónico justifica el supuesto de percepción del MDP.

| ID | Entregable | Contenido |
|---|---|---|
| **E1** | Diseño mecánico | Celda base de *machine tending* de un centro CNC y **biblioteca modular de componentes CAD** —máquina, mesa, utillaje, prensa, carro, pieza en tránsito, obstáculos primitivos— cada uno exportable por separado; parámetros de Denavit-Hartenberg del manipulador de 6 GDL; cinemática directa e inversa; envolvente de trabajo y alcanzabilidad; singularidades de muñeca que fundamentan el espacio de acción Δq. **Los 8 escenarios experimentales se componen a partir de esta biblioteca: es la única fuente de geometría del proyecto.** |
| **E2** | Electrónico | Diseño de la electrónica de control del manipulador: dimensionamiento de actuadores y reductores para reproducir la envolvente de pares y velocidades; etapa de potencia; unidad de cómputo y microcontrolador; sensado por encoders e instrumentación del vector de observación; arquitectura de comunicación; cadena de seguridad; presupuesto de latencia del lazo. |
| **E3** | Software y control | Entorno Gymnasium sobre PyBullet; formulación del MDP y recompensa multiobjetivo; entrenamiento SAC desde cero; módulo analítico de distancia mínima validado contra FCL; línea base MoveIt 2 + OMPL; generador paramétrico de escenarios. |
| **E4** | Implementación | Demo en vivo con obstáculos propuestos durante la sustentación; tablero comparativo de las 5 métricas; análisis estadístico; informe y repositorio reproducible. |

> **Ningún entregable es decorativo, y los cuatro están enganchados entre sí.** La biblioteca de E1 es la geometría que compone los escenarios del experimento. En E2, la unidad de cómputo debe ejecutar la inferencia de la política entrenada en E3 dentro del período de control, y el dimensionamiento de actuadores se obtiene por dinámica inversa sobre las trayectorias que el propio proyecto genera.
>
> Este encuadre responde además dos objeciones de la sección 22: «asumes percepción perfecta, eso no existe» —E2 identifica la instrumentación que la haría real— y «¿esto es mecatrónica o informática?», ya que el proyecto integra diseño mecánico, diseño electrónico, control e inteligencia artificial.

**Pendiente bloqueante:** confirmar con el profesor la reformulación de E2 y que el diseño de celda satisface el entregable mecánico.

---

## PARTE II — DEFINICIÓN DEL PROYECTO

### 5. Área de desarrollo

Inteligencia Artificial y Machine Learning en la Industria · Robótica Industrial.

> **Nota:** en la versión inicial se había puesto «Robótica y Cobots en la Industria». Se corrigió porque el proyecto excluye la colaboración humano-robot, y mantener «Cobots» generaba una inconsistencia detectable.

### 6. Realidad problemática

En los procesos de automatización industrial, los manipuladores robóticos realizan tareas repetitivas mediante trayectorias previamente programadas según la configuración de su espacio de trabajo. Sin embargo, cuando cambian la posición de máquinas, piezas u obstáculos, estas trayectorias pueden dejar de ser eficientes o generar riesgos de colisión, requiriendo una nueva planificación.

Los métodos convencionales de planificación, como PRM, RRT y RRT*, permiten generar trayectorias libres de colisión, pero generalmente requieren realizar nuevamente el proceso de búsqueda ante cambios en el entorno. Frente a ello, el aprendizaje por refuerzo ofrece una alternativa basada en el aprendizaje de políticas de movimiento mediante la interacción con entornos simulados.

Por ello, surge la necesidad de evaluar la capacidad de un sistema basado en aprendizaje por refuerzo para planificar el movimiento de un manipulador robótico de 6 grados de libertad ante diferentes configuraciones de obstáculos, considerando indicadores como tasa de éxito, colisiones, longitud de trayectoria, tiempo de ejecución y distancia mínima a los obstáculos.

> **PENDIENTE CRÍTICO:** esta sección carece de datos cuantitativos y de fuentes. Es su punto más débil frente a los demás proyectos del curso, que presentan estadísticas oficiales. Ver Parte VI para el material de refuerzo disponible.

### 7. Problema

La dificultad para generar movimientos libres de colisión y adaptables a diferentes configuraciones de obstáculos en un manipulador robótico de 6 GDL, sin depender de una trayectoria previamente establecida para una única configuración del espacio de trabajo.

### 8. Proyecto tentativo

Desarrollo de un sistema de planificación de movimiento basado en aprendizaje por refuerzo para la evitación de obstáculos en un manipulador robótico de 6 grados de libertad aplicado a celdas de manufactura.

Desglosado según la plantilla qué / para qué / cómo / dónde:

| Dimensión | Contenido |
|---|---|
| **QUÉ** | Un sistema de planificación de movimiento reactivo basado en una política de control continuo aprendida mediante aprendizaje por refuerzo profundo para un manipulador industrial de 6 GDL. |
| **PARA QUÉ** | Para eliminar la dependencia de trayectorias preprogramadas y de la replanificación completa cuando cambia la configuración de obstáculos de la celda, reduciendo el costo de reconfiguración que hoy impide automatizar la producción de alta variedad y bajo volumen. |
| **CÓMO** | Entrenando una política condicionada a descriptores geométricos analíticos de distancia mínima, con aleatorización de dominio sobre posición, escala y forma; evaluando su generalización ante configuraciones no observadas y comparándola contra RRT-Connect y RRT* de OMPL/MoveIt 2 bajo condiciones equivalentes. |
| **DÓNDE** | En celdas de manufactura flexible de la industria metalmecánica, particularmente en abastecimiento de máquina (*machine tending*) de centros CNC; validado íntegramente en simulación. |

### 9. Pregunta de investigación

¿Bajo qué régimen de variabilidad geométrica del entorno una política de movimiento aprendida por refuerzo conserva desempeño suficiente para operar sin reprogramación, y a partir de qué punto la replanificación clásica sigue siendo necesaria?

### 10. Alcance

**Incluye:** modelado del manipulador y la celda en simulación; formulación del MDP (observación, acción, recompensa); entrenamiento de la política con SAC desde cero; implementación de la línea base clásica; protocolo experimental sobre escenarios de complejidad creciente y fuera de distribución; análisis estadístico sobre múltiples semillas.

**Excluye:** percepción artificial y procesamiento de imágenes; colaboración humano-robot y normativa asociada (ISO 10218, ISO/TS 15066); despliegue en manipulador físico y transferencia *sim-to-real*; planificación de tareas y control de bajo nivel.

**Supuesto de percepción ideal:** la posición, dimensiones y orientación de los obstáculos se leen directamente del simulador. Los resultados constituyen una cota superior de desempeño. El supuesto se aplica por igual a la política y a la línea base clásica, de modo que la comparación permanece válida.

### 11. Escenarios experimentales

| # | Configuración | Perturbación | Propósito |
|---|---|---|---|
| 1 | Espacio libre | Ninguna | Control experimental; cota superior de precisión |
| 2 | Obstáculo prismático único en la trayectoria nominal | Ninguna | Maniobra base de circunvalación |
| 3 | Tres obstáculos concurrentes | Espacial compuesta | Celda densamente poblada |
| 4 | Obstáculo desplazado | Posición del centroide | Robustez ante traslación |
| 5 | Obstáculo redimensionado | Escala volumétrica | Adaptación a cambio de dimensiones |
| 6 | Forma mutada (prisma → cilindro/esfera) | Morfología | Invarianza de la representación geométrica |
| 7 | Paso estrecho entre dos prismas | Holgura crítica | **Prueba de estrés**; se espera ventaja del método clásico |
| 8 | Configuración de utillaje no vista en entrenamiento | Fuera de distribución | **Escenario decisivo**: determina si el método elimina la reprogramación |

**Protocolo estadístico:** semillas aleatorias independientes; 100 episodios de evaluación con política determinista por semilla y escenario; media y desviación estándar; prueba de rangos con signo de Wilcoxon frente a la línea base.

**Recorte de alcance por el plazo de 10 semanas.** El protocolo completo (8 escenarios × 5 semillas × 3 métodos) no es alcanzable. Se prioriza así, y el recorte se declara explícitamente en el informe como decisión de diseño experimental:

| | Escenarios | Semillas |
|---|---|---|
| **Núcleo obligatorio** | 1, 2, 4, 5, 6 y 8 | 3 |
| **Extensión si el tiempo alcanza** | 3 y 7 | 5 |

Los escenarios 4, 5 y 6 permanecen en el núcleo porque son los ejes de variabilidad geométrica —posición, escala y morfología— que responden directamente la pregunta de investigación; el 8 es el escenario decisivo sobre generalización. Los escenarios 3 y 7 son pruebas de estrés valiosas pero no imprescindibles para sostener la conclusión.

**Formulación de hipótesis:** direccionales (qué método supera a cuál en qué métrica), nunca mediante umbrales numéricos absolutos, que comprometerían la validez del trabajo ante resultados informativos pero por debajo del valor prefijado.

---

## PARTE III — GLOSARIO DE ALGORITMOS

**RRT.** Planificador por muestreo aleatorio que construye incrementalmente un árbol de configuraciones válidas. Probabilísticamente completo; trayectorias no óptimas y quebradas.

**RRT-Connect.** Variante bidireccional de RRT: hace crecer dos árboles simultáneamente desde inicio y meta. Rápido para hallar solución factible; es el planificador por defecto en muchas implementaciones industriales.

**RRT\*.** Variante asintóticamente óptima de RRT, con fase de reconexión en cada iteración. Estándar de referencia en calidad de trayectoria, a costa de mayor tiempo de cómputo.

**PRM.** Planificador de múltiples consultas que construye un grafo previo en el espacio de configuración. Eficiente en entornos estáticos; el grafo se invalida si los obstáculos se mueven.

**OMPL.** Biblioteca de código abierto que implementa los planificadores anteriores; estándar de facto en ROS, integrada en MoveIt.

**MDP.** Formalización de un problema de decisión secuencial: espacio de estados, espacio de acciones, dinámica de transición, función de recompensa y factor de descuento.

**DDPG.** Algoritmo actor-crítico fuera de política para acciones continuas, con actor determinista. Susceptible a sobreestimación de valores y muy sensible a hiperparámetros.

**TD3.** Mejora de DDPG: dos críticos independientes tomando el mínimo, actualización retardada del actor y suavizado por ruido del objetivo. Mayor estabilidad.

**SAC.** Algoritmo actor-crítico fuera de política de máxima entropía: optimiza recompensa esperada más entropía de la política, promoviendo exploración y evitando óptimos locales. Alta eficiencia de muestreo, baja sensibilidad a hiperparámetros por ajuste automático del coeficiente de temperatura. **Algoritmo adoptado.**

**PPO.** Algoritmo en política con función objetivo recortada. Muy estable, pero de baja eficiencia de muestreo al descartar experiencia tras cada actualización.

**Geometric Fabrics.** Marco de control geométrico reactivo que codifica comportamientos (atracción, repulsión, límites) como sistemas dinámicos de segundo orden con estabilidad demostrable. Suave y en tiempo real, pero local.

**Aprendizaje curricular.** Incremento progresivo de la dificultad de la tarea durante el entrenamiento.

**Demostraciones expertas.** Trayectorias generadas por un método externo (típicamente un planificador clásico) inyectadas en el búfer de experiencia para acelerar el aprendizaje.

**Generalización fuera de distribución.** Capacidad de una política de conservar desempeño sobre configuraciones del entorno ausentes de su experiencia de entrenamiento.

---

## PARTE IV — ESTADO DEL ARTE

### 12. Papers

#### Paper 1 — Mao, Wang, Zhou, Xia & Zhang (2025)

*Design and experimental verification of a dynamic obstacle avoidance algorithm for robot manipulators based on deep reinforcement learning*
*Experimental Technology and Management* (实验技术与管理), vol. 42, n.º 4, pp. 78–85, abr. 2025. ISSN 1002-4956. **Artículo en chino con resumen en inglés.**

Propone un algoritmo de evitación de obstáculos dinámicos basado en SAC para un manipulador de 6 GDL. La recompensa combina evitación de colisiones, autocolisión, alcance del objetivo y suavidad de movimiento; el estado incluye ángulos y velocidades articulares junto con la posición del efector y puntos clave del cuerpo del robot; la acción son aceleraciones articulares. Entrenado en PyBullet con Gymnasium y Stable-Baselines3, y validado sobre un UR5 físico con cámara Intel RealSense D435, pinza OnRobot y marcadores ArUco procesados con OpenCV, logrando que el error de posición converja a cero y trayectorias suaves tanto en simulación como en hardware real.

**Limitaciones y diferencia con el proyecto.** Solo se prueba con un robot y obstáculos simples, sin evaluar múltiples configuraciones ni las cinco métricas específicas. Tampoco compara contra métodos clásicos ni evalúa generalización ante obstáculos no vistos en entrenamiento. Comparte algoritmo, robot y stack, por lo que constituye la **referencia metodológica directa** del proyecto, que conserva su formulación y añade los tres elementos ausentes.

DOI: 10.16791/j.cnki.sjg.2025.04.010
https://www.sciopen.com/article/10.16791/j.cnki.sjg.2025.04.010

---

#### Paper 2 — Fu & Tang (2025)

*Optimizing Robotic Arm Obstacle Avoidance via Improved Random Tree Star (RRT)\* and Deep Reinforcement Learning Coordination*
Symmetry 17(12), 2112

Marco híbrido que combina RRT* mejorado (con muestreo adaptativo guiado por predicción de obstáculos) con DRL: RRT* guía la exploración de la política y reduce el muestreo inválido en 62 %, mientras el DRL aporta optimización global para predecir obstáculos dinámicos. Logra 93.8 % de tasa de éxito (21.5 puntos más que RRT* tradicional), 1.97 m de longitud promedio de trayectoria y 94.7 % de éxito en colaboración multirrobot, validado en simulación y en un caso industrial de ensamblaje automotriz.

**Limitaciones y diferencia con el proyecto.** No reporta número de colisiones ni distancia mínima como métricas separadas; el RL está siempre acoplado a RRT*, de modo que por construcción resulta imposible atribuir la mejora a alguno de los dos componentes ni conocer el desempeño de una política independiente; y no prueba generalización. **Ellos acoplan, el proyecto contrasta.**

*Cautela:* los autores están adscritos a una Escuela de Industria Ligera y a una Escuela de Economía y Administración, no a grupos de robótica, y reportan métricas atípicas para el dominio (consumo energético en kWh). Citar por su planteamiento, no apoyarse en sus valores numéricos.

https://doi.org/10.3390/sym17122112

---

#### Paper 3 — Xia, Lu, Xu & Xu (2024)

*Deep Reinforcement Learning based Proactive Dynamic Obstacle Avoidance for Safe Human-Robot Collaboration*
Manufacturing Letters 41, pp. 1246–1256

Método de planificación de trayectorias con SAC para que un manipulador evite colisiones con el brazo humano, modelado como cilindro móvil en 3D, formulando el problema como MDP con función de recompensa compuesta basada en campos de separación de seguridad. Validado solo en simulación; la prueba en robot físico queda como trabajo futuro.

**Limitaciones y diferencia con el proyecto.** Solo prueba un tipo de obstáculo, sin variar configuraciones ni geometrías; no hay validación en hardware; no reporta las cinco métricas de forma sistemática ni evalúa generalización. La diferencia de fondo es el objeto de estudio: su obstáculo es un operario humano, lo que sitúa el trabajo en colaboración humano-robot con su marco normativo específico, mientras el proyecto aborda la reconfiguración geométrica de la celda. **Se cita por su aporte metodológico** —modelado de obstáculos mediante envolventes de cápsulas y recompensas por distancia de separación—, que es independiente de la naturaleza del obstáculo.

https://doi.org/10.1016/j.mfglet.2024.09.151

---

#### Paper 4 — Fidalgo Astorquia, Villate-Castillo, Tellaeche & Vazquez (2025)

*Comparative Benchmark of Sampling-Based and DRL Motion Planning Methods for Industrial Robotic Arms*
Sensors 25(17), 5282

**Es el antecedente más cercano y el pilar del argumento de aporte.** Presenta una comparación exhaustiva entre planificadores clásicos de OMPL y un planificador aprendido basado en SAC, sobre un UR3e de 6 GDL con pinza RG2. Construye un conjunto de más de 100 000 trayectorias libres de colisión generadas con OMPL en MoveIt, usadas simultáneamente como banco de pruebas de los métodos clásicos y como demostraciones expertas para entrenar el agente mediante aprendizaje curricular. Ambos enfoques se evalúan bajo paridad estricta de adaptadores ROS/MoveIt sobre tiempo de planificación, tasa de éxito y suavidad de trayectoria, con parametrización temporal óptima (TOPPRA). El planificador DRL alcanza mayores tasas de éxito y tiempos de planificación significativamente menores, con trayectorias más compactas y deterministas.

**Limitaciones y diferencia con el proyecto — LO MÁS IMPORTANTE DE TODO EL ESTADO DEL ARTE.**

1. **Su entorno no contiene obstáculos.** El vector de observación consta de 14 valores continuos: seis ángulos articulares, diferencia cartesiana de posición, diferencia de orientación en cuaterniones, y un indicador binario de colisión que solo se activa ante autocolisión o colisión con el piso. No hay ninguna variable que describa geometría, posición o dimensiones de un obstáculo. La tarea evaluada es **alcance de pose en espacio libre**, no evitación de obstáculos.
2. **No evalúa generalización geométrica.** El aprendizaje curricular endurece las tolerancias de precisión, no la dificultad del entorno.
3. **Los propios autores reconocen** que los planificadores clásicos conservan ventajas en adaptabilidad *zero-shot* y generalidad ambiental.
4. **La política se entrena con demostraciones generadas por el mismo método contra el cual compite**, comprometiendo la independencia de la comparación. El proyecto entrena desde cero.

> Frase de defensa: *«hicieron el benchmark correcto en el escenario equivocado; nosotros lo llevamos al escenario donde el problema existe».*

https://doi.org/10.3390/s25175282
PDF libre: https://pmc.ncbi.nlm.nih.gov/articles/PMC12431259/

---

#### Paper 5 — Jurgenson & Tamar (2019)

*Harnessing Reinforcement Learning for Neural Motion Planning*
Robotics: Science and Systems (RSS)

Trabajo fundacional sobre planificación de movimiento neuronal mediante aprendizaje por refuerzo, que formula la generalización como pregunta experimental central y no como observación lateral. Propone DDPG-MP, variante que incorpora demostraciones y modelo aproximado para acelerar el aprendizaje, y distingue metodológicamente entre variar las configuraciones de inicio y meta sobre obstáculos fijos, y variar la propia disposición de obstáculos. Incluye un experimento dedicado a la generalización a configuraciones no observadas, alcanzando DDPG-MP la mayor tasa de éxito de validación, de 0.93.

**Limitaciones y diferencia con el proyecto.** Escenario de laboratorio y no industrial. Emplea entrada visual de la configuración de obstáculos en lugar de descriptores geométricos analíticos, elevando dimensionalidad y costo computacional. No compara contra OMPL bajo condiciones equivalentes. Su antigüedad —anterior a la consolidación de SAC, Stable-Baselines3 y los entornos de referencia actuales— limita la comparabilidad de sus resultados. **Aporta el marco conceptual del índice de generalización**, y el proyecto traslada su pregunta a un manipulador industrial no redundante de 6 GDL con observación de baja dimensionalidad y comparación estadística frente a métodos clásicos.

https://arxiv.org/abs/1906.00214

---

### 13. Aporte a nivel de Paper

Los cinco antecedentes aportan fundamentos técnicos y metodológicos complementarios para el desarrollo del sistema propuesto. Mao et al. (2025) aportan la formulación del problema como proceso de decisión de Markov con SAC sobre un manipulador de 6 GDL, la representación del estado mediante puntos clave del cuerpo del robot y la estructura de recompensa multiobjetivo; Fu & Tang (2025) contribuyen con evidencia cuantitativa de la brecha de desempeño entre un planificador cinemático y un agente reactivo; Xia et al. (2024) proporcionan el modelado de obstáculos mediante envolventes de cápsulas y la formulación de recompensas por distancia de separación; Fidalgo Astorquia et al. (2025) aportan el protocolo de comparación equitativa entre planificadores de OMPL y políticas aprendidas bajo métricas unificadas; y Jurgenson & Tamar (2019) proporcionan el marco conceptual para evaluar la generalización ante configuraciones de obstáculos no observadas.

En conjunto, estos trabajos sustentan la selección de SAC como algoritmo, un espacio de acción en incrementos articulares, descriptores geométricos analíticos de distancia mínima como observación, y RRT-Connect y RRT* como línea base de comparación, además de aportar criterios para la validación mediante tasa de éxito, colisiones, distancia mínima, longitud de trayectoria y tiempo de ejecución. No obstante, ninguno integra simultáneamente los elementos que el problema exige: quienes evalúan políticas con obstáculos no las contrastan contra métodos clásicos en condiciones equivalentes, quien acopla ambos paradigmas no puede atribuir el desempeño a ninguno por separado, el único banco de pruebas riguroso frente a OMPL se realiza sin obstáculos en la escena, y la evaluación formal de generalización no ha sido trasladada a un manipulador industrial de 6 GDL. El aporte del presente trabajo consiste en cerrar esa intersección, determinando bajo qué régimen de variabilidad geométrica una política aprendida conserva desempeño suficiente para operar sin reprogramación en celdas de manufactura.

---

### 14. Tesis

#### Tesis 1 — Liu (2024), University of Toronto

*Geometric Fabrics Guided Learning for Collision-Free Manipulator Global Motion Generation*
Tesis de Bachelor of Applied Science in Engineering Science (Robotics). Directores: Florian Shkurti (UofT), Karl Van Wyk y Nathan Ratliff (NVIDIA Research)

Se propone entrenar una política de RL (PPO) que no controla directamente las articulaciones, sino que da comandos de alto nivel a un controlador reactivo (Geometric Fabrics), el cual genera movimiento suave y libre de colisiones. Se entrena en Isaac Gym con miles de escenarios de obstáculos y se evalúa en un Franka Panda de 7 GDL, logrando 99.15 % de éxito, 0.64 % de colisión y tiempo de reacción de aproximadamente 0.0028 s, superando a métodos previos y acercándose a planificadores globales.

**Limitaciones y diferencia con el proyecto.** Se enfoca en 7 GDL (solo prueba brevemente 6 GDL), no reporta longitud de trayectoria ni distancia mínima como métricas, y depende de un controlador intermedio en vez de que el RL controle el movimiento directamente. El proyecto emplea RL puro en 6 GDL, donde la ausencia de redundancia cinemática restringe sustancialmente el espacio de soluciones, con las cinco métricas completas.

*Valor adicional:* al ser tesis de pregrado de una institución de referencia mundial en robótica, sirve como argumento de calibración del alcance.

https://jasonjzliu.com/data/Jingzhou_Liu_University_of_Toronto_Engineering_Science_Thesis.pdf

---

#### Tesis 2 — Sanches (2021), Universidade de São Paulo

*End-to-End Visual Obstacle Avoidance for a Robotic Manipulator using Deep Reinforcement Learning*
Disertación de maestría, ICMC-USP. Directora: Roseli Aparecida Francelin Romero. DOI: 10.11606/D.55.2021.tde-30082021-100712

El estudio propone una política de RL de extremo a extremo que usa imágenes y datos propioceptivos para que un manipulador alcance una posición objetivo mientras evita un obstáculo colocado aleatoriamente en la escena. Se entrena con TD3 en un entorno simulado construido en Unity con el framework ML-Agents, demostrando que el agente aprende una política efectiva de evitación usando imágenes como entrada principal.

**Limitaciones y diferencia con el proyecto.** Solo evalúa un único obstáculo por escena, no reporta el conjunto completo de métricas cuantitativas y no valida en robot físico. Adopta la vía opuesta en percepción: aprende de imágenes, mientras el proyecto emplea descriptores geométricos analíticos. Esa diferencia es deliberada: la observación visual eleva la dimensionalidad del estado y el costo de entrenamiento sin aportar información adicional cuando la geometría del entorno es conocida.

*Antecedente latinoamericano más próximo.*

https://teses.usp.br/teses/disponiveis/55/55134/tde-30082021-100712/es.html

---

#### Tesis 3 — Fidalgo Astorquia (2025), Universidad de Deusto

*Estudio de la planificación de trayectorias en entornos dinámicos para manipuladores industriales mediante aprendizaje por refuerzo*
Tesis doctoral. Directores: Alberto Tellaeche Iglesias y Juan-Ignacio Vazquez

Estudia cómo los manipuladores industriales pueden aprender a planificar sus movimientos de forma más autónoma en entornos dinámicos, cambiantes o poco estructurados, donde los métodos clásicos —aunque probados y fiables— muestran limitaciones. Propone un proceso que combina entrenamiento en entornos virtuales, incorporación de ejemplos provenientes de métodos tradicionales y una estrategia de aprendizaje progresivo. Reporta que el enfoque permite movimientos más consistentes y seguros, ejecutables en robots reales sin largos tiempos de ajuste, y que se adapta mejor que los métodos clásicos cuando se introducen restricciones adicionales o cuando los objetivos cambian de posición, declarando entre sus aportaciones una comparación detallada frente a dichos métodos.

**Limitaciones y diferencia con el proyecto.** Su evaluación de adaptabilidad se centra en el cambio de posición del objetivo y no en la variación morfológica y dimensional de los obstáculos, que es la perturbación característica de una reconfiguración de celda. La incorporación de demostraciones provenientes de los métodos tradicionales durante el entrenamiento compromete la independencia de la comparación posterior frente a esos mismos métodos; el proyecto entrena desde cero.

> **Nota de trazabilidad obligatoria:** esta tesis y el Paper 4 corresponden al mismo autor y constituyen un único cuerpo de investigación. Debe declararse explícitamente en el informe.

https://deustoteka.deusto.es/bitstreams/e4120daf-86d2-4f56-9fb3-580ad17b5c85/download

---

### 15. Aporte a nivel de tesis

A partir de la revisión de las tesis relacionadas se observa que las soluciones existentes abordan la planificación de movimiento con aprendizaje desde enfoques parciales. La tesis desarrollada en la Universidad de Toronto propone una política de refuerzo que emite comandos de alto nivel a un controlador reactivo basado en Geometric Fabrics, alcanzando un desempeño elevado en evitación de colisiones, aunque se enfoca en un manipulador redundante de 7 GDL, delega la generación del movimiento a un controlador intermedio en lugar de que la política controle directamente el desplazamiento articular, y no reporta longitud de trayectoria ni distancia mínima como métricas. Por su parte, la investigación de la Universidad de São Paulo entrena una política de extremo a extremo que emplea imágenes junto con datos propioceptivos para evitar un obstáculo mediante TD3, pero evalúa una única obstrucción por escena, no reporta el conjunto completo de métricas cuantitativas y no valida sobre robot físico. Finalmente, la tesis doctoral de la Universidad de Deusto sí compara sistemáticamente el aprendizaje por refuerzo frente a los planificadores clásicos en entornos dinámicos, aunque centra su evaluación de adaptabilidad en el cambio de posición del objetivo y no en la variación geométrica de los obstáculos, e incorpora demostraciones de los propios métodos tradicionales durante el entrenamiento, lo que compromete la independencia de la comparación.

Frente a estas limitaciones, la presente investigación propone la evaluación de una política de aprendizaje por refuerzo entrenada desde cero, que controla directamente los incrementos articulares de un manipulador no redundante de 6 grados de libertad a partir de descriptores geométricos analíticos de distancia mínima, sometida a múltiples configuraciones de obstáculos con variación de posición, escala y forma, y contrastada estadísticamente frente a los planificadores clásicos RRT-Connect y RRT* bajo condiciones equivalentes, reportando de forma sistemática la tasa de éxito, el número de colisiones, la longitud de trayectoria, el tiempo de ejecución y la distancia mínima a los obstáculos.

---

### 16. Productos

#### Producto 1 — "RapidPlan" (Realtime Robotics, Estados Unidos)

Plataforma de planificación de movimiento libre de colisiones para robots industriales y colaborativos.

RapidPlan permite a robots industriales y colaborativos navegar entornos dinámicos, generando planes libres de colisión en milisegundos y manteniendo las trayectorias válidas incluso ante cambios en vivo del piso de planta. Su propio planteamiento comercial parte de constatar que hoy los robots se programan para ir de un punto A a un punto B por una única ruta definida, lo que valida directamente la formulación del problema abordado en este trabajo: la rigidez de las trayectorias preprogramadas ante cambios del entorno es un problema industrial reconocido y con demanda comercial real.

Sin embargo, no emplea aprendizaje automático: resuelve la búsqueda de caminos mediante algoritmos deterministas acelerados por hardware propietario, de modo que su velocidad no es transferible a software convencional ni permite evaluar el comportamiento de políticas aprendidas. Su reacción ante obstáculos dinámicos exige además el subsistema de percepción RapidSense, y opera bajo licencia empresarial cerrada con un costo por celda incompatible con la micro y pequeña empresa metalmecánica.

https://rtr.ai/rapidplan/

---

#### Producto 2 — "cuMotion" (NVIDIA Corporation, Estados Unidos)

Biblioteca de planificación de movimiento acelerada por GPU dentro de Isaac Manipulator.

cuMotion proporciona planificación de movimiento, generación de trayectorias y cinemática inversa impulsadas por GPU, entregando ejecución rápida y libre de colisiones en entornos congestionados mediante optimización global paralelizada sobre miles de núcleos. Su orientación declarada hacia líneas de ensamblaje flexibles que requieren reconfiguración frecuente de las celdas respalda la premisa central de este trabajo: la manufactura de alta variedad demanda planificación adaptativa.

Sin embargo, no emplea políticas aprendidas sino optimización numérica en línea, por lo que no amortiza el costo computacional en una fase previa de entrenamiento ni permite estudiar la generalización ante configuraciones geométricas no observadas. Exige de forma obligatoria una GPU NVIDIA dedicada a bordo, que constituye precisamente la barrera de infraestructura y costo identificada en el contexto productivo objetivo.

https://developer.nvidia.com/blog/making-industrial-robots-more-nimble-with-nvidia-isaac-manipulator-and-vention-machinemotion-ai

---

#### Producto 3 — "RoboDK" (RoboDK Inc., Canadá)

Software de simulación y programación fuera de línea multimarca para manipuladores industriales.

RoboDK realiza programación fuera de línea, calibración y verificación de colisiones para más de mil modelos de robot, e incorpora un planificador de movimiento libre de colisiones basado en **mapas de rutas probabilísticos (PRM) de implementación propia**: una fase de construcción del mapa, que se ejecuta una vez, y una fase de consulta que busca el camino más corto sobre él. Es la herramienta que emplearía realmente un taller metalmecánico de escala media que decidiera automatizar, y por eso representa la práctica efectivamente accesible en el mercado.

> **Corrección (2026-09-19).** Versiones anteriores de este documento afirmaban que RoboDK invoca OMPL con RRT, PRM o EST, y que por tanto la línea base de este trabajo usaba sus mismos planificadores. **La documentación oficial no lo respalda**: describe un PRM propio y no menciona OMPL. El argumento debe formularse con cuidado: la línea base comparte a lo sumo la *familia* de algoritmos (planificación por muestreo, y PRM si se adopta LazyPRM\* como planificador de calidad; ver `semana-04/3.9-configuracion-ompl.md`), no la implementación.

Sin embargo, calcula rutas estáticas a priori y carece de adaptación en tiempo de ejecución: los obstáculos deben permanecer inmóviles en el árbol CAD, de modo que cualquier cambio de utillaje obliga a rehacer la planificación y reexportar el programa, que es precisamente el costo de reconfiguración que este trabajo busca eliminar. Hereda además el tiempo de cómputo no determinista de los planificadores por muestreo.

https://robodk.com/doc/en/Collision-Avoidance-Collision-Free-Motion-Planner.html
https://robodk.com/doc/en/Collision-Avoidance-Using-PRM-Motion-Planner.html

**Modelos de costo (para el campo correspondiente):**

| Producto | Modelo | Costo |
|---|---|---|
| RapidPlan | Licencia empresarial | Bajo cotización, no publicado |
| cuMotion | SDK gratuito | Cero en software; requiere GPU NVIDIA RTX dedicada |
| RoboDK | Licencia perpetua o suscripción | Educativa USD 145/año; profesional según robodk.com/pricing |
| Propuesta | Código abierto | Cero en software; estación de trabajo convencional |

---

### 17. Aporte a nivel de producto

El aporte del presente proyecto a nivel de producto consiste en el desarrollo de un sistema de planificación de movimiento reactivo basado en una política de control continuo aprendida por refuerzo profundo, capaz de generar trayectorias libres de colisión para un manipulador de 6 GDL ante configuraciones de obstáculos variables, sin reprogramación punto a punto y ejecutable sobre una unidad de procesamiento convencional mediante software íntegramente de código abierto.

En comparación con RapidPlan, la propuesta persigue el mismo objetivo funcional (mantener la validez de las trayectorias ante cambios del entorno), pero sustituye la descomposición volumétrica determinista acelerada por hardware propietario por una política aprendida cuyo costo computacional se amortiza durante el entrenamiento, eliminando tanto la dependencia de hardware especializado como la del subsistema de percepción comercializado por separado. Frente a cuMotion, el proyecto renuncia a la optimización numérica en línea a cambio de inferencia de latencia determinista sobre CPU, eliminando el requisito de una GPU dedicada a bordo que constituye la principal barrera de infraestructura para la micro y pequeña empresa nacional. Y respecto a RoboDK, que representa la práctica actualmente accesible, la propuesta incorpora adaptación en tiempo de ejecución en lugar de cálculo estático a priori, evitando que cada cambio de utillaje obligue a rehacer la planificación y reexportar el programa.

Adicionalmente, y a diferencia de las tres soluciones comerciales, el proyecto cuantifica y publica explícitamente el compromiso entre calidad de trayectoria, tiempo de respuesta y retención de desempeño ante configuraciones geométricas no observadas durante el entrenamiento. Ninguno de los productos revisados documenta esa caracterización, de modo que el aporte no se limita a una alternativa de menor costo de despliegue, sino a un criterio verificable de decisión sobre cuándo una política aprendida resulta preferible a la replanificación clásica y cuándo no.

---

### 18. Patentes

#### Patente 1 — US 11,813,753 B2 (FANUC Corporation, Japón)

*Collision avoidance motion planning method for industrial robot.* Inventores: Changhao Wang, Hsien-Chung Lin y Tetsuaki Kato. Concedida y activa.

Técnica de planificación de movimiento con evitación de colisiones basada en búsqueda del peor estado y optimización. A partir de la definición geométrica de los obstáculos, los puntos de inicio y meta y un conjunto inicial de puntos de paso, localiza entre cada par adyacente la ubicación con la peor distancia al obstáculo considerando todas las partes del robot y la herramienta, y optimiza las posiciones de los puntos de paso hasta eliminar toda colisión y satisfacer un criterio de distancia mínima. Resuelve así el compromiso entre densidad de puntos de paso, tiempo de cómputo y suavidad del movimiento.

Sin embargo, no emplea inteligencia artificial ni aprendizaje: es cálculo geométrico y optimización numérica sobre una trayectoria calculada fuera de línea, sin generación reactiva de consignas en lazo cerrado, y presupone conocimiento geométrico exacto y estático de los obstáculos al momento de planificar.

https://patents.google.com/patent/US11813753B2/en

---

#### Patente 2 — US 12,240,113 B2 (Google LLC, Estados Unidos)

*Deep reinforcement learning for robotic manipulation.* Inventores: Sergey Levine, Ethan Holly, Shixiang Gu y Timothy Lillicrap. Prioridad de 2016, con cadena de continuaciones concedidas hasta 2025.

Patente fundacional en aprendizaje por refuerzo profundo continuo aplicado a manipulación robótica. Protege métodos de entrenamiento distribuido con actualizaciones asíncronas fuera de política, en los que múltiples robots físicos operando en paralelo comparten un búfer de repetición centralizado para optimizar una red neuronal unificada, atacando la lentitud del aprendizaje cuando se requiere interacción continua sobre hardware real.

Sin embargo, su alcance cubre la arquitectura de recolección distribuida de experiencia mediante una flota de robots físicos, no la formulación de un proceso de decisión de Markov para evitación de obstáculos ni el uso de algoritmos actor-crítico en simulación individual, y presupone una infraestructura de cómputo centralizado inexistente en una investigación académica individual.

https://patents.google.com/patent/US12240113B2/en
Registro alterno verificado: https://patentsgazette.uspto.gov/week09/OG/html/1532-1/US12240113-20250304.html

---

### 19. Aporte del trabajo

El aporte general del presente proyecto consiste en integrar los conocimientos y referencias obtenidos de los antecedentes relacionados con la planificación de movimiento, el aprendizaje por refuerzo profundo aplicado a manipuladores, la representación geométrica de obstáculos y los planificadores clásicos basados en muestreo. Los papers aportan fundamentos sobre la formulación del problema como proceso de decisión de Markov, el diseño de funciones de recompensa multiobjetivo y los protocolos de comparación equitativa frente a los planificadores de OMPL; las tesis proporcionan experiencias de entrenamiento de políticas de control continuo en entornos simulados y criterios de validación frente a métodos convencionales; mientras que los productos comerciales evidencian la demanda industrial real de planificación adaptativa ante celdas reconfigurables y las limitaciones de las soluciones existentes, basadas en hardware propietario o en cálculo estático fuera de línea.

A partir de estos aportes, el proyecto plantea el desarrollo y evaluación de un sistema de planificación de movimiento basado en una política de aprendizaje por refuerzo entrenada desde cero, que controla los incrementos articulares de un manipulador de 6 grados de libertad a partir de descriptores geométricos de distancia mínima, destinado a la evitación de obstáculos ante múltiples configuraciones del espacio de trabajo en celdas de manufactura. Asimismo, los antecedentes proporcionan criterios para la selección del algoritmo, la representación del estado y la estrategia de recompensa, así como para la evaluación experimental del desempeño mediante la tasa de éxito, el número de colisiones, la longitud de trayectoria, el tiempo de ejecución y la distancia mínima a los obstáculos. De esta manera, el proyecto articula los aportes de los antecedentes en una propuesta orientada a determinar bajo qué régimen de variabilidad geométrica una política aprendida conserva desempeño suficiente para operar sin reprogramación, contrastada estadísticamente frente a los planificadores clásicos RRT-Connect y RRT*.

---

### 20. Mapa de vacíos (síntesis visual para diapositiva)

| Fuente | 6 GDL | RL aislado | Obstáculos | vs. clásicos | Generalización |
|---|:---:|:---:|:---:|:---:|:---:|
| Paper 1 — Mao et al. | ✔ | ✔ | ✔ | ✘ | ✘ |
| Paper 2 — Fu & Tang | ✔ | ✘ | ✔ | parcial | ✘ |
| Paper 3 — Xia et al. | ✔ | ✔ | ✔ | ✘ | ✘ |
| Paper 4 — Fidalgo et al. | ✔ | ✔ | ✘ | ✔ | ✘ |
| Paper 5 — Jurgenson & Tamar | ✘ | ✔ | ✔ | ✘ | ✔ |
| Tesis 1 — Liu | ✔ | ✘ | ✔ | ✘ | ✘ |
| Tesis 2 — Sanches | ✔ | ✔ | ✔ | ✘ | ✘ |
| Tesis 3 — Fidalgo | ✔ | ✔ | parcial | ✔ | parcial |
| **Proyecto propuesto** | **✔** | **✔** | **✔** | **✔** | **✔** |

> **Advertencia:** esta tabla se construyó a partir de resúmenes y secciones de metodología. Debe completarse tras leer los textos completos. Un error en una celda que el evaluador conozca invalida toda la tabla. La fila de la Tesis 3 es la más próxima y la que requiere verificación más cuidadosa.

---

## PARTE V — DEFENSA

### 21. Argumento sobre el contexto peruano

**La versión débil, que no debe usarse como argumento principal:** «nadie lo ha hecho en Perú». Es geografía, no aporte científico, y un evaluador exigente responderá que la física del UR5 es la misma en Lima que en Múnich.

**La versión fuerte, en este orden:**

1. **El aporte técnico, independiente de la geografía.** La intersección documentada: benchmark RL vs OMPL con obstáculos y con medición de generalización. Está abierta a nivel mundial.
2. **La pertinencia del criterio.** El resultado es un umbral de variabilidad geométrica tolerable. Ese criterio vale más donde la variedad de producto es alta y el presupuesto de integración bajo.
3. **La formación de capacidad.** Antecedente nacional. Argumento más débil, va al final y nunca solo.

### 22. Preguntas probables con respuesta

**«¿En qué se diferencia de lo ya publicado?»**
Los trabajos que evalúan RL con obstáculos no lo contrastan contra planificadores clásicos en condiciones equivalentes. El único banco de pruebas riguroso frente a OMPL se realiza sin obstáculos en la escena: su vector de observación no contiene ninguna variable que describa el entorno, solo un indicador binario de autocolisión y colisión con el piso. Sus propios autores reconocen que la adaptabilidad *zero-shot* sigue siendo ventaja de los métodos clásicos.

**«¿No es simplemente aplicar SAC?»**
SAC es de 2018 y no se pretende aportar nada al algoritmo. El aporte reside en la pregunta experimental que se responde con él y en el protocolo que la hace verificable.

**«¿Qué hiciste tú, si el robot, el simulador y la librería ya existen?»**
No se construye el instrumento, se diseña la medición. El aporte es la formulación del MDP, la función de recompensa, la matriz de perturbación geométrica y el protocolo de comparación equitativa. Que las herramientas sean estándar hace los resultados reproducibles y comparables.

**«Dos de tus fuentes son del mismo autor.»**
Declarado explícitamente. Se citan ambos porque el paper documenta el protocolo experimental con mayor detalle que la tesis, y reconocer al competidor más directo con precisión es parte de un estado del arte serio.

**«¿Por qué RL si RRT\* ya funciona?»**
No se sostiene que sea mejor. RRT* es asintóticamente óptimo y produce mejores trayectorias con tiempo suficiente. La hipótesis es sobre el compromiso: la política responde por inferencia con latencia determinista, el planificador clásico replanifica desde cero con tiempo variable. Se mide cuánta calidad cuesta esa ventaja y bajo qué variabilidad deja de compensar.

**«Si RRT\* da mejores trayectorias, tu método es peor.»**
Es una elección de diseño dependiente del requisito. En celda estática con holgura de cómputo, RRT* es la respuesta correcta, y así se consignará en las conclusiones. La contribución es determinar el punto de cruce.

**«¿Por qué no aprender todo de extremo a extremo?»**
Aprender lo que ya está resuelto es mala ingeniería. Los planificadores clásicos ofrecen garantías de completitud probabilística y comportamiento predecible. El aprendizaje se reserva para el nivel donde el enfoque analítico presenta limitaciones concretas.

**«¿Por qué SAC y no PPO o TD3?»**
Por eficiencia de muestreo: SAC es fuera de política y reutiliza experiencia, mientras PPO la descarta tras cada actualización. Frente a TD3, SAC presenta menor sensibilidad a hiperparámetros por el ajuste automático del coeficiente de entropía. Se contempla una subprueba con PPO bajo la misma recompensa como contraste.

**«Asumes percepción perfecta. Eso no existe.»**
Está declarado como supuesto. Los resultados constituyen una cota superior. El supuesto se aplica por igual a la política y a la línea base, de modo que la comparación permanece válida. La degradación ante error de percepción se declara como trabajo futuro.

**«¿Por qué solo simulación?»**
El objeto de estudio es la política de control, no la transferencia a hardware. Un manipulador físico introduciría holguras, deflexión y errores de calibración que enmascararían el efecto a medir.

**«¿Esto es mecatrónica o informática?»**
Integra al menos tres áreas de la especialidad: control, informática e inteligencia artificial. El modelado cinemático, el cálculo analítico de distancias mínimas entre eslabones y obstáculos, y el análisis de límites articulares y de velocidad son componentes mecatrónicos centrales.

**«¿Cómo sabes que no memorizó los escenarios de entrenamiento?»**
Es lo que se mide. La política congelada se evalúa sobre configuraciones fuera de distribución y se reporta la razón entre su tasa de éxito allí y la nominal. Si cae por debajo de un valor útil, el método no sirve para alta variedad, y ese resultado también responde la pregunta.

**«¿Y si el agente no converge?»**
Riesgo identificado. La línea base clásica se implementa primero y funciona desde las primeras semanas, constituyendo a la vez el punto de comparación y el resultado de respaldo. Si la política no converge en los escenarios restrictivos, el resultado es la caracterización de dónde falla.

**«¿Cuál es el producto final tangible?»**
Demostración en vivo del sistema sobre el entorno simulado, con la política ejecutándose en tiempo real frente a configuraciones de obstáculos propuestas durante la sustentación, más el tablero de métricas comparativas.

**«Esto ya existe comercialmente.»**
Existe, resuelto por otra vía: hardware propietario o GPU dedicada. Ninguno usa políticas aprendidas ni es accesible para una MYPE. La pregunta no es si es posible evitar obstáculos, sino qué se pierde al hacerlo mediante una política aprendida ejecutable sobre CPU convencional.

---

## PARTE VI — CONTEXTO PERUANO Y PENDIENTES

### 23. Cómo se maneja hoy el problema en el Perú

No existe mercado de programación robótica interna. Las empresas que automatizan contratan **integradores**, que diseñan, montan y programan la celda completa.

Integradores identificados con operación en Perú:

- **MECANOS AUTOMATION** — integrador de Yaskawa, ABB, FANUC, Turin y JAKA para Perú y la región; representante de SprutCAM, software CAD/CAM/OLP para robots y CNC. *Confirma que la práctica real es programación fuera de línea, exactamente el método que el proyecto cuestiona.*
- **NFM Robotics** — empresa peruana que ofrece soluciones de soldadura «sin necesidad de programadores especializados», dirigida a empresas con procesos establecidos que buscan automatizar tareas repetitivas. *Ese argumento de venta es evidencia directa de que la barrera de programación es un problema reconocido en el mercado local.*
- **Konetia** (España) — declara proyectos de robótica industrial en Perú, entre otros países.

**El ciclo actual:** la empresa contrata al integrador, este monta y programa las trayectorias punto a punto o mediante software fuera de línea, y entrega. Si después cambia el utillaje o la pieza, el taller debe volver a contratar al integrador o mantener un técnico capacitado en el teach pendant. Para lotes pequeños ninguna opción se amortiza, y por eso la mayoría no automatiza.

**Lo que NO está documentado públicamente:** cuántos robots industriales operan en Perú, cuánto cobra un integrador local por reprogramar una celda, cuántas horas toma un cambio de lote.

### 24. Acción recomendada de mayor impacto

Entrevistar a un integrador local (MECANOS AUTOMATION o NFM Robotics), presentándose como estudiante de tesis de la UNI. Preguntas concretas: cuánto demora reprogramar una celda tras un cambio de producto, cuánto cuesta el servicio, y por qué sus clientes no automatizan más.

Rendimiento esperado: datos primarios citables para la realidad problemática (su punto más débil), un antecedente nacional real en lugar de inferencias, y potencialmente el cliente del Artículo 14.

### 25. Cifras de contexto disponibles (requieren fuente primaria)

Datos obtenidos de fragmentos de búsqueda, **pendientes de verificación en fuente primaria** antes de citarse:

- Sector metalmecánico peruano: más de 350 000 empleos, 74 000 empresas, más del 9 % del PBI manufacturero, más de 40 industrias abasteciendo a minería, construcción y transportes → *Estudio de Investigación del Sector Metalmecánico 2024*, PRODUCE (gob.pe/produce).
- MIPYME: 99.5 % de las empresas formales del país, de las cuales 95.6 % son microempresas → estadísticas MIPYME de PRODUCE.
- Densidad robótica mundial: 162 unidades por cada 10 000 trabajadores en 2023, más del doble que en 2016; Corea del Sur 1 012; Brasil por debajo de 50 → *World Robotics*, IFR (ifr.org); comunicados de prensa anuales son gratuitos.

### 26. Lista de pendientes

**Bloqueantes — confirmar con el profesor:**
- Completar nombre y código del segundo integrante en el encabezado de este documento y en el formato Excel del curso.
- Confirmar con el profesor la reformulación del entregable electrónico E2 como arquitectura de sensado y comunicaciones.
- Confirmar que el diseño de celda CAD satisface el entregable de diseño mecánico.
- Confirmar que la demo de software satisface el requisito de producto tangible.
- Confirmar que el recorte de alcance experimental de la sección 11 es aceptable.
- Confirmar el efecto del cambio a equipo de dos personas sobre el Artículo 14 y los criterios de evaluación.
- **Aclarar en qué máquina está la GPU NVIDIA.** En el equipo de trabajo actual `nvidia-smi` no logra comunicarse con el driver; si el entrenamiento corre en CPU, la Compuerta 1 de la semana 4 gana importancia.

**Críticos:**
1. Eliminar de todas las URLs cualquier parámetro de seguimiento (se detectó `utm_source=chatgpt.com` en el enlace de la Tesis 2).
2. Corregir el área de desarrollo: quitar «Cobots».
3. Incorporar datos cuantitativos con fuente a la realidad problemática.
4. Abrir el PDF de la Tesis 2 y confirmar los grados de libertad del manipulador (la descripción actual admite que no se verificó).
5. Reformular cualquier hipótesis con umbral numérico a formulación direccional.

**Importantes:**
6. Descargar el Paper 4 (PDF libre; el portal de MDPI bloquea la descarga automatizada, hay que bajarlo a mano) y confirmar personalmente el vector de observación de 14 valores sin representación de obstáculos, en la sección 3.2.2. Es el pilar del argumento de aporte y no debe citarse de segunda mano.
7. ~~Confirmar en documentación oficial de RoboDK el uso de OMPL.~~ **Resuelto (2026-09-19):** RoboDK **no** usa OMPL, sino un PRM propio. Corregida la sección 16 y reemplazada la URL raíz.
8. ~~Confirmar accesibilidad del PDF de la Tesis 3 y verificar autor, año y directores.~~ **Resuelto (2026-09-19):** verificado y descargado; ver `estado-del-arte/README.md`.
9. Declarar el supuesto de percepción ideal en algún campo visible del formato de entrega (hoy no aparece).
10. Diferenciar mejor «Aporte a nivel de producto» de «Aporte del trabajo»: el primero debe hablar solo del artefacto frente a los tres productos comerciales; el segundo integrar papers, tesis y productos.
11. Confirmar con el profesor que una demostración de software satisface el requisito de producto tangible del curso.

**Documentos de planificación asociados:**
- `EDT.md` — EDT adoptada, con paquetes de trabajo, cronograma de 15 semanas y compuertas de decisión.
- `semana-03/nota-tecnica-entorno.md` — verificación del entorno y hallazgos técnicos.
- `semana-04/3.1-contrato-escenarios-y-metricas.md` — contrato de escenarios y definición de las 5 métricas.
- `semana-04/3.9-configuracion-ompl.md` — configuración de OMPL, verificación y pendientes P1-P6.
- `semana-04/3.1-propuesta-contrato-v1.1.md` — corrección del contrato de escenarios, aplicada como v1.1; 9 de 19 variantes aún infactibles (v1.2 pendiente).
- `estado-del-arte/` — las 13 referencias verificadas: BibTeX, lista IEEE, índice con discrepancias y PDFs de acceso abierto.

**Verificaciones ya realizadas (no repetir):**
- Papers 1, 2, 3, 4 y 5: existen, DOI correctos.
- Paper 3: el DOI correcto es el de *Manufacturing Letters* (10.1016/j.mfglet.2024.09.151). Cualquier versión que lo atribuya a *Journal of Manufacturing Systems* es errónea.
- Paper 1: la revista es *Experimental Technology and Management* (实验技术与管理), vol. 42, n.º 4, pp. 78–85, 2025, verificado en el propio PDF. No es *Complex System Modeling and Simulation*.
- Tesis 1 y 2: existen, con PDF de acceso libre.
- Patente 1: primer inventor es Changhao Wang.
- Patente 2: usar el número concedido US 12,240,113 B2; inventores Levine, Holly, Gu y Lillicrap.
