# EDT — Ruta 3: Isaac Sim / Isaac Lab

**Proyecto:** Planificación de movimiento y evasión de obstáculos mediante aprendizaje por refuerzo profundo para un manipulador industrial de **6 GDL**
**Curso:** Proyecto Mecatrónico · FIM–UNI
**Equipo:** 2 personas · **Duración:** 10 semanas
**Manipulador:** UR5e — **6 grados de libertad, no redundante** (invariante del proyecto)

> ⚠️ **Ruta de alta ambición y alto riesgo. No recomendada bajo la restricción de 10 semanas.** Se documenta completa para que la decisión sea informada y para dejarla lista como línea de trabajo futuro (tesis).

---

## 1. Resumen de la ruta

Se entrena la política en **Isaac Sim / Isaac Lab**, aprovechando simulación acelerada por GPU con miles de entornos en paralelo, y se mantiene **ROS 2 + MoveIt 2 + OMPL** para la línea base clásica, comunicados mediante el puente ROS 2 de Isaac Sim.

**Observación decisiva:** esta ruta **no elimina** el trabajo de ROS 2 — lo *añade* encima. La línea base clásica sigue necesitando MoveIt 2 y OMPL, de modo que el equipo debe dominar dos stacks completos en lugar de uno. Esa es la razón principal por la que no se recomienda en 10 semanas.

---

## 2. Stack técnico

| Capa | Herramienta |
|---|---|
| Simulador de entrenamiento | NVIDIA Isaac Sim + Isaac Lab |
| Descripción de escena | USD (Universal Scene Description) |
| Algoritmo | SAC vía RSL-RL / SKRL / Stable-Baselines3 según integración de Isaac Lab |
| Línea base | ROS 2 Jazzy + MoveIt 2 + OMPL (RRT-Connect, RRT*) |
| Puente | Isaac Sim ROS 2 Bridge |
| Modelo del robot | UR5e de 6 GDL: URDF → conversión a USD |
| CAD de celda | FreeCAD / SolidWorks → USD para Isaac, URDF/SDF para ROS 2 |

## 3. Requisitos previos — **BLOQUEANTE**

| Requisito | Estado actual | Criticidad |
|---|---|---|
| **Driver NVIDIA funcional** | ❌ **`nvidia-smi` falla en esta máquina** | **BLOQUEANTE** |
| GPU NVIDIA RTX con VRAM suficiente | Por confirmar (¿está en la máquina del compañero?) | **BLOQUEANTE** |
| Isaac Sim + Isaac Lab instalados | Faltan (descarga e instalación pesadas) | Alta |
| Ubuntu 24.04 + ROS 2 Jazzy | Instalado | — |
| MoveIt 2 + paquetes UR | Faltan | Alta |

> **Antes de considerar siquiera esta ruta hay que resolver el driver NVIDIA y confirmar en qué máquina está la GPU.** Si el entrenamiento debe correr en la máquina del compañero, el flujo de trabajo del equipo queda condicionado a la disponibilidad de esa máquina — un riesgo de coordinación adicional en un proyecto de 10 semanas.

---

## 4. Paquetes de trabajo

> **Persona B** es quien ya tiene experiencia en ROS 2. Nadie tiene experiencia previa en Isaac.

### E0 — Habilitación (paquete que solo existe en esta ruta)

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 0.1 | Resolver driver NVIDIA; confirmar GPU y VRAM disponibles | A + B | 1 |
| 0.2 | Instalar Isaac Sim e Isaac Lab; verificar ejemplo de manipulación | A | 1 |
| 0.3 | **Curva de aprendizaje: USD, Omniverse y la API de tareas de Isaac Lab** | A + B | 1-3 |
| 0.4 | Convertir el URDF del UR5e (6 GDL) a USD y validar cinemática y límites | A | 2 |

> El paquete 0.3 consume aproximadamente **2-3 semanas de las 10 disponibles**, sin producir ningún entregable del curso. Ese es el costo real de esta ruta.

### E1 — Entregable de diseño mecánico

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 1.1 | Diseño CAD de la celda de machine tending de CNC | A | 1-2 |
| 1.2 | Parámetros DH del UR5e (6 GDL); cinemática directa e inversa | A | 2 |
| 1.3 | Envolvente de trabajo y análisis de alcanzabilidad | A | 3 |
| 1.4 | Singularidades de muñeca; justificación del espacio de acción Δq | A | 3 |
| 1.5 | **Doble exportación del CAD**: a USD para Isaac y a URDF/SDF para ROS 2 | A + B | 3 |

