# Propuesta de migración del proyecto al DOBOT Magician E6

**Fecha:** 2026-09-22 · **Rama:** `feature/magician-e6-evaluacion`
**Antecedente:** `evaluacion-magician-e6.md` (el E6 es viable: modelo oficial, PyBullet y MoveIt
verificados, `ServoJ` a 33 Hz para el robot real).
**Estado:** **APROBADA el 2026-09-22 con una modificación** (Caleb Camargo). Aplicada a `EDT.md`,
al documento de contexto, al `README.md` y al cronograma. Pendiente la revisión cruzada de
Leonardo Vásquez.

> **Modificación al aprobar: el robot real queda fuera de las 15 semanas.** El alcance obligatorio
> es el algoritmo de RL y su evaluación en simulación. Todo lo que exige el E6 físico —la
> caracterización de `ServoJ`, la aleatorización para la transferencia (1.3), la capa de seguridad
> (1.4), la validación en el robot (1.5), la maqueta física y la compuerta 3— pasa a **trabajo
> adicional** (`EDT.md`, sección 10). En consecuencia:
>
> - Se mantienen D1-D5: el MDP usa el período y los límites del E6 para que la política **pueda**
>   ejecutarse en él sin reentrenar.
> - **D6 no se aplica**: eliminar PPO solo servía para liberar la semana del robot real. La
>   subprueba 3.15 sigue como extensión.
> - El E2 no mide sobre el robot: **diseña su integración** (arquitectura, latencia, seguridad) con
>   la documentación del fabricante, y hace el análisis dinámico con el modelo.
> - El cronograma apenas cambia: las secciones 4.2, 4.5 y 4.6 de abajo quedan **sustituidas** por lo
>   aplicado en `EDT.md`. El resto del documento se conserva como registro de la propuesta.

---

## 0. Qué cambia y qué no

La pregunta de investigación, SAC, la acción Δq, la observación por distancias mínimas, las
5 métricas, la línea base y la arquitectura *PyBullet entrena / ROS 2 evalúa* **se mantienen**.
Cambian cuatro cosas de fondo:

| Antes | Después |
|---|---|
| UR5e simulado, sin hardware | **Magician E6 simulado y real** |
| Alcance 0.85 m, celda industrial a escala real | Alcance 0.45 m, **celda de escritorio a escala ~1:2** |
| "Excluye despliegue físico y sim-to-real" | **Incluye validación en el robot real** como demostración de transferencia, no como pregunta de investigación |
| E2 diseña la electrónica de un robot hipotético | **E2 integra y caracteriza el robot que existe** |

### Decisiones que la propuesta necesita del equipo

| # | Decisión | Recomendación |
|---|---|---|
| D1 | Robot único E6 (se abandona el UR5e) | **Sí.** Una política no se transfiere entre robots, y dos robots no caben en 10 semanas |
| D2 | Período de control | **30 ms** (33 Hz), el que recomienda Dobot para `ServoJ` |
| D3 | Transición del simulador | **Cinemática** (sección 1.2.3) |
| D4 | Tolerancia de éxito M1 | **5 mm** y 0.05 rad (hoy 10 mm) |
| D5 | Presupuesto del episodio | **300 pasos = 9 s** (hoy 500) |
| D6 | Subprueba PPO (3.15) | **Eliminarla** para liberar la semana que exige el robot real |

---

## 1. Aprendizaje por refuerzo — lo más importante

### 1.1 Qué NO cambia

- **SAC desde cero**, sin demostraciones.
- **Acción Δq** (incrementos articulares acotados). El E6 lo favorece: `ServoJ` recibe exactamente
  posiciones articulares.
- **Observación por descriptores geométricos** de distancia mínima, sin visión.
- **Percepción ideal** como supuesto declarado, para ambos métodos.
- Las 5 métricas, el protocolo estadístico y los 8 escenarios (redimensionados, sección 3).

### 1.2 Cambios al MDP

#### 1.2.1 Período de control: Δt = 30 ms

