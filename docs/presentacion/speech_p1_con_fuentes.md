# Speech de la Presentación 1 con las fuentes de cada valor

Texto para decir en voz alta (10 min), con el reparto **C** (Caleb) y **L** (Leonardo). Debajo de cada diapositiva va
una tabla con **de dónde sale cada cifra** y qué decir si preguntan por ella. Los números entre corchetes remiten a
la lista de referencias al final (misma numeración que el informe). Las variantes más cortas por diapositiva están en
`guion_p1.md`.

**Regla de honestidad para la sala:** las cifras de mercado vienen de fuentes públicas y algunas son secundarias
(se dice así); las cifras de resultados son propias y salen de `results/*.csv`.

---

## 1 · Carátula (0:20) — C

> Buenos días, profesor. Somos Caleb Camargo y Luis Leonardo Tupac, de Ingeniería Mecatrónica. Les presentamos
> nuestro proyecto: un planificador de movimiento para el brazo DOBOT Magician E6 que aprende por refuerzo
> profundo a evitar obstáculos, y que comparamos contra los planificadores clásicos.

Sin cifras.

## 2 · Temas (0:10) — C

> Veremos el problema, el estado del arte, la justificación y los objetivos, la solución y su metodología, el marco
> teórico, la viabilidad, y por último cronograma, presupuesto y conclusiones.

Sin cifras.

## 3 · Situación problemática (0:35) — L

> La automatización crece: la Federación Internacional de Robótica contó unos 542 mil robots industriales
> instalados en 2024, casi el doble que una década antes, y un parque de 4.66 millones de unidades. Pero el
> crecimiento se concentra en grandes fábricas: Asia absorbió el 74 % de las instalaciones. En el Perú, el
> Ministerio de la Producción registra unas 74 mil empresas metalmecánicas, con más de 350 mil empleos y más del 9 %
> del PBI manufacturero. Son pymes de alta variedad y bajo volumen: lotes cortos de piezas distintas.
>
> Y ahí está el choque: un robot industrial sigue una trayectoria programada para una disposición concreta de la
> celda. Si cambia un utillaje, hay que reprogramar. Los integradores estiman que un robot de 50 mil dólares puede
> acarrear 150 mil o más de integración para una sola tarea. Por eso muchas pymes no automatizan.

| Cifra | Fuente | Qué decir si preguntan |
|---|---|---|
| 542 000 robots instalados en 2024; casi el doble que 10 años antes | IFR, *World Robotics 2025*, comunicado de prensa [14] | Es la nota de prensa de la IFR; el informe completo es de pago |
| Parque operativo de 4 664 000 (+9 %) | Misma nota IFR [14] | — |
| Asia 74 %, China 54 % de las instalaciones | Misma nota IFR [14] | — |
| 74 000 empresas, 350 000 empleos, > 9 % del PBI manufacturero | PRODUCE-OGEIEE, *Estudio del sector metalmecánico 2024*, citado por ProActivo, 16-jul-2025 [15] | Citamos la nota periodística; no leímos el estudio original |
| 48 robots en el Perú a fines de 2017 (solo si preguntan) | IFR vía Aduana News [16] | Fuente secundaria y antigua; no hallamos cifra oficial reciente, y eso ya indica baja penetración |
| Robot de USD 50 000 → USD 150 000 de integración | *The Fabricator* [17] | Es estimación de integradores, no estudio independiente: lo damos como orden de magnitud |

## 4 · Problema (0:30) — L

> El problema general es la limitada capacidad de los manipuladores de seis grados de libertad para evitar
> obstáculos cuando cambia la celda, porque dependen de trayectorias fijas o de replanificar desde cero. La pregunta
> de ingeniería es qué hay que considerar, en diseño mecatrónico y de software, para construir un planificador
> reactivo basado en refuerzo para el Magician E6 que reduzca ese costo de reconfiguración.

Sin cifras (6 GDL es característica del robot, ver diap. 11).

## 5 · Estado del arte: productos (0:35) — L