> El paquete 1.5 es más costoso que en las otras rutas: la celda debe existir y coincidir en dos formatos de escena distintos.

### E2 — Entregable electrónico (reformulado: arquitectura de sensado y comunicaciones)

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 2.1 | Arquitectura de control de celda: controlador UR5e, PLC, bus, jerarquía de mando | A | 5 |
| 2.2 | Especificación de instrumentación que produciría el vector de observación | A | 5 |
| 2.3 | Presupuesto de latencia: sensado + inferencia + ejecución | A | 6 |
| 2.4 | Cadena de seguridad: paro de emergencia, enclavamientos, categoría | A | 6 |

### E3 — Entregable de software y control

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 3.1 | **Contrato de escenarios y definición formal de las 5 métricas** | A + B | 1 |
| 3.2 | Definición de la tarea en Isaac Lab: espacio de observación, acción Δq, terminación | A | 4 |
| 3.3 | Función de recompensa multiobjetivo | A | 4-5 |
| 3.4 | Aleatorización de dominio con el framework de Isaac Lab | A | 5-6 |
| 3.5 | Entrenamiento SAC con entornos paralelos: 3 semillas | A | 6-8 |
| 3.6 | Workspace ROS 2: MoveIt 2, `ur_simulation_gz`, UR5e | B | 2 |
| 3.7 | Configuración de OMPL: RRT-Connect y RRT* | B | 3 |
| 3.8 | `moveit_ros_benchmarks` para tiempo, longitud y éxito | B | 3-4 |
| 3.9 | **Módulo de distancia mínima eslabón-obstáculo, validado contra FCL** | B | 4-5 |
| 3.10 | Generador paramétrico de escenarios, emitiendo para USD **y** URDF/SDF | B | 5-6 |
| 3.11 | **Verificación de equivalencia Isaac ↔ Gazebo**: geometría, límites, escala, modelo de contacto | A + B | 6 |
| 3.12 | Ejecución batch de la línea base clásica | B | 7 |

### E4 — Entregable de implementación

| ID | Paquete de trabajo | Resp. | Sem |
|---|---|---|---|
| 4.1 | Cálculo de las 5 métricas para ambos métodos | A + B | 8-9 |
| 4.2 | Protocolo estadístico: medias, desviaciones, Wilcoxon | A + B | 9 |
| 4.3 | Análisis de generalización — escenario 8 | A | 9 |
| 4.4 | Tablero comparativo y demo en vivo (visualmente superior a las otras rutas) | B | 9 |
| 4.5 | Informe final | A + B | 10 |
| 4.6 | Slides y ensayo de sustentación | A + B | 10 |

---

## 5. Alcance experimental

Dadas las 2-3 semanas consumidas en habilitación, el alcance debe recortarse **más** que en las otras rutas:

**Núcleo mínimo:** escenarios 1 (espacio libre), 2 (obstáculo único), 6 (forma mutada) y 8 (fuera de distribución). **3 semillas.**

Los escenarios 4 y 5 (traslación y escala) quedan como extensión — lo que es un problema, porque **son ejes centrales de la pregunta de investigación**. Esta pérdida de cobertura es el costo científico de la ruta.

**Compensación parcial:** el paralelismo masivo de Isaac permite, una vez superada la curva de aprendizaje, entrenar muchas más semillas y configuraciones en la misma ventana de tiempo. Si el proyecto tuviera 16 semanas en lugar de 10, esta ruta sería competitiva.

---

## 6. Cronograma

| Sem | Persona A | Persona B | Hito verificable |
|---|---|---|---|
| 1 | Driver NVIDIA; instalar Isaac; CAD v1; contrato | Instalar MoveIt 2 y UR; contrato | **Isaac Sim abre y corre un ejemplo** |
| 2 | Aprendizaje de Isaac Lab; URDF→USD del UR5e | Workspace ROS 2 funcionando | UR5e de 6 GDL visible en Isaac y en Gazebo |
| 3 | Aprendizaje Isaac Lab; DH y alcanzabilidad; doble exportación | OMPL configurado | **COMPUERTA 0: ¿el equipo domina Isaac Lab?** |
| 4 | Definición de la tarea; recompensa v1 | Benchmarks; distancia mínima | Entorno de Isaac Lab ejecutando pasos |
| 5 | Aleatorización de dominio; sensado | Distancia mínima validada; generador de escenarios | Primeras curvas de entrenamiento |
| 6 | Entrenamiento; latencia y seguridad | Generador de escenarios; **equivalencia Isaac↔Gazebo** | **COMPUERTA 1: ¿converge?** |
| 7 | Entrenamiento 3 semillas | Barrido de la línea base | Datos crudos del clásico completos |
| 8 | Cierre de entrenamiento | Cálculo de métricas | Datos crudos del RL completos |
| 9 | Generalización; informe | Estadística; tablero y demo | 5 métricas tabuladas |
| 10 | Slides y ensayo | Slides y ensayo | Defensa ensayada |

