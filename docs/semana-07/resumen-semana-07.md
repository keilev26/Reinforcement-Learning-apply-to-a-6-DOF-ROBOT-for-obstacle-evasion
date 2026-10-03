# Semana 7 — Todo lo realizado

**Rama:** `feature/magician-e6-evaluacion`

Documento único de la semana: reúne todo lo hecho, con método, resultados y cómo reproducirlo. De
lo que la EDT asignaba a la semana 7 (1.4, 1.6, 1.7, 3.3 y la validación de distancias), casi todo
se adelantó a la semana 6 (`../semana-06/resumen-semana-06.md`). Esta semana cierra 1.3 y 1.4 en
su parte de código y **adelanta de la semana 8** el generador de escenarios (3.12), la
**equivalencia entre motores (3.13, compuerta 1)** y la recompensa formal (3.4).

---

## 0. Resumen

| Paquete | Estado | Resultado clave |
|---|---|---|
| **3.13** Equivalencia PyBullet ↔ MoveIt ↔ Gazebo *(sem. 8-9)* | **Hecho: compuerta 1 superada** | Cinemática igual a 4.6·10⁻⁸ m (MoveIt) y 8.5·10⁻⁷ m (Gazebo); escena idéntica al contrato en los tres motores |
| **3.12** Generador de escenarios *(sem. 8)* | **Hecho** | Una sola expansión del contrato para los tres motores; los 19 mundos de Gazebo, verificados contra el contrato |
| **1.3** Geometría de colisión por componente | **Hecho en código** | La colisión de cada componente es su primitiva envolvente del contrato |
| **1.4** Exportación URDF/SDF con convención de anclaje | **Hecho en código** | 10 componentes exportados, anclados en su centro geométrico. El CAD se enchufa como visual en cuanto esté en `cad/` |
| **3.4** Recompensa formal *(sem. 8)* | **Hecho: recompensa v1** | El potencial de precisión da los **primeros éxitos del proyecto**: 11 de 19 variantes con 1 semilla y 300 000 pasos |
| Pendientes de la semana 6 | Hecho | Orientación de la política de prueba medida; commits subidos |

---

## 1. Pendientes de la semana 6 (cerrados)

- **Orientación de la política de 300 000 pasos (recompensa v0).** En el mejor punto de cada
  episodio llega a 4.5-7.7 mm de la meta, pero con 0.15-0.17 rad de error angular, el triple de
  la tolerancia. **La precisión que falta es de orientación, no de posición.** Registrado en
  `../semana-06/3.2-3.3-entorno-y-mdp.md` y punto de partida de la sección 4.
- La evaluación periódica del entrenamiento registra ahora también el error de orientación.
- Commits `fe493e1`, `04d1d82` y `4a93a2c` subidos a la rama.

---

## 2. Paquete 3.13 — Equivalencia entre motores (compuerta 1)

**Criterio de la EDT:** el mismo escenario cargado en los motores debe coincidir en geometría,
posición, escala y límites articulares. Si no coincide, se detiene el entrenamiento.

**Método.** Con Gazebo y MoveIt levantados sobre la variante 2:
- `equivalencia_ros.py` (ROS) recoge la cinemática directa de MoveIt en 200 configuraciones
  aleatorias, los límites de velocidad, la escena de planificación y, para 6 configuraciones libres
  de colisión, el estado que alcanza Gazebo y **las poses de los eslabones que reporta el propio
  Gazebo** (`gz model`);
- `evaluation/verificar_equivalencia.py` (`.venv`) carga lo mismo en PyBullet y compara.

| Comprobación | Resultado |
|---|---|
| Límites de velocidad: PyBullet vs MoveIt | Diferencia 0 |
| Cinemática directa: PyBullet vs MoveIt (KDL), 200 configuraciones × 7 marcos | Error máx. **4.6·10⁻⁸ m** y 5.8·10⁻⁷ rad |
| Cinemática directa: PyBullet vs **Gazebo**, 6 configuraciones × 6 eslabones | Error máx. **8.5·10⁻⁷ m** y 7.3·10⁻⁶ rad (al nivel de los 6 decimales que imprime Gazebo) |
| Escena: contrato vs PyBullet vs MoveIt (descontando el margen de 2 mm) vs SDF de Gazebo | Diferencia máx. **< 10⁻¹⁷** en dimensiones, posición y orientación de los 4 objetos |
| Geometría de colisión del robot: PyBullet vs FCL | Error máx. 1.14 mm, con signo conocido (paquete 3.11) |