> Revisamos cuatro soluciones. RapidPlan, de Realtime Robotics, planifica en milisegundos, pero con hardware
> propietario y licencia cerrada. cuMotion, de NVIDIA, es gratuito pero exige una GPU NVIDIA a bordo. RoboDK
> calcula rutas estáticas: si cambia el utillaje hay que replanificar y reexportar, y la licencia educativa cuesta
> unos 145 dólares al año. MoveIt con OMPL es abierto y es el estándar, pero replanifica desde cero con tiempo
> variable. Ninguna es una política aprendida, y ninguna mide cuánto se degrada ante geometrías nuevas. El robot de
> nuestro proyecto cuesta unos 6 995 dólares; en nuestro caso es prestado.

| Cifra | Fuente | Qué decir si preguntan |
|---|---|---|
| RapidPlan: planificación en milisegundos, hardware propietario | Realtime Robotics, página del producto [9] (consultada 19-sep-2026) | Precio no publicado ("bajo cotización") |
| cuMotion: gratuito, requiere GPU NVIDIA | NVIDIA Developer Blog, Isaac Manipulator [10] (19-sep-2026) | — |
| RoboDK: ruta estática; licencia educativa USD 145/año | Documentación de RoboDK [11]; precio de robodk.com/pricing en sep-2026, recogido en el documento de contexto [19] | El precio **no se reverificó** en octubre; puede haber cambiado |
| MoveIt/OMPL gratuito, estándar | MoveIt [29], OMPL [28] | — |
| DOBOT Magician E6 ≈ USD 6 995 | RobotLAB, ficha de producto [18] (oct-2026) | Precio de un vendedor, varía; para nosotros el costo es 0 porque es prestado |

## 6 · Estado del arte: publicaciones (0:35) — C

> De las publicaciones, cuatro nos importan. Mao y colaboradores usan el mismo stack que nosotros, PyBullet,
> Gymnasium y Stable-Baselines3, pero no comparan contra planificadores clásicos. Fidalgo y colaboradores hicieron
> el benchmark más serio contra OMPL, con cien mil trayectorias, pero su entorno no tiene obstáculos y ellos mismos
> admiten que los clásicos conservan ventaja de adaptabilidad. Jurgenson y Tamar tratan la generalización, con
> entrada visual y sin OMPL. Y Liu usa un robot de siete grados de libertad con un controlador intermedio.
> Ninguno reúne obstáculos, política aprendida aislada, comparación con clásicos y medición de la generalización a la
> vez. Ese es el vacío que ocupa el proyecto.

| Dato | Fuente | Nota |
|---|---|---|
| Mao et al. 2025: SAC, PyBullet + Gymnasium + SB3, UR3e | [1] *Experimental Technology and Management* 42(4) | El texto está en chino; leímos el resumen en inglés |
| Fidalgo et al. 2025: unas 100 000 trayectorias, OMPL vs DRL, 14 observaciones | [4] *Sensors* 25(17), 5282 | Es el antecedente más cercano |
| Jurgenson y Tamar 2019: entrada visual, sin OMPL | [5] RSS 2019, arXiv:1906.00214 | — |
| Liu 2024: robot de 7 GDL (Franka Panda), controlador intermedio | [6] tesis de la Univ. de Toronto | — |

## 7 · Justificación (0:35) — C

> Cuatro razones. Permitir que la celda cambie sin reprogramar. Evitar licencias y GPU a bordo: todo es código
> abierto. Aportar una medición que falta en la literatura: cuánta variación geométrica tolera una política frente a
> OMPL. Y resolver problemas de ingeniería reales: corregir el modelo del robot, diseñar la recompensa y respetar el
> período de control de 30 milisegundos. Al ser simulación no hay personas junto al robot; en una celda real
> aplicarían la ISO 10218 y la Ley 29783.

| Dato | Fuente |
|---|---|
| Período de control de 30 ms (≈33 Hz) | Configuración del entorno del proyecto (`config/`, `docs/semana-0X`); coincide con el servo del E6 |
| ISO 10218 (seguridad en robots industriales) y Ley 29783 (SST, Perú) | Normas citadas en el informe, sección III; no se verificó su texto vigente |