**COMPUERTA 0 (semana 3) — la más importante de esta ruta.** Si al terminar la semana 3 el equipo no tiene un entorno de Isaac Lab ejecutando pasos con el UR5e, **se abandona la ruta y se migra a la Ruta 2**. Pasada esa fecha, ya no queda cronograma para recuperarse.

> Nótese que el colchón de la semana 10 desaparece: en esta ruta las semanas 9 y 10 están completamente ocupadas. No hay margen para imprevistos.

---

## 7. Riesgos específicos

| Riesgo | Impacto | Contingencia |
|---|---|---|
| **Driver NVIDIA no se resuelve** | **Ruta inviable** | Migrar a Ruta 2 en la semana 1 |
| **Curva de aprendizaje de USD/Isaac Lab excede 3 semanas** | Alto — pierde el proyecto | Compuerta 0 en la semana 3; migración forzosa a Ruta 2 |
| Dependencia de una sola máquina con GPU | Medio-alto | Coordinar acceso; considerar cómputo en la nube |
| Doble mantenimiento de escena (USD + URDF/SDF) | Medio | Generador paramétrico que emita ambos formatos (3.10) |
| Objeción metodológica por doble motor de física | Alto | Paquete 3.11 obligatorio, igual que en la Ruta 1 |
| Ningún antecedente del estado del arte usa Isaac | Medio | No ayuda a posicionar el aporte frente a los 5 papers y 3 tesis ya seleccionados |
| Sin colchón en el cronograma | Alto | No hay contingencia real; cualquier atraso se traslada a la sustentación |

---

## 8. Ventajas y desventajas

**A favor**
- Simulación acelerada por GPU con entornos masivamente paralelos: una vez funcionando, entrena mucho más rápido que Gazebo o PyBullet.
- Alta fidelidad física y de renderizado; **la demo en vivo sería visualmente muy superior**.
- Domina el estado del arte industrial actual en simulación robótica; valor formativo alto.
- Habilita naturalmente el trabajo futuro de transferencia sim-to-real.

**En contra**
- **No elimina el trabajo de ROS 2, lo añade encima:** la línea base clásica sigue exigiendo MoveIt 2 y OMPL. Son dos stacks completos.
- 2-3 semanas de las 10 se van en habilitación y curva de aprendizaje, sin producir entregables del curso.
- **Obliga a recortar escenarios que son centrales para la pregunta de investigación** (traslación y escala).
- Depende de un driver NVIDIA que hoy no funciona y de una GPU cuya ubicación no está confirmada.
- Mantiene el mismo hueco metodológico de doble motor de física que la Ruta 1, sin la ventaja de rapidez de esta.
- Ningún antecedente del estado del arte lo usa, así que no refuerza el posicionamiento del aporte.
- Cronograma sin colchón.

---

## 9. Veredicto

**No recomendada para este proyecto en 10 semanas.** La ruta combina el hueco metodológico de la Ruta 1 (dos motores de física) con un costo de aprendizaje muy superior al de la Ruta 2, y obliga a sacrificar escenarios que son el corazón de la pregunta de investigación.

**Cuándo sí tendría sentido:** como continuación en la tesis, con 16 semanas o más, driver y GPU resueltos, y con el objetivo explícito de estudiar transferencia sim-to-sim o sim-to-real. En ese contexto, la infraestructura construida en la Ruta 2 (módulo de distancia mínima, generador de escenarios, banco de evaluación) se reutiliza directamente, porque vive por encima del simulador.

---

**Rutas alternativas:** ver `EDT-Ruta2-ROS2-Unificado.md` (recomendada) y `EDT-Ruta1-PyBullet.md`.