**Veredicto: compuerta 1 superada.** Los tres motores ven el mismo robot y la misma escena; la
única diferencia es la ya caracterizada en distancias (≤ 1.14 mm), cubierta por el margen de 2 mm
de la línea base.

Hallazgos laterales:
- Al convertir el URDF a SDF, Gazebo **suma la masa del efector a Link6** (0.1527 + 0.1 kg), lo
  esperable al unir eslabones fijos. No afecta a la cinemática.
- Límites articulares en Gazebo: `gz model` no los expone; salen del mismo URDF por construcción.

Datos: `results/equivalencia_ros_20260929_1920.json`, `results/equivalencia_escenario_2.yaml`,
`results/equivalencia_mundo_gazebo_escenario_2.sdf`.

---

## 3. Paquetes 3.12, 1.3 y 1.4 — Generador de escenarios y exportación de componentes

**3.12.** El mundo de Gazebo se generaba dentro del launch. Pasó a `shared_scenarios/contrato.py`
(`mundo_sdf`), junto a la expansión que ya usaban PyBullet y MoveIt. **Las tres vistas de cualquier
escenario salen ahora del mismo código:**

| Motor | Adaptador | Origen de la geometría |
|---|---|---|
| PyBullet | `gym_env/escena.py` | `contrato.celda()` + `contrato.variantes()` |
| MoveIt | `p6_contrato.py` (`cargar`) | Ídem, con el margen de 2 mm |
| Gazebo | `gazebo_e6.launch.py` | `contrato.mundo_sdf()` |

**1.3 y 1.4.** `tools/exportar_escenarios.py` exporta cada componente de la biblioteca a
`cad/exportados/{urdf,sdf}/<componente>.*`, **con el origen en su centro geométrico**, la misma
convención de `pose` del contrato. La colisión es la primitiva envolvente (geometría de colisión
simplificada). Si existe `cad/<componente>.stl`, se usa como visual del URDF. **Hoy la carpeta
`cad/` no tiene los CAD**, así que la visual es la misma primitiva: en cuanto se suban, el
exportador los toma sin cambiar código.

**Verificación (29 pruebas nuevas, 73 en total):**
- los 19 mundos SDF contienen exactamente los objetos, poses y dimensiones del contrato;
- los 10 componentes cargan en PyBullet con su caja envolvente centrada en el origen (< 2 mm);
- Gazebo levantado con el launch refactorizado ejecuta la tarea en 5 k=2.0: 2 tramos, 0 de 729
  estados ejecutados en colisión, TCP a 0.25-0.30 mm.

**Incidencia registrada.** Un primer arranque falló porque había quedado vivo un servidor de
Gazebo de la corrida anterior (dos mundos `celda` a la vez). Fue un problema del script auxiliar de
parada, no del launch.

---

## 4. Paquete 3.4 — Recompensa formal (v1)

### 4.1 Punto de partida

Con la recompensa v0 y 300 000 pasos, la política rodea el obstáculo y llega a 4.5-7.7 mm en
posición, pero con 0.15-0.17 rad de orientación: 0 éxitos (sección 1). Había dos hipótesis:
- **H1:** la orientación pesa poco en la v0 (1 por rad, frente a 10 por L en posición);
- **H2:** falta una señal fuerte cuando posición **y** orientación están ya cerca a la vez.

### 4.2 Diseño experimental

Dos corridas en paralelo, **misma semilla (0)**, 300 000 pasos, que difieren **solo** en la
recompensa. `training/configs/sac_v1a.yaml` y `sac_v1b.yaml` heredan de `sac_v0` y declaran solo el
cambio.