## 8 · Objetivo general (0:20) — C

> Desarrollar y evaluar un planificador reactivo basado en SAC para el Magician E6 que evite obstáculos de forma y
> posición variables, y compararlo con OMPL en igualdad de condiciones. Tres ideas: evitar, comparar de forma justa
> y medir hasta dónde generaliza.

Sin cifras.

## 9 · Objetivos específicos (0:30) — L

> Tenemos seis objetivos específicos, cada uno con su indicador. Los cuatro primeros están logrados: el modelo del
> robot y la celda, el contrato de escenarios y las cinco métricas, la línea base medida y tres entrenamientos de un
> millón de pasos. El quinto, validar frente a OMPL y medir la generalización, está en curso, y el sexto, el diseño
> electrónico de la integración con el E6, está pendiente. La validación usa la prueba de Wilcoxon pareada.

| Cifra | Fuente |
|---|---|
| 3 entrenamientos × 1 M pasos | `results/mejor_sac_v1_s{0,1,2}_1M_pc.json`, `docs/semana-08/entrenamiento-pc-potente.md` |
| Estados logrado/en curso/pendiente | Tabla de objetivos del informe (sección IV) y `docs/EDT.md` |
| Wilcoxon pareada | Wilcoxon 1945 [31] |

## 10 · Diagrama pictórico (0:40) — L

> El contrato de escenarios y la biblioteca CAD fijan la tarea, las métricas y las piezas de la celda. El generador
> compone cada escena. El entorno simula el E6 y entrega al agente 43 observaciones y una recompensa. El agente SAC
> responde con un incremento articular y se entrena en la PC con GPU. Las mismas escenas se planifican con MoveIt y
> OMPL, y un evaluador común calcula las cinco métricas para ambos métodos. Probar en el robot físico queda como
> trabajo adicional.

| Cifra | Fuente |
|---|---|
| 43 observaciones | `docs/semana-0X` del entorno: desglose en `docs/semana-09/formulas-explicadas.md` §2 (6 posiciones + 6 incremento previo + 3 error de posición + ... + distancias por eslabón); es el espacio de observación del entorno Gymnasium |
| 5 métricas: éxito, colisión, longitud, tiempo de ejecución, distancia mínima | Contrato de escenarios, `docs/semana-0X`; informe sección VI.4 |

## 11 · Componentes (0:25) — L

> El robot es el Magician E6, de 6 grados de libertad, 750 gramos de carga útil y 450 milímetros de alcance.
> Entrenamos en PyBullet con Gymnasium y Stable-Baselines3. La línea base se mide en ROS 2 con MoveIt, OMPL y
> Gazebo, un motor distinto, así que hay que verificar la equivalencia. Elegimos SAC por su eficiencia de muestreo,
> y entrenamos en una PC prestada con GTX 1080.

| Cifra | Fuente |
|---|---|
| E6: 6 GDL, carga útil 750 g, alcance 450 mm, repetibilidad ±0.1 mm | Ficha del fabricante / RobotLAB [18]; modelo URDF oficial del E6 |
| SAC elegido por eficiencia de muestreo | Haarnoja et al. 2018 [20]; SB3 [22] |
| GTX 1080, PyTorch cu126 | `docs/semana-08/guia-pc-nueva.md`, `entrenamiento-pc-potente.md` |
| Verificación de equivalencia PyBullet–Gazebo | `results/equivalencia_escenario_2.yaml`, `equivalencia_ros_20260929_1920.json` |

## 12 · Metodología (0:30) — C

> Ocho etapas. Las cinco primeras están hechas: contrato, modelo, entorno, línea base y entrenamiento. La sexta,
> evaluación y generalización, está en curso. La séptima es el diseño electrónico y la octava, el robot físico,
> queda como adicional. Hay un ciclo entre evaluar y ajustar la recompensa y el muestreo.