Hoy el MDP no fija Δt. Con el robot real deja de ser libre: `ServoJ` está diseñado para llamarse
cada **30 ms** (manual de Dobot, V4). El simulador debe usar **el mismo** Δt; si no, la política
aprende una dinámica que el robot no reproduce.

#### 1.2.2 Acción: Δq_max = 0.05 rad por paso

| | Valor |
|---|---|
| Salida de la red | a ∈ [−1, 1]⁶ |
| Acción aplicada | Δq = a · Δq_max, recortada a los límites articulares |
| Límite físico | v_max · Δt = 2.0944 rad/s × 0.030 s = 0.063 rad |
| **Δq_max propuesto** | **0.05 rad** (80 % del límite) |

El 20 % de margen es para que el controlador del E6 **alcance** cada objetivo dentro de su paso: si
se pide más de lo que puede recorrer en 30 ms, `ServoJ` se retrasa y la política en el robot real
deja de ver lo que veía en simulación. Hay que confirmar también que no se supera la velocidad de
TCP de 0.5 m/s (a 0.5 m del eje, 0.05 rad en 30 ms son 0.83 m/s). **Se mide en la caracterización
del robot (paquete 2.1).**

#### 1.2.3 Transición: cinemática, no dinámica

Propuesta: q_{t+1} = clip(q_t + Δq), colocada con `resetJointState`, sin simular pares.

- El E6 real **se controla por posición** (su propio controlador sigue a `ServoJ`); la política
  nunca comanda pares.
- Las masas del modelo son **estimaciones** (ver 2.1). Una transición dinámica haría que la
  política dependiera de ellas.
- La diferencia entre la transición cinemática y el robot real es el **retardo y el error de
  seguimiento** de `ServoJ`, que se miden (2.1) y se introducen como aleatorización (1.3).

#### 1.2.4 Colisiones entre pasos: subpasos de ≤ 0.02 rad

Con 0.05 rad por paso, un eslabón a 0.5 m del eje recorre 25 mm: puede **atravesar** un obstáculo
delgado sin que ningún estado muestreado choque. Es exactamente el defecto que se encontró en la
línea base (paquete 3.9, causa A). Por paridad, **cada paso se revisa en 3 subpasos** (≤ 0.017 rad),
con el mismo criterio de 0.02 rad que ya usa la validación independiente de la línea base.

#### 1.2.5 Observación: solo lo que el robot real puede calcular

Regla nueva: **nada entra a la observación si el robot real no puede producirlo**. Propuesta:

| Componente | Dim. | En el robot real sale de |
|---|---|---|
| q normalizado a [−1, 1] | 6 | Puerto 30004 (cada 8 ms) |
| Δq de la acción anterior | 6 | La propia política |
| Error de posición del TCP a la meta | 3 | Cinemática directa del URDF + meta |
| Error de orientación (cuaternión) | 4 | Ídem |
| Distancia mínima por eslabón al obstáculo más cercano | 6 | Cinemática directa + poses **medidas** de los obstáculos (supuesto de percepción) |
| Vector unitario de esa distancia, por eslabón | 18 | Ídem |
| **Total** | **43** | |

Se descartan las velocidades articulares leídas del simulador: en el robot llegan con ruido y
retardo. Si se necesita velocidad, la da Δq anterior / Δt.

> El Paper 4 usa 14 valores sin ninguna variable de obstáculo. Las 24 dimensiones de distancia y
> dirección son exactamente lo que el proyecto agrega.

#### 1.2.6 Recompensa: normalizada por la escala de la tarea

Todo término con longitudes (umbral de seguridad, bonificación por cercanía a la meta) se expresa
como **fracción de una longitud característica L**, la distancia `p_pick → p_place` del contrato.
Así la recompensa no depende de la escala de la celda, y lo que se ajuste ahora sigue sirviendo si
cambia la geometría.