| Experimento | Cambio respecto de la v0 | Hipótesis |
|---|---|---|
| **A** | Orientación 1 → **5** por rad: salir 0.05 rad cuesta como ~11 mm de posición | H1 sola |
| **B** | Orientación 5 **+ potencial de precisión** Φ = exp(−d / 0.02 m) · exp(−θ / 0.10 rad), peso 10 | H1 + H2 |

El término de precisión entra como **diferencia de potencial**, Φ(s′) − Φ(s). Un bono por paso cerca
de la meta pagaría por quedarse rondándola en lugar de terminar; el moldeado por potencial da el
gradiente sin cambiar la política óptima (`gym_env/entorno.py`, `potencial_precision`).

**Rendimiento.** Dos corridas simultáneas con los 6 hilos por defecto de PyTorch saturan la CPU y
bajan a ~37 transiciones/s cada una. Con `--hilos 2` suben a ~95/s cada una: 300 000 pasos en
~55 min.

### 4.3 Resultados (evaluación determinista cada 20 000 pasos)

| Pasos | v0: éxitos / errores típicos | **A** | **B** |
|---|---|---|---|
| 100 000 | 0/4 | 0/4 (21-358 mm, 0.08-0.20 rad) | 0/4 (11-74 mm, 0.035-0.23 rad) |
| 160 000 | 0/4 | 0/4 | **2/4** (1 y esfera) |
| 200 000 | 0/4 | 0/4 (colapsa: 3.1 rad) | **1/4** (el 2, con obstáculo: 46 pasos, 3.5 mm) |
| 220 000-300 000 | 0/4 | 0/4 | **3/4 en 3 de 5 evaluaciones** (1, 2 y esfera) y 2/4 en las otras 2 (1 y esfera) |

Registros completos: `results/entrenamiento_sac_v{0,1a,1b}_300k_evaluaciones.csv`.

**Conclusión: se rechaza H1 sola y se acepta H1 + H2.** Reequilibrar la orientación no basta (A:
0 éxitos e inestable). El potencial de precisión es lo que permite cerrar los últimos milímetros
(B). **Se adopta B como recompensa v1**: `RECOMPENSA_V1` en `gym_env/entorno.py` y
`training/configs/sac_v1.yaml`.

### 4.4 La política B en las 19 variantes del contrato

`evaluation/evaluar_politica.py`, política determinista, un episodio por variante (todos son
idénticos; ver la decisión abierta de la semana 6). Datos: `results/politica_sac_v1b_300k_metricas.csv`.

| Escenario | Éxito | Colisiones | Observación |
|---|---|---|---|
| 1, 2, 6 (las 3 formas) | **5/5** | 0 | |
| 4 desplazado | 3/5 | 0 | Falla dy=+0.08 y d=(+0.06, +0.06) |
| 5 redimensionado | 3/4 | 0 | Falla k=2.0, el obstáculo más grande |
| 3 tres obstáculos | 0/1 | 0 | Prensa, carro y pieza en tránsito: nunca vistos al entrenar |
| 7 paso estrecho | 0/3 | 0 | Postes nunca vistos al entrenar. Además, la holgura (13-38 mm) cae dentro del umbral de proximidad de 20 mm |
| **8 fuera de distribución** | 0/1 | **1** | **Primer dato de la pregunta de generalización**: con 300 000 pasos, la política no generaliza al utillaje no visto |
| **Total** | **11/19** | 1 | |

**Comparación preliminar con RRT-Connect** en las 11 variantes resueltas. Es una sola semilla con
30 % del entrenamiento previsto: **no tiene valor estadístico**, solo muestra hacia dónde apunta.

| Métrica | Política (SAC, v1) | RRT-Connect | Lectura |
|---|---|---|---|
| M4 cómputo | **11-22 ms** por episodio | 68-118 ms | 5-7 veces menos |
| M5 holgura | **8.5-39 mm** (mediana 29) | 2.5-10.5 mm (mediana 3.8) | La política deja mucho más margen |
| M3 longitud cartesiana | 0.56-0.93 m | 0.48-0.73 m | La política es 4-70 % más larga (mediana +29 %) |
| M4 ejecución | 1.1-2.4 s | 1.3-2.5 s | **No comparable todavía** (4.5) |