Sin cifras externas; estado según `docs/EDT.md` y `tools/gen_cronograma.py`.

## 13 · Marco teórico: decisión de Markov (0:25) — C

> Formulamos el problema como un proceso de decisión de Markov. El estado son 43 números: posiciones articulares,
> el incremento anterior, el error de pose y, por eslabón, la distancia y dirección al obstáculo. La acción son seis
> incrementos acotados a 0.05 radianes cada 30 ms. La recompensa premia el progreso, la orientación y la precisión,
> y castiga cercanía, brusquedad y tiempo: más diez por llegar, menos diez por chocar. El agente maximiza el retorno
> descontado con gamma 0.99.

| Cifra | Fuente |
|---|---|
| MDP, retorno descontado | Sutton y Barto [23] |
| Δq máximo 0.05 rad, 30 ms, γ = 0.99, ±10 de recompensa terminal, pesos de la recompensa | `config/` de entorno y recompensa; explicación con ejemplos en `docs/semana-09/formulas-explicadas.md` §2-3 |
| Cinemática, Denavit-Hartenberg | Siciliano et al. [24] |

## 14 · Marco teórico: SAC (0:35) — C

> SAC maximiza la recompensa más la entropía de la política, lo que obliga a explorar. Usa dos críticos y toma el
> mínimo para no sobreestimar. El crítico se entrena contra el valor objetivo; el actor, con reparametrización. La
> temperatura alfa se ajusta sola hacia una entropía objetivo de menos seis, y las redes objetivo se actualizan
> despacio, con tau 0.005.

| Cifra | Fuente |
|---|---|
| Doble crítico, entropía, temperatura automática | Haarnoja et al. 2018 [20] y [21] |
| Entropía objetivo = −dim(A) = −6 | Haarnoja et al. [21]; dim(A) = 6 articulaciones |
| τ = 0.005, γ = 0.99, lote 256, búfer 10⁶, redes 256×256, lr 3·10⁻⁴ | Hiperparámetros por defecto de SB3 [22], usados en `config/` del entrenamiento |

## 15 · Planificación y métricas (0:20) — L

> La cinemática del E6 sale de Denavit-Hartenberg. La manipulabilidad de Yoshikawa se anula en las singularidades; por
> eso la acción es un incremento articular y no cartesiano. El mapa muestra que recoger y depositar están en la zona
> fiable. La línea base usa RRT-Connect y LazyPRM*, y las métricas se comparan por pares con Wilcoxon.

| Dato | Fuente |
|---|---|
| Mapa de alcanzabilidad (105 de 221 puntos del plano de trabajo) | `results/analisis_cinematico_e6.yaml` (221 celdas, 105 alcanzables) y `docs/semana-06/1.6-1.7-alcanzabilidad-y-singularidades.md`; figura `docs/informe/img/alcanzabilidad_e6.png` |
| RRT-Connect | Kuffner y LaValle [25]; LazyPRM Bohlin y Kavraki [26]; OMPL [28]; FCL para colisiones [30] |
| Wilcoxon | [31] |

## 16 · Aplicaciones (0:15) — L

> La aplicación directa es el abastecimiento de máquinas CNC. Indirectamente, un banco de pruebas reutilizable y
> material docente. Los usuarios son pymes metalmecánicas, integradores y escuelas de ingeniería.

Sin cifras.

## 17 · Viabilidad técnica (0:25) — C

> Técnicamente ya funciona, y lo decimos con honestidad. La mejor semilla llega a 87 % de éxito en 100 escenas, pero
> la media de las tres semillas es 66 %, frente a 99 % de RRT-Connect, y varía mucho de una semilla a otra. A cambio,
> la política usa unas cinco veces menos cómputo, 19 milisegundos por episodio contra 98, y deja más holgura: 30
> milímetros frente a 4.