| Término | UR5e (implícito) | E6 propuesto |
|---|---|---|
| Umbral de seguridad d_seg | ~5 cm | **2 cm** (≈ 0.07 L) |
| Tolerancia de éxito (M1) | 10 mm | **5 mm**: 1.5 % de la tarea, como antes |
| Mesa como obstáculo | Implícito | **Explícito**: el robot está sobre la mesa y M2 cuenta eslabón–mesa |

#### 1.2.7 Episodio: 300 pasos (9 s)

La tarea del E6 mide ~0.3 m. A una velocidad típica de 0.1 m/s son 3 s = 100 pasos. 300 pasos dejan
margen triple para rodear obstáculos. 500 pasos (15 s) solo alargarían los episodios fallidos.

### 1.3 Nuevo: aleatorización para la transferencia al robot real

Es **distinta** de la aleatorización geométrica que responde la pregunta de investigación (pose,
escala, forma), y se mantiene pequeña para no mezclarse con ella:

| Perturbación | Rango inicial | Se ajusta con |
|---|---|---|
| Retardo de actuación | 0-1 pasos (0-30 ms) | Medición de `ServoJ` (2.1) |
| Fracción alcanzada de cada Δq | 0.85-1.0 | Ídem |
| Ruido en q observado | ±0.001 rad | Repetibilidad ±0.1 mm |
| Error en la pose medida del obstáculo | ±5 mm | Precisión de la plantilla de colocación (1.8) |

Se entrena y evalúa en simulación **con** esta aleatorización para ambos métodos, y se reporta.

### 1.4 Nuevo: capa de seguridad en el despliegue

En el robot real, antes de enviar cada `ServoJ`, un filtro comprueba el estado siguiente: dentro de
límites, sin autocolisión y con distancia a los obstáculos medidos > 1 cm. Si falla, **detiene el
robot**. Además se activa la detección de colisiones del propio E6.

**Toda intervención del filtro cuenta como fallo del episodio** y se reporta aparte. El filtro
protege el robot, no mejora los números.

### 1.5 Nuevo: protocolo de validación en el robot real

| | Propuesta |
|---|---|
| Escenarios | 1, 2, 4 (dos poses), 6 (prisma y cilindro), 8 |
| Episodios | 10 por escenario y método |
| Métodos | Política SAC y RRT-Connect, ambos ejecutados con `ServoJ` |
| Métricas | Las 5, desde el registro de q a 8 ms: éxito (pose final contra la meta), colisiones (filtro o detección del robot), longitud, tiempo y d_min (cinemática directa + poses medidas) |
| Alcance de la conclusión | **Demostración de transferencia**. Con 10 episodios no se hace inferencia estadística: la comparación formal sigue siendo la de simulación |

### 1.6 Riesgos del RL con el E6

| Riesgo | Contingencia |
|---|---|
| La política no transfiere (el retardo real es mayor que el simulado) | Ampliar la aleatorización 1.3 con los datos medidos. Compuerta 3 |
| La celda pequeña deja pasos estrechos en relación con el tamaño de los eslabones | La geometría de colisión es conservadora (≤ 17 mm de exceso p95). Verificar el contrato v2.0 con la herramienta de 3.1 antes de entrenar |
| Poco acceso al robot | Llevar el puente de despliegue listo desde la semana 9 y probar primero con trayectorias de RRT-Connect |

---

## 2. Entorno

### 2.1 Modelo del robot — HECHO en esta rama

`tools/gen_modelo_e6.py` genera `ros2_ws/src/rl6gdl_e6_description/` desde el URDF oficial (commit
fijado), con: masas escaladas a 7.2 kg, velocidad de 2.0944 rad/s, par estimado por dinámica
inversa, mallas visuales reducidas, **colisiones convexas idénticas para PyBullet y FCL**, raíz en
la mesa, `tool0` y la matriz de colisiones permitidas. La cinemática se verifica idéntica a la
oficial (error de 3e-8 m). Detalle y números en el `README.md` del paquete.

`gym_env/robot_e6.py` lo carga en PyBullet y aplica la matriz de colisiones; 9 pruebas en
`gym_env/tests/`. Rendimiento: ~12 000 pasos/s cinemáticos con consulta de distancia.

