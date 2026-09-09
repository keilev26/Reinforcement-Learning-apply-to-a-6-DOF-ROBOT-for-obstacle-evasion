# Puntos a confirmar con el profesor

**Proyecto:** Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de 6 GDL
**Curso:** Proyecto Mecatrónico · Escuela Profesional de Ingeniería Mecatrónica · FIM–UNI

> Estos cuatro puntos son **bloqueantes**: condicionan el reparto de trabajo y el cronograma de 10 semanas. Conviene resolverlos antes de la semana 1.

---

## 1. Cambio a equipo de dos personas

El proyecto se planteó inicialmente como individual y ahora se desarrollará entre dos estudiantes.

**Preguntas:**
- ¿Se requiere actualizar formalmente el registro del proyecto y el formato Excel de entrega?
- ¿El trabajo en equipo modifica el alcance mínimo esperado o los criterios de evaluación?
- ¿Cambia en algo la aplicación del **Artículo 14** (puntaje adicional por cliente formal), que se había dado por perdido bajo el supuesto de proyecto individual sin cliente?

---

## 2. Entregable electrónico en un proyecto de simulación *(el más importante)*

El curso estructura la entrega en cuatro componentes: **electrónico, software/control, diseño mecánico e implementación**. Este proyecto es íntegramente de software y simulación, sin hardware físico, por lo que el entregable electrónico no aplica en su forma habitual.

**Propuesta:** sustituirlo por el **diseño de la arquitectura de sensado y comunicaciones que haría realizable la celda**, que incluiría:

- Arquitectura de control de la celda: controlador del UR5e, PLC de celda, bus de comunicación y jerarquía de mando.
- Especificación de la instrumentación que produciría el vector de observación del sistema: LiDAR 3D, cámaras de profundidad o escáneres de seguridad que entregarían la posición, dimensiones y orientación de los obstáculos que en la simulación se leen directamente del entorno.
- Presupuesto de latencia del lazo de control: tiempo de sensado + inferencia de la política + ejecución, contrastado con el período de control del manipulador.
- Cadena de seguridad: paro de emergencia, enclavamientos y categoría de seguridad.

**Justificación:** el proyecto asume percepción ideal como supuesto declarado. Este entregable convierte ese supuesto de una *limitación* en una *decisión de diseño con ruta de realización identificada*, y documenta qué instrumentación sería necesaria para llevar el sistema a una celda real.

**Pregunta:** ¿acepta esta reformulación del entregable electrónico? Si no, ¿qué alternativa sugiere para un proyecto sin hardware?

---

## 3. Diseño de celda como entregable de diseño mecánico

**Propuesta:** el entregable mecánico consistiría en el diseño CAD de una **celda de manufactura flexible para abastecimiento de máquina (*machine tending*) de un centro CNC**, que incluye:

- Layout de la celda: pedestal del robot, centro CNC, mesa de piezas, utillaje y los elementos móviles que actúan como obstáculos (prensas, carros, piezas en tránsito).
- Modelado del manipulador de 6 GDL: parámetros de Denavit-Hartenberg, cinemática directa e inversa, límites articulares y de velocidad.
- Análisis de alcanzabilidad: verificación de que las poses de recogida y depósito caen dentro de la envolvente de trabajo del manipulador.
- Análisis de singularidades de muñeca, que fundamenta la elección del espacio de acción del controlador.

**Punto a destacar:** el diseño mecánico no sería un anexo documental. La celda diseñada en CAD se exporta a formato de simulación y **es** la escena donde se ejecutan los experimentos. El diseño es la entrada geométrica del experimento.

**Pregunta:** ¿satisface esto el entregable de diseño mecánico del curso?

---

## 4. Producto tangible

El curso exige demostración tangible del producto final.

**Propuesta:** demostración en vivo durante la sustentación, con la política de control ejecutándose en tiempo real sobre el entorno simulado, enfrentando configuraciones de obstáculos propuestas por el jurado en ese momento, junto a un tablero comparativo de métricas contra los planificadores clásicos RRT-Connect y RRT\*.

**Pregunta:** ¿una demostración de software en vivo satisface el requisito de producto tangible, o se espera un artefacto físico?

---

## 5. Alcance experimental en 10 semanas

El protocolo experimental completo contempla 8 escenarios × 5 semillas aleatorias × 100 episodios de evaluación, para tres métodos (política aprendida, RRT-Connect y RRT\*). En 10 semanas no es alcanzable completo.

**Propuesta de recorte, declarado explícitamente en el informe:**

| | Escenarios | Semillas |
|---|---|---|
| **Núcleo obligatorio** | 1 (espacio libre), 2 (obstáculo único), 4 (traslación), 5 (escala), 6 (forma), 8 (fuera de distribución) | 3 |
| **Extensión si el tiempo alcanza** | 3 (tres obstáculos), 7 (paso estrecho) | 5 |

Los escenarios 4, 5 y 6 se mantienen en el núcleo porque son los ejes de variabilidad geométrica que responden directamente la pregunta de investigación; el 8 es el escenario decisivo sobre generalización.

**Pregunta:** ¿es aceptable este recorte de alcance, declarándolo como decisión de diseño experimental en el informe?

---

## 6. Consulta de cronograma

- ¿Cuáles son las fechas exactas de entrega de cada uno de los cuatro entregables?
- ¿Hay entregas parciales o revisiones intermedias programadas dentro de las 10 semanas?