### 4.5 Problema de paridad detectado en M4 → resuelto con la opción A1 (sección 5.1)

En varias variantes la política **ejecuta más rápido** que la línea base aunque su trayectoria es
más larga. La causa: la línea base respeta el límite de aceleración de 4.72 rad/s² (TOTG), mientras
que la transición cinemática del entorno **solo limita la velocidad**: la política pasa de reposo a
0.05 rad/paso en un solo paso. La condición de paridad de `metricas.yaml` exige los mismos límites
para ambos métodos, así que **el tiempo de ejecución de la política no es comparable tal como
está**.

| Opción | Efecto |
|---|---|
| **A. Limitar la aceleración en el entorno:** \|Δq_t − Δq_t−1\| ≤ 4.72 · 0.03² = 0.0042 rad | Paridad estricta y fiel al robot real (`ServoJ` también está limitado). Hay que reentrenar. **Recomendada** |
| B. Mantener el entorno y reportar M4 ejecución con la salvedad | Sin reentrenar, pero la métrica pierde validez |

**Decisión del equipo (2026-09-29): A1**, aplicada en la sección 5.1.

### 4.6 Qué sigue (3.5-3.7)

- Entrenar con `sac_v1` hasta 1 M de pasos y 3 semillas, con la aceleración acotada (5.1).
- Las fallas en 5 k=2.0, 4 dy=+0.08 y 7 apuntan al **currículo** (3.6): más peso a los obstáculos
  grandes y cercanos a la tarea, sin tocar las variantes del escenario 8.

---

## 5. Decisiones aplicadas: paridad de aceleración (A1) y protocolo estadístico

### 5.1 Paridad de aceleración (decisión A1)

**Problema (sección 4.5).** La línea base respeta 4.72 rad/s² (TOTG) y el entorno solo limitaba la
velocidad: la política podía pasar de 0 a 1.67 rad/s en un paso, unos 55 rad/s², 12 veces el
límite. Por eso "ejecutaba más rápido" con trayectorias más largas. El tiempo de ejecución (M4) no
era comparable.

**Cambio.** `metricas.yaml` 2.1 declara `aceleracion_max_rad_s2: 4.72`. El entorno recorta cada
paso a |Δq_t − Δq_t−1| ≤ 4.72 · 0.03² = **0.0042 rad** por articulación, antes del tope de
velocidad. La acción sigue siendo Δq acotado (el MDP aprobado). La observación ya incluía el Δq
anterior, así que la política ve su velocidad y sabe cuánto puede cambiarla.

**Verificación.**
- `test_aceleracion_acotada`: acelerando y frenando en seco, ningún paso cambia Δq en más de
  0.0042 rad.
- El controlador de referencia (recta articular con perfil trapezoidal, `gym_env/controladores.py`)
  resuelve el espacio libre y el paso estrecho en **39 pasos (1.17 s)**. Con los mismos límites,
  el mínimo teórico para llegar exactamente a la meta es de ~1.3 s: la política termina al entrar
  en la tolerancia de 5 mm, sin completar el último frenado. **Asimetría residual: ~0.1 s a favor
  de la política**, que se declara.

### 5.2 Protocolo estadístico (recomendación de la semana 6)

**Problema.** Con política determinista y entorno cinemático, las "100 repeticiones por escenario"
de una misma variante son 100 copias del mismo episodio.

**Cambio (`metricas.yaml` 2.1, `protocolo`).**