### 2.2 Pendiente en ROS 2

| Tarea | Detalle |
|---|---|
| Configuración de MoveIt propia | Grupo `manipulador` de `base_link` a `tool0`, sobre `rl6gdl_e6_description`. SRDF con la matriz de `colisiones_permitidas.yaml`, no la oficial |
| Formato Jazzy | Ya diagnosticado: `planning_plugins` como lista y adaptadores separados |
| OMPL (3.9) | Portar `rl6gdl_planning`: grupo, y `longest_valid_segment_fraction` = **0.00067** para conservar 0.014 rad (el espacio del E6 mide 20.8 rad; el del UR5e, 28.8) |
| Volver a medir 3.9 | Las conclusiones (RRT\* inviable, LazyPRM\* 10/10) eran del UR5e: **hay que repetirlas** |
| Gazebo Harmonic | `gz_ros2_control/GazeboSimSystem` en un xacro aparte que incluya el URDF |
| Scripts | `diagnostico_pendientes.py`, `p6_contrato.py` y los demás tienen `ur_manipulator` escrito |

### 2.3 Nuevo: despliegue en el robot real

- Nodo puente política → `ServoJ` a 33 Hz, con la capa de seguridad 1.4. Punto de partida: el
  driver Jazzy de WChamorro (ya hace streaming con `ServoJ`) o el SDK oficial `TCP-IP-Python-V4`.
- Requisito del controlador: firmware **≥ V4.4.0.0**.
- Registro de q a 8 ms (puerto 30004) para calcular las métricas.

### 2.4 Compuerta 1 ampliada: tres modelos equivalentes

PyBullet ↔ Gazebo (como antes) y ahora **simulación ↔ robot real**: cinemática directa contra
`GetPose()` en ≥ 5 posturas, con error < 1 mm. Así se verifica también el marco `tool0`, que hoy
sale de la malla.

---

## 3. Contrato de escenarios: v2.0 a escala de escritorio

La v1.1 del UR5e no se puede usar: `p_pick` y `p_place` están a ~0.55 m de la base, **fuera del
alcance del E6**. Como la v1.2 ya tenía que reubicar obstáculos (9 de 19 variantes infactibles), se
propone rehacerlo como **v2.0**:

| Elemento | v1.1 (UR5e) | v2.0 (E6), propuesta de partida |
|---|---|---|
| Escala | 1 | ~0.53 (relación de alcances 0.45 / 0.85) |
| Montaje | Pedestal de 0.75 m | **Base sobre la mesa, z = 0** |
| Tarea | Recoger de mesa, depositar en CNC | Igual, en maqueta: mesa de piezas y CNC de escritorio |
| `p_pick`, `p_place` | ~0.55 m de la base | 0.25-0.35 m, **elegidos con cinemática inversa y colisiones verificadas**, no solo por distancia |
| Prisma del escenario 2 | 0.20 × 0.20 × 0.40 m | ~0.08 × 0.08 × 0.16 m |
| Escenario 6 | 0.016 m³ los tres | Mismo volumen entre sí, a la nueva escala |
| Pieza | Sin especificar | Masa de pieza + efector ≤ 0.75 kg |
| Pinza | No modelada | **Modelarla** (observación 4 de la v1.1): el efector real existe |

Criterio de aceptación: **las 8 variantes válidas** con la prueba automática de 3.1 portada al E6,
antes de generar un solo dato. Los obstáculos se diseñan para **fabricarse** (impresión 3D o
espuma) con las mismas medidas.

---

## 4. Cambios a la EDT (`docs/EDT.md`)

### 4.1 E1 — Diseño mecánico

| ID | Cambio |
|---|---|
| 1.1 | Celda de *machine tending* **de escritorio** para el E6 |
| 1.2 | Biblioteca a escala, **diseñada para fabricarse** |
| 1.3 | La colisión del robot ya está hecha (3.16); queda la de los componentes de celda |
| 1.5 | **Rehacer** la tabla DH y la cinemática para el E6 (se derivan del URDF oficial) |
| 1.6, 1.7 | Alcance y singularidades del E6 |
| **1.8 (nuevo)** | Fabricación de la maqueta y los obstáculos, y **plantilla de colocación** con poses conocidas (sostiene el supuesto de percepción en el robot real) |