| Cifra | Fuente (carpeta `results/`) |
|---|---|
| Éxito SAC por semilla: 0.68 / 0.43 / 0.87; media 0.66 (100 escenas de evaluación) | `politica_sac_v1_s{0,1,2}_1M_pc_evaluacion.csv` |
| Colisión de SAC ≈ 2 % | Mismos CSV, columna de colisión |
| RRT-Connect 296/300 = 98.7 %, 0 colisiones, ≈ 98-103 ms | `linea_base_evaluacion_20260930_0648_metricas.csv` y `..._0651_...csv` |
| LazyPRM* 99/100, ≈ 5 s | Mismos CSV de línea base |
| Cómputo 19.4 vs 97.8 ms por episodio; holgura 30 vs 4 mm; éxito 0.667 vs 1.000 (p = 5·10⁻¹¹) | `comparacion_sac_v1_1M_vs_RRTConnect.txt` (Wilcoxon pareado) |
| Tiempo de ejecución sin diferencia (p = 0.87) | Mismo archivo |
| Éxito cae con el tamaño del obstáculo (de 1.00 a 0.62 en la mejor semilla) | `results/analisis_generalizacion/` y figura `fig_tamano.png` |

Aviso: "unas cinco veces menos cómputo" = 97.8 / 19.4 ≈ 5.0. Se compara cómputo por episodio, no latencia por paso.

## 18 · Viabilidad económica, social y operativa (0:20) — L

> Hasta hoy no se gastó nada: todo es prestado y el software es abierto. Socialmente, abarata la automatización
> variable y no expone a personas. Operativamente, se entrena en una PC con GPU, unas cuatro horas por corrida, y la
> política se ejecuta en CPU. Descartamos Isaac Sim, seguir con el UR5e y entrenar con demostraciones de OMPL.

| Cifra | Fuente |
|---|---|
| ≈ 3-4 horas por millón de pasos | `docs/semana-08/entrenamiento-pc-potente.md` (medición propia en la GTX 1080) |
| Costo S/ 0 | Declaración de los autores: robot, PC y portátil prestados |

## 19 · Cronograma (0:20) — L

> En verde lo realizado hasta la semana 8. En ámbar, lo de esta semana: evaluación y esta presentación. En gris, lo
> pendiente: una segunda iteración con mejor muestreo y recompensa, el diseño electrónico, la Presentación 2 en las
> semanas 11 y 12, el informe y la sustentación final.

Fuente: `tools/gen_cronograma.py` (cronograma de 16 semanas) y reglamento del curso. Confirmar la semana de la P1.

## 20 · Presupuesto (0:15) — L

> El robot, la PC de entrenamiento y la portátil son prestados, y el software es abierto: costo cero. El único gasto
> previsto es la impresión, unos 20 soles estimados.

| Cifra | Fuente |
|---|---|
| S/ 20 de impresión | **Estimación propia, sin cotización**; decirlo si preguntan |
| Todo lo demás S/ 0 | Préstamos; software abierto |

## 21-22 · Producto final (0:20) — C y L

> *(C)* En el diagrama resaltamos lo que se implementa: todo lo de simulación y la comparación; el robot físico queda
> en gris, como adicional. *(L)* Y en la metodología, las etapas uno a siete se hacen en el curso; la ocho es
> adicional.

Sin cifras.

## 23 · Conclusiones (0:25) — C

> Cuatro conclusiones. El problema es real y está poco cubierto en el Perú. Ya tenemos la infraestructura completa.
> Con la formulación actual la política aún no iguala a OMPL, 66 % contra 99 %, con mucha variación entre semillas,
> pero usa cinco veces menos cómputo y deja más holgura. Y lo que sigue es mejorar el muestreo y la recompensa,
> validar con más escenas, diseñar la integración con el E6 y preparar la demostración en vivo. Gracias;
> quedamos atentos a sus preguntas.

Cifras: las de la diapositiva 17.

---

## Referencias citadas (numeración del informe)