| Elemento | Definición |
|---|---|
| Conjunto de evaluación | **100 escenas fijas** muestreadas de la distribución de entrenamiento, siempre con obstáculo, con semilla 1000 (distinta de las de entrenamiento). Versionado en `shared_scenarios/evaluacion.yaml` y generado por `tools/generar_evaluacion.py` |
| Composición | 36 prismas, 27 cilindros y 37 esferas; se descartaron 4 escenas donde la tarea era infactible |
| Política | 1 episodio por escena y semilla (determinista); 3 semillas en el núcleo |
| Línea base | 3 consultas por escena (el planificador es estocástico) |
| Comparación | Wilcoxon **pareado por escena**: política = media entre semillas, línea base = media entre consultas. Las métricas continuas solo en escenas donde ambos métodos tienen éxito |
| Variantes fijas | Las 19 del contrato se siguen evaluando, una vez por semilla, para los análisis por escenario (el 8 es el de generalización) |

Implementación:
- `contrato.escenas_evaluacion()`, fuente única de las escenas;
- `EntornoE6.reset(options={"obstaculos": ...})`;
- `evaluar_politica.py --conjunto evaluacion` y `benchmark_linea_base.py --conjunto evaluacion`;
- `evaluation/comparar.py`, la prueba, con 2 pruebas sintéticas: detecta la dirección correcta y
  no declara diferencias donde no las hay.

### 5.3 Primera aplicación completa del protocolo (recompensa v1 + aceleración acotada)

**Entrenamiento.** `sac_v1` con el entorno A1: semillas 0 y 1, 300 000 pasos en paralelo
(`--hilos 2`, ~55 min).

**Resultado: 0 éxitos en ambas semillas.** La misma recompensa **sin** el límite de aceleración
resolvía 3 de 4 variantes de evaluación a los 300 000 pasos (sección 4.3). Con el límite, las
políticas se quedan a una mediana de **53-59 mm y 0.18-0.20 rad** de la meta y agotan los 300
pasos.

**Interpretación.** Es el costo previsto al decidir A1: la política tiene que **anticipar el
frenado** para detenerse dentro de 5 mm, con cambios de velocidad de como mucho 0.0042 rad por
paso. 300 000 pasos son el 30 % del entrenamiento previsto para 3.5, y las evaluaciones periódicas
seguían mejorando (de ~400 mm a ~15-30 mm en las variantes sencillas). **Se continúa el
entrenamiento hasta 1 M de pasos por semilla** (`training/entrenar_sac.py --desde`), en curso.

**Línea base en las 100 escenas del conjunto de evaluación.** Medida con la CPU libre, para que
M4 sea comparable:

| Método | M1 éxito | M2 colisiones | M3 cart. (mediana) | M4 cómputo | M4 ejecución | M5 d_min |
|---|---|---|---|---|---|---|
| RRT-Connect (3 consultas/escena) | **296/300** | 0 | 0.598 m | 103 ms | 2.06 s | 3.3 mm |
| LazyPRM\* (1 consulta/escena) | **99/100** | 0 | 0.626 m | 5 043 ms | 2.05 s | 7.7 mm |
| SAC v1, aceleración acotada, 300 000 pasos (2 semillas) | 0/200 | 15 episodios con colisión | — | 85 ms (300 pasos) | 9.0 s (agota) | — |

Fallas de la línea base:
- **E074** (prisma k = 1.87, muy cerca de la tarea): MoveIt no encuentra cinemática inversa con el
  margen de 2 mm (-31) en ninguno de los dos planificadores. Es una consecuencia real de la
  configuración de la línea base (1 de 100 escenas) y se mantiene en el conjunto.
- **E008**: un rechazo de `ValidateSolution`.

**Comparación pareada (Wilcoxon, 100 escenas).** El protocolo corre de punta a punta. Con 0 éxitos
de la política solo se puede comparar M1: la línea base es mejor (p ≈ 10⁻²³ frente a ambos
planificadores). M3, M4 y M5 no tienen pares.

Hallazgo de la herramienta: con 0 pares, el comparador imprimía "sin diferencia significativa",
lo que es engañoso. Ahora dice "sin pares: algún método no tuvo éxitos".

Datos:
- `results/linea_base_evaluacion_20260930_{0648,0651}_metricas.csv` (crudos en `results/raw/`);
- `results/politica_sac_v1_acel_s{0,1}_300k_{evaluacion,contrato}.csv`;
- `results/entrenamiento_sac_v1_acel_s{0,1}_300k_evaluaciones.csv`.