### 4.2 E2 — Electrónica: de diseñar un robot a integrar uno real

El E2 actual dimensiona actuadores para reproducir la envolvente del UR5e. Con un robot real, eso
pierde sentido. Se propone:

| ID | Antes | Después |
|---|---|---|
| 2.1 | Dimensionamiento de actuadores | **Caracterización de `ServoJ`**: retardo, error de seguimiento, velocidad de TCP. Alimenta 1.3 |
| 2.2 | Reductores | **Arquitectura de despliegue**: PC ↔ controlador por Ethernet, puertos 29999 y 30004 |
| 2.3 | Etapa de potencia | **Efector final**: ventosa o pinza, E/S digitales de la brida, presupuesto de carga útil |
| 2.4 | Unidad de cómputo | Igual en espíritu: la inferencia debe caber en 30 ms. **Se mide** |
| 2.5 | Sensado | **Pose de los obstáculos**: plantilla, medición y su error |
| 2.6 | Comunicación | Lazo de 33 Hz: *jitter* y pérdidas medidas |
| 2.7 | Seguridad | Parada de emergencia, nivel de detección de colisión del E6, capa de seguridad de software (1.4) |
| 2.8 | Presupuesto de latencia | **Medido**, no estimado: lectura de q + inferencia + `ServoJ` |

El E2 gana lo que el curso pide: mediciones reales, no una selección de catálogo.

### 4.3 E3 — Software y control

| ID | Cambio |
|---|---|
| 3.1 | Contrato **v2.0** (sección 3) y `metricas.yaml` con D4 y D5 |
| 3.2 | Entorno Gym con el E6, transición cinemática y Δt = 30 ms |
| 3.3 | MDP de la sección 1.2 |
| 3.4 | Recompensa normalizada por L |
| 3.8 | **Se reabre**: MoveIt y Gazebo Harmonic con el E6 |
| 3.9 | **Se reabre**: volver a medir OMPL con el E6 |
| 3.15 | **Se elimina** (PPO) si se aprueba D6 |
| **3.16 (nuevo)** | Modelo corregido del E6, fuente única — **hecho** |
| **3.17 (nuevo)** | Aleatorización para la transferencia (1.3) |

### 4.4 E4 — Implementación

| ID | Cambio |
|---|---|
| 4.4 | Demo en vivo **en el robot real** |
| **4.7 (nuevo)** | Puente de despliegue y capa de seguridad (1.4, 2.3) |
| **4.8 (nuevo)** | Validación en el robot real (1.5) |

### 4.5 Compuertas

| Compuerta | Semana | Cambio |
|---|---|---|
| 1 — Equivalencia | 8 | Se añade la pata simulación ↔ robot real (2.4) |
| 2 — Convergencia | 10 | Sin cambio |
| **3 — Transferencia (nueva)** | 12 | Si la política no completa los escenarios 1 y 2 en el robot a velocidad reducida: ampliar la aleatorización una vez; si sigue fallando, la demo ejecuta en el robot las trayectorias de la política generadas en simulación, y se declara como resultado |

### 4.6 Cronograma, semanas 5 a 15