| N.º | Referencia |
|---|---|
| [1] | J. L. Mao et al., *Experimental Technology and Management*, 42(4), 78-85, abr. 2025. |
| [4] | I. Fidalgo Astorquia et al., «Comparative benchmark of sampling-based and DRL motion planning methods for industrial robotic arms», *Sensors* 25(17), 5282, 2025. |
| [5] | T. Jurgenson y A. Tamar, «Harnessing reinforcement learning for neural motion planning», RSS 2019, arXiv:1906.00214. |
| [6] | J. Liu, tesis B.A.Sc., University of Toronto, 2024. |
| [9] | Realtime Robotics, RapidPlan, https://rtr.ai/rapidplan/ (19-sep-2026). |
| [10] | NVIDIA, Isaac Manipulator / cuMotion, NVIDIA Developer Blog (19-sep-2026). |
| [11] | RoboDK, Collision-free motion planner, https://robodk.com/doc/en/Collision-Avoidance-Collision-Free-Motion-Planner.html (19-sep-2026). |
| [14] | IFR, *World Robotics 2025*, comunicado de prensa, https://ifr.org/ifr-press-releases/news/global-robot-demand-in-factories-doubles-over-10-years (oct-2026). |
| [15] | PRODUCE-OGEIEE, Estudio del sector metalmecánico 2024, citado en ProActivo, 16-jul-2025, https://proactivo.com.pe/sector-metalmecanico-genera-350-mil-empleos-y-74-mil-empresas/ |
| [16] | Aduana News, «Robots en América Latina…», cifras de la IFR, https://aduananews.com/en/robots-en-america-latina-cuantos-son-donde-estan-y-cuanto-tributan/ |
| [17] | *The Fabricator*, «How robots program themselves», https://www.thefabricator.com/thefabricator/article/automationrobotics/how-robots-program-themselves |
| [18] | RobotLAB, DOBOT Magician E6, https://www.robotlab.com/store/dobot-magician-e6/ (oct-2026). |
| [19] | C. Camargo y L. L. Tupac, Documento de contexto del proyecto, `docs/contexto-proyecto-rl-manipulador-6gdl.md`, 2026. |
| [20] | T. Haarnoja et al., «Soft actor-critic…», ICML 2018, pp. 1861-1870. |
| [21] | T. Haarnoja et al., «Soft actor-critic algorithms and applications», arXiv:1812.05905, 2018. |
| [22] | A. Raffin et al., «Stable-Baselines3», *JMLR* 22(268), 2021. |
| [23] | R. S. Sutton y A. G. Barto, *Reinforcement Learning: An Introduction*, 2.ª ed., MIT Press, 2018. |
| [24] | B. Siciliano et al., *Robotics: Modelling, Planning and Control*, Springer, 2009. |
| [25] | J. J. Kuffner y S. M. LaValle, «RRT-Connect», IEEE ICRA 2000, pp. 995-1001. |
| [26] | R. Bohlin y L. E. Kavraki, «Path planning using lazy PRM», IEEE ICRA 2000, pp. 521-528. |
| [28] | I. A. Şucan, M. Moll y L. E. Kavraki, «The Open Motion Planning Library», *IEEE RAM* 19(4), 2012. |
| [29] | D. Coleman et al., «Reducing the barrier to entry of complex robotic software: a MoveIt! case study», *JOSER* 5(1), 2014. |
| [30] | J. Pan, S. Chitta y D. Manocha, «FCL», IEEE ICRA 2012. |
| [31] | F. Wilcoxon, «Individual comparisons by ranking methods», *Biometrics Bulletin* 1(6), 1945. |

La numeración debe coincidir con el orden de `thebibliography` del informe (`docs/informe/informe_p1.tex`); si
cambia la lista, hay que actualizar esta tabla.

## Antes de exponer: cifras que conviene revisar

1. Verificar que los números de referencia de esta hoja coincidan con los del PDF del informe.
2. Las filas marcadas "no se reverificó" (RoboDK USD 145/año) y "estimación propia" (S/ 20 de impresión) se dicen
   con esa reserva.
3. Las cifras de resultados se pueden regenerar con `tools/analisis_pares.py` y los CSV de `results/`.