### 5.4 Continuación hasta 1 M de pasos: primera comparación con datos en ambas direcciones

Las dos semillas se continuaron desde los modelos de 300 000 pasos hasta **1 M**
(`entrenar_sac.py --desde`; el búfer de repetición se rellena antes de volver a actualizar).

**Evolución.** Los primeros éxitos con aceleración acotada aparecen hacia los 320 000-340 000
pasos. Desde ~900 000, ambas semillas resuelven 3 de 4 variantes de evaluación en la mayoría de
las evaluaciones. La política queda a **4-10 mm** de la meta: que cuente como éxito depende de caer
justo por debajo o por encima de los 5 mm, y por eso la tasa oscila entre evaluaciones.

**Las 19 variantes del contrato:** **9/19 en ambas semillas, 0 colisiones en todas**. Resuelve 1,
2, las tres formas del 6, 4 dx = +0.08, 4 dy = −0.08, y 5 k = 0.6 y k = 1.0. Falla 3, 5 k ≥ 1.5, el 7
y el **8, pero sin chocar**: sin el límite de aceleración, la política de 300 000 pasos chocaba en
el 8.

**Las 100 escenas del conjunto de evaluación:**

| | Semilla 0 | Semilla 1 |
|---|---|---|
| Éxitos | **44/100** | **43/100** |
| Por forma: prisma / cilindro / esfera | 11/36 · 12/27 · 21/37 | 12/36 · 11/27 · 20/37 |
| Episodios con colisión | 9 | 5 |
| Error de posición final (mediana) | 11.0 mm | 14.7 mm |

**Comparación pareada** (Wilcoxon, por escena; las métricas continuas, en las 45 escenas donde
ambos métodos tienen éxito). Salida completa en `results/comparacion_sac_v1_1M_vs_*.txt`.

| Métrica | Política (mediana) | RRT-Connect | p | Veredicto | LazyPRM\* | p | Veredicto |
|---|---|---|---|---|---|---|---|
| M1 éxito | 44 % | 99 % | 10⁻¹³ | línea base | 99 % | 10⁻¹³ | línea base |
| M3 cartesiana | 0.561 m | 0.576 m | 0.67 | sin diferencia | 0.602 m | 0.046 | política |
| M3 articular | 2.96 rad | 2.45 rad | 10⁻¹² | línea base | 2.63 rad | 10⁻⁷ | línea base |
| **M4 cómputo** | **22 ms** | 91 ms | 10⁻¹⁴ | **política** | 5 039 ms | 10⁻¹⁴ | **política** |
| **M4 ejecución** | 2.04 s | 1.96 s | 0.30 | **sin diferencia** | 2.00 s | 0.09 | sin diferencia |
| **M5 holgura** | **36 mm** | 4 mm | 10⁻¹⁴ | **política** | 8 mm | 10⁻⁹ | **política** |

**Lectura (preliminar: 2 semillas, el protocolo pide 3):**

1. **El compromiso que plantea la pregunta de investigación aparece medido.**
   - La política cuesta **4 veces menos cómputo** que RRT-Connect y **230 veces menos** que LazyPRM\*.
   - Mantiene **9 veces más holgura** con los obstáculos.
   - El precio es la fiabilidad: resuelve el 44 % de las escenas frente al 99 % de la línea base, y
     choca en el 5-9 %.
2. **Con la paridad de aceleración, el tiempo de ejecución es igual** (p = 0.30). Confirma que la
   "ventaja" de la sección 4.4 era un artefacto del entorno sin límite de aceleración: la decisión
   A1 era necesaria.
3. **La morfología importa** (eje del escenario 6): con la esfera la política acierta el ~55 % de
   las escenas, y con el prisma y el cilindro, ~30-40 %. Es un resultado directo para la pregunta
   de investigación.
4. **Qué sigue:**
   - la tercera semilla del núcleo;
   - **currículo (3.6)** para los obstáculos grandes (k ≥ 1.5) y cercanos a la tarea;
   - revisar si la tolerancia de 5 mm deja al 44 % en un borde artificial: muchas fallas quedan a
     5-10 mm. **No se cambia la tolerancia para mejorar el número**: se reporta la distribución del
     error final junto a M1.

