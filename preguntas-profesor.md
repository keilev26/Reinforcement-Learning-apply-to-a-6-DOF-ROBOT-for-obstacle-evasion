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

## 2. Entregable electrónico: diseño de la electrónica de control *(el más importante)*

El curso estructura la entrega en cuatro componentes: **electrónico, software/control, diseño mecánico e implementación**. El proyecto se valida íntegramente en simulación, por lo que el entregable electrónico se plantea como **diseño**, no como montaje.

**Encuadre.** El proyecto trata sobre un manipulador de 6 GDL, no sobre un modelo comercial concreto. Se adopta la **mecánica del UR5e como plataforma de referencia** —geometría, parámetros de Denavit-Hartenberg, envolvente de trabajo y límites articulares— y sobre esa mecánica se **diseña una electrónica de control propia**.

**Propuesta:** el entregable electrónico consistiría en el diseño completo de esa electrónica:

- **Dimensionamiento de actuadores** para reproducir la envolvente del manipulador de referencia: 150 N·m en hombro y codo, 28 N·m en muñeca, velocidad máxima de π rad/s.
- Selección de reductores y transmisión, con la relación de reducción por articulación.
- Etapa de potencia: drivers de motor, fuente de alimentación y protecciones.
- **Unidad de cómputo y microcontrolador**, dimensionados para ejecutar la inferencia de la política de control aprendida dentro del período de control.
- Sensado: encoders por articulación, e instrumentación que produciría el vector de observación del sistema (LiDAR 3D, cámaras de profundidad, escáner de seguridad).
- Arquitectura de comunicación: bus entre articulaciones y con el controlador de celda.
- Cadena de seguridad: paro de emergencia, enclavamientos y categoría de seguridad.
- Presupuesto de latencia del lazo: sensado + inferencia + actuación, contrastado con el período de control.

**Justificación del rigor.** El dimensionamiento de los actuadores no se haría por catálogo: se obtendría por **dinámica inversa sobre las trayectorias que el propio proyecto genera**, extrayendo el par realmente demandado por articulación durante la ejecución de las trayectorias del entrenamiento y de la línea base.

**Pregunta:** ¿satisface esto el entregable electrónico del curso, entendido como diseño y no como implementación en hardware?

---

## 3. Diseño de celda como entregable de diseño mecánico

**Propuesta:** el entregable mecánico consistiría en el diseño CAD de una **celda de manufactura flexible para abastecimiento de máquina (*machine tending*) de un centro CNC**, que incluye:

- Layout de la celda base: pedestal del robot, centro CNC, mesa de piezas y envolvente de seguridad.
- **Biblioteca modular de componentes**, cada uno modelado y exportable por separado: máquina, mesa, utillaje, prensa, carro de transporte, pieza en tránsito y obstáculos primitivos. Los ocho escenarios experimentales se **componen** a partir de esta biblioteca, en lugar de modelarse por separado.
- Modelado del manipulador de 6 GDL: parámetros de Denavit-Hartenberg, cinemática directa e inversa, límites articulares y de velocidad.
- Análisis de alcanzabilidad: verificación de que las poses de recogida y depósito caen dentro de la envolvente de trabajo del manipulador.
- Análisis de singularidades de muñeca, que fundamenta la elección del espacio de acción del controlador.

**Punto a destacar:** el diseño mecánico no sería un anexo documental. La biblioteca diseñada en CAD se exporta a formato de simulación y **es** la geometría con la que se construyen todas las escenas donde se ejecutan los experimentos. El diseño es la entrada geométrica del experimento, y su única fuente.

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