| Sem | Persona A | Persona B | Hito verificable |
|---|---|---|---|
| 5 | Modelo E6 (3.16 ✓) · DH del E6 (1.5) · celda de escritorio (1.1) | MoveIt E6 en Jazzy (3.8) · OMPL (3.9) | **El E6 planifica en MoveIt y carga en PyBullet desde la misma fuente** |
| 6 | Biblioteca a escala (1.2) · contrato v2.0 (3.1) · entorno Gym (3.2) | Gazebo Harmonic (3.8) · distancia mínima (3.11) · **1.ª sesión en el robot**: `ServoJ` y `tool0` (2.1) | `env.step()` y contrato v2.0 válido |
| 7 | MDP (3.3) · alcance y singularidades (1.6, 1.7) | Distancia validada contra FCL (3.11) · generador (3.12) | Distancias validadas |
| 8 | Recompensa (3.4) | Equivalencia (3.13) · fabricación de la maqueta (1.8) | **Compuerta 1** |
| 9 | Entrenamiento escenarios 1-2 (3.5) | Puente de despliegue y seguridad (4.7) · E2 (2.2, 2.6) | **El robot real ejecuta una trayectoria de RRT-Connect por el puente** |
| 10 | Aleatorización geométrica y de transferencia (3.6, 3.17) | Línea base batch (3.14) · E2 (2.4, 2.5) | **Compuerta 2** |
| 11 | Entrenamiento, 3 semillas (3.7) | Barrido del clásico · E2 (2.7, 2.8) | Datos crudos completos |
| 12 | Escenario 8 (4.3) · **1.ª prueba de la política en el robot** (4.8) | Métricas y estadística (4.1, 4.2) | **Compuerta 3** |
| 13 | Validación en el robot (4.8) · informe (4.5) | Tablero y demo (4.4) | Resultados reales |
| 14 | Slides (4.6) · paper IEEE | Paper IEEE | Defensa lista |
| **15** | **Sustentación con el robot** | **Sustentación con el robot** | |

Lo que hace caber el robot real: se elimina PPO (3.15), el núcleo queda en 3 semillas y el trabajo
de E2 pasa a ser medición sobre el robot en lugar de dimensionamiento.

### 4.7 Gantt (`tools/gen_cronograma.py`)

- Filas nuevas: 1.8, 3.16 (marcada **R** en la semana 5), 3.17, 4.7 y 4.8.
- 3.8 y 3.9 **conservan su R** de las semanas 1-4 (se hicieron, con el UR5e) y suman una barra
  **P** en las semanas 5-6 con la etiqueta "(E6)". Mismo tratamiento para 1.5.
- Se quita 3.15 si se aprueba D6.
- Se regenera el Excel.

---

## 5. Cambios al documento de contexto y al README

| Sección | Cambio |
|---|---|
| Contexto §1, restricciones | Quitar "Sin hardware físico". La demo tangible pasa a ser el robot real |
| Contexto §4, decisiones | Robot: **DOBOT Magician E6**, con modelo oficial corregido. Se retira la adopción del UR5e como plataforma de referencia y el rediseño hipotético de su electrónica. Se añade: Δt = 30 ms, transición cinemática, capa de seguridad |
| Contexto §4.1, entregables | E2 reformulado (4.2). E4 con validación física |
| Contexto §8, DÓNDE | "Validado en simulación **y demostrado en un manipulador real de 6 GDL**, sobre una celda de *machine tending* a escala" |
| Contexto §10, alcance | Pasa de "excluye despliegue físico" a "incluye validación en robot real como demostración de transferencia; excluye la transferencia como objeto de estudio" |
| Contexto §20, mapa de vacíos | Añadir la validación en hardware al aporte: el Paper 1 valida en un UR5 físico, pero sin comparar contra OMPL; aquí se comparan ambos métodos también en el robot |
| Contexto §22, defensa | Pregunta nueva: *"¿por qué un robot de escritorio si el problema es industrial?"* → la pregunta es de variabilidad geométrica y no depende de la escala; el método solo depende del URDF |
| `README.md` | Manipulador, estructura (`rl6gdl_e6_description`), puesta en marcha y pruebas |
| `docs/semana-03`, `semana-04` | **No se tocan**: son registros fechados del trabajo con el UR5e. Se añade una nota de que el robot cambió en la semana 5 |

---

## 6. Orden de aplicación

1. Aprobar D1-D6 (sección 0).
2. EDT, contexto y README (secciones 4 y 5), en una misma PR.
3. Gantt regenerado.
4. Contrato v2.0 con su prueba de aceptación (sección 3). **Antes de escribir el entorno Gym.**
5. MoveIt y Gazebo con el E6 (2.2).