> **Corrección (semana 8).** La sospecha de que muchas fallas quedaban a 5-10 mm de la meta **no se
> sostiene** en las 100 escenas: subir la tolerancia de 5 a 10 mm añade 0 y 3 puntos a las dos
> semillas, y los fallos son sobre todo escenas en las que la política no llega. Solo ocurría en las 4
> variantes fáciles que se evalúan durante el entrenamiento. Ver `../semana-08/generalizacion-y-metricas.md`.

Datos: `results/politica_sac_v1_acel_s{0,1}_1M_{evaluacion,contrato}.csv`,
`results/entrenamiento_sac_v1_acel_s{0,1}_300k-1M_evaluaciones.csv`.

**Nota sobre la GPU (RTX 3050 Mobile, 4 GB).**
- **Causa del fallo:** el módulo del driver 580 no estaba compilado para el kernel 7.0.0-34. Los
  restos incompletos del driver 550 en DKMS impedían la compilación automática al actualizar el
  kernel.
- **Solución (2026-09-30):** `sudo dkms install nvidia/580.178.04 -k 7.0.0-34-generic` y
  `sudo modprobe nvidia`, sin reiniciar. `nvidia-smi` ya la ve (CUDA 13.0).
- **PyTorch con CUDA:** instalado (`2.14.1+cu130`). La raíz tenía 3 GB libres, así que el `.venv`
  se movió a la partición `/data` (339 GB libres) y quedó un **enlace simbólico** `.venv` en el
  proyecto: todas las rutas siguen iguales.
- **Medición:** 20 000 pasos de SAC tardan **181 s en CPU y 183 s en GPU**. Sin ganancia: la red es
  pequeña (256 × 256, lotes de 256) y el tiempo lo consumen la simulación de PyBullet y el bucle de
  Python. `entrenar_sac.py --dispositivo {auto,cpu,cuda}`.
- **Corrección (semana 8):** aquí se supuso que la GPU serviría para varias corridas en paralelo.
  **La medición dice lo contrario**: dos corridas en GPU alcanzan ~35 pasos/s cada una, frente a ~95
  en CPU (ver `../semana-08/resumen-semana-08.md`, sección 1). Para este proyecto se entrena en CPU.
- **Alcance:** la GPU solo acelera el entrenamiento. La inferencia de M4 se mide en CPU por
  contrato (`metricas.yaml`, `hardware`).

---

## 6. Estado del cronograma

- Semana 7: 1.3, 1.4, 3.4, 3.12 y 3.13 marcados como realizados.
- **La ruta crítica baja de 14 a 13 semanas**: el proyecto gana una semana de holgura antes de la
  sustentación. Ahora pasa por la cadena de RL: 3.5 → 3.6 → 3.7.
- **Decisiones tomadas:** paridad de aceleración (A1) y protocolo estadístico por escenas
  muestreadas, ambas aplicadas en la sección 5.

## 7. Reproducir

```bash
# 3.13 (con Gazebo + MoveIt corriendo: ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py escenario:=2)
python3 ros2_ws/src/rl6gdl_planning/scripts/equivalencia_ros.py --variante 2
.venv/bin/python -m evaluation.verificar_equivalencia results/equivalencia_ros_<fecha>.json \
    /tmp/rl6gdl_e6_escenario_2.sdf

# 1.3, 1.4 y 3.12
.venv/bin/python tools/exportar_escenarios.py [--mundos]
.venv/bin/python -m pytest

# 3.4 (los dos experimentos en paralelo, ~55 min)
.venv/bin/python -m training.entrenar_sac --config sac_v1a --pasos 300000 --semilla 0 --hilos 2 &
.venv/bin/python -m training.entrenar_sac --config sac_v1b --pasos 300000 --semilla 0 --hilos 2 &
.venv/bin/python -m evaluation.evaluar_politica training/runs/sac_v1b_s0_<fecha>/modelo_final.zip
```
