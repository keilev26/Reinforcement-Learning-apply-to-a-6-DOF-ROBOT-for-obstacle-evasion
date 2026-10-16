# Guion de la Presentación 1 (10 min + 5 de preguntas)

Texto para decir en voz alta, diapositiva por diapositiva, con el reparto entre **Caleb (C)** y **Leonardo (L)**.
El reparto sigue lo que hizo cada uno (L: celda, línea base, cronograma; C: entorno, MDP, entrenamiento), pero se
puede cambiar. Tiempo total: 9:25, con 35 s de margen. Las cifras y su origen están en
`docs/semana-09/presentacion-1-informe-y-diapositivas.md`.

Consejos: no leer la diapositiva; mirar al profesor; en las diapositivas con ecuaciones (13 y 14) señalar con la
mano el término del que se habla; tener a mano `formulas-explicadas.md` para las preguntas.

---

## 1 · Carátula (0:20) — C

> Buenos días, profesor. Somos Caleb Camargo y Luis Leonardo Tupac, de Ingeniería Mecatrónica. Les presentamos
> nuestro proyecto: un planificador de movimiento para el brazo DOBOT Magician E6, que aprende por refuerzo
> profundo a evitar obstáculos, y que comparamos con los planificadores clásicos.

## 2 · Temas (0:10) — C

> Vamos a ver el problema, el estado del arte, la justificación y los objetivos, la solución y su metodología, el
> marco teórico, la viabilidad, y por último el cronograma, el presupuesto y las conclusiones.

## 3 · Situación problemática (0:35) — L

> La automatización crece: la IFR contó unos 542 mil robots industriales instalados en 2024. Pero casi todos están
> en grandes fábricas de producción en serie. En el Perú, PRODUCE registra unas 74 mil empresas metalmecánicas,
> más de 350 mil empleos; son pymes de alta variedad y bajo volumen, es decir, lotes cortos de piezas distintas.
>
> Y ahí está el choque: un robot industrial sigue una trayectoria programada para una disposición concreta de la
> celda. Si cambia un utillaje, la trayectoria deja de servir y hay que reprogramar. Para una pyme, eso cuesta
> horas de un ingeniero cada vez, y por eso muchas no automatizan.

*(Si preguntan por el dato de 48 robots en el Perú: es de la IFR en 2017, citado por prensa; no hay cifra oficial
más reciente.)*

## 4 · Problema (0:30) — L

> El problema general es la limitada capacidad de los manipuladores de seis grados de libertad para evitar
> obstáculos cuando cambia la celda, porque dependen de trayectorias fijas o de replanificar todo desde cero. Y la
> pregunta de ingeniería es qué hay que considerar, en diseño mecatrónico y de software, para construir un
> planificador reactivo basado en refuerzo para el Magician E6 que reduzca ese costo de reconfiguración.

## 5 · Estado del arte: productos (0:35) — L

> Revisamos cuatro soluciones. RapidPlan, de Realtime Robotics, planifica en milisegundos, pero con hardware
> propietario y licencia cerrada. cuMotion, de NVIDIA, es gratuito pero exige una GPU NVIDIA a bordo. RoboDK
> calcula rutas estáticas: si cambia el utillaje, hay que replanificar y reexportar. Y MoveIt con OMPL es abierto
> y es el estándar, pero replanifica desde cero con tiempo variable.
>
> Ninguna es una política aprendida, y ninguna mide cuánto se degrada ante geometrías nuevas. El robot de nuestro
> proyecto cuesta unos 6 995 dólares; en nuestro caso es prestado.

## 6 · Estado del arte: publicaciones (0:35) — C

> De las publicaciones, cuatro nos importan. Mao usa el mismo stack que nosotros, pero no compara contra
> planificadores clásicos. Fidalgo hizo el benchmark más serio contra OMPL, pero su entorno no tiene obstáculos;
> sus propios autores admiten que los clásicos conservan ventaja de adaptabilidad. Jurgenson trata la
> generalización, con entrada visual y sin OMPL. Y Liu usa un robot de siete grados de libertad con un
> controlador intermedio.
>
> Ninguno reúne las cuatro cosas a la vez: obstáculos, política aprendida aislada, comparación con clásicos y
> medición de la generalización. Ese es el vacío que ocupa el proyecto.

## 7 · Justificación (0:35) — C

> Cuatro razones. Permitir que la celda cambie sin reprogramar. Evitar licencias y GPU a bordo: todo es código
> abierto. Aportar una medición que falta en la literatura: cuánta variación geométrica tolera una política
> frente a OMPL. Y resolver problemas de ingeniería reales, como corregir el modelo del robot, diseñar la
> recompensa o respetar el período de control de 30 milisegundos.
>
> Al ser simulación, no hay personas junto al robot; si se llevara a una celda real, aplicaría ISO 10218 y la
> Ley 29783 de seguridad y salud en el trabajo.

## 8 · Objetivo general (0:20) — C

> El objetivo general: desarrollar y evaluar un planificador reactivo basado en SAC para el Magician E6, que evite
> obstáculos de forma y posición variables, y compararlo con OMPL en igualdad de condiciones. Tres ideas: evitar
> obstáculos variables, comparar de forma justa y medir hasta dónde generaliza.

## 9 · Objetivos específicos (0:30) — L

> Tenemos seis objetivos específicos, cada uno con su indicador. Los cuatro primeros ya están logrados: el modelo
> del robot y la celda, el contrato de escenarios y las cinco métricas, la línea base medida y tres
> entrenamientos de un millón de pasos. El quinto, validar frente a OMPL y medir la generalización, está en curso,
> y el sexto, el diseño electrónico de la integración con el E6, está pendiente. La validación se hace con la
> prueba de Wilcoxon pareada.

## 10 · Diagrama pictórico (0:40) — L

> Así funciona el sistema. El contrato de escenarios y la biblioteca CAD fijan la tarea, las métricas y las piezas
> de la celda. El generador compone cada escena. El entorno simula el E6 y entrega al agente 43 observaciones y
> una recompensa. El agente SAC responde con un incremento articular y se entrena en la PC con GPU.
>
> Las mismas escenas se planifican con MoveIt y OMPL, y un evaluador común calcula las cinco métricas para ambos
> métodos. Probar en el robot físico es un trabajo adicional, fuera del alcance.

## 11 · Componentes (0:25) — L

> El robot es el Magician E6. Entrenamos en PyBullet con Gymnasium y Stable-Baselines3. La línea base se mide en
> ROS 2 con MoveIt, OMPL y Gazebo, un motor distinto, por lo que hay que verificar la equivalencia. Elegimos SAC
> por su eficiencia de muestreo, y entrenamos en una PC prestada con GTX 1080.

## 12 · Metodología (0:30) — C

> La metodología tiene ocho etapas. Las cinco primeras están hechas: contrato, modelo, entorno, línea base y
> entrenamiento. La sexta, evaluación y generalización, está en curso. La séptima es el diseño electrónico, y la
> octava, el robot físico, queda como adicional. Hay un ciclo entre evaluar y ajustar la recompensa y el
> muestreo.

## 13 · Marco teórico: decisión de Markov (0:25) — C

> Formulamos el problema como un proceso de decisión de Markov. El estado son 43 números: posiciones articulares,
> el incremento anterior, el error de pose y, por eslabón, la distancia y dirección al obstáculo. La acción son
> seis incrementos acotados a 0.05 radianes cada 30 milisegundos. La recompensa premia el progreso, la
> orientación y la precisión, y castiga la cercanía, la brusquedad y el tiempo: más diez por llegar, menos diez
> por chocar. El agente maximiza el retorno descontado con gamma 0.99.

## 14 · Marco teórico: SAC (0:35) — C

> SAC maximiza la recompensa más la entropía de la política, lo que obliga a explorar. Usa dos críticos y toma el
> mínimo para no sobreestimar. El crítico se entrena contra el valor objetivo; el actor, con reparametrización.
> La temperatura alfa se ajusta sola hacia una entropía objetivo de menos seis, y las redes objetivo se actualizan
> despacio, con tau 0.005.

## 15 · Planificación y métricas (0:20) — L

> La cinemática del E6 sale de Denavit-Hartenberg. La manipulabilidad de Yoshikawa se anula en las
> singularidades; por eso la acción es un incremento articular y no cartesiano. El mapa muestra que recoger y
> depositar están en la zona fiable. La línea base usa RRT-Connect y LazyPRM, y las cinco métricas se comparan por
> pares con Wilcoxon.

## 16 · Aplicaciones (0:15) — L

> La aplicación directa es el abastecimiento de máquinas CNC. Indirectamente, un banco de pruebas reutilizable y
> material docente. Los usuarios son pymes metalmecánicas, integradores y escuelas de ingeniería.

## 17 · Viabilidad técnica (0:25) — C

> Técnicamente ya funciona, y lo decimos con honestidad. La mejor semilla llega a 87 por ciento de éxito en 100
> escenas, pero la media de las tres semillas es 66 por ciento, frente a 99 de RRT-Connect, y varía mucho de una
> semilla a otra. A cambio, la política usa unas cinco veces menos cómputo, 19 milisegundos por episodio contra
> 98, y deja más holgura. Es el punto de partida para mejorar.

## 18 · Viabilidad económica, social y operativa (0:20) — L

> Hasta hoy no se gastó nada: todo es prestado y el software es abierto. Socialmente, abarata la automatización
> variable y no expone a personas. Operativamente, se entrena en una PC con GPU, unas cuatro horas por corrida, y
> la política se ejecuta en CPU. Descartamos Isaac Sim, seguir con el UR5e y entrenar con demostraciones de OMPL.

## 19 · Cronograma (0:20) — L

> En verde lo realizado hasta la semana 8. En ámbar, lo de esta semana: evaluación y esta presentación. En gris, lo
> pendiente: una segunda iteración con mejor muestreo y recompensa, el diseño electrónico, la Presentación 2 en las
> semanas 11 y 12, el informe y la sustentación final.

## 20 · Presupuesto (0:15) — L

> El robot, la PC de entrenamiento y la portátil son prestados, y el software es abierto: costo cero. El único
> gasto previsto es la impresión, unos 20 soles estimados.

## 21-22 · Producto final (0:20) — C y L

> *(C, diap. 21)* En el diagrama resaltamos lo que se implementa: todo lo de simulación y la comparación; el robot
> físico queda en gris, como adicional.
> *(L, diap. 22)* Y en la metodología, las etapas uno a siete se hacen en el curso; la ocho es adicional.

## 23 · Conclusiones (0:25) — C

> Cuatro conclusiones. El problema es real y está poco cubierto en el Perú. Ya tenemos la infraestructura
> completa. Con la formulación actual la política aún no iguala a OMPL, con mucha variación entre semillas, pero
> usa cinco veces menos cómputo y deja más holgura. Y lo que sigue es mejorar el muestreo y la recompensa,
> validar con más escenas, diseñar la integración con el E6 y preparar la demostración en vivo. Gracias;
> quedamos atentos a sus preguntas.

## 24 · Referencias (respaldo)

No se expone. Se deja abierta durante las preguntas.

---

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Por qué RL si RRT-Connect ya funciona? | No decimos que sea mejor. La política responde con latencia pequeña y fija; el planificador replanifica con tiempo variable. Medimos cuánta calidad cuesta esa ventaja y hasta dónde llega. |
| Su política tiene 66 % y RRT-Connect 99 %: ¿fracasó? | Es el resultado de la primera formulación. Falla sobre todo con obstáculos grandes (el éxito cae de 1.00 a 0.62 en la mejor semilla). Por eso la siguiente iteración cambia el muestreo de entrenamiento y la recompensa. |
| ¿Por qué solo simulación si tienen el robot? | El objeto de estudio es la política, no la transferencia a hardware. Un robot real introduce holguras y errores de calibración que enmascaran el efecto, y con pocos episodios reales no hay estadística. La política se diseña para el E6 (mismo período de 30 ms y mismos límites). |
| ¿Percepción ideal? | Sí, es un supuesto declarado: los resultados son una cota superior, y se aplica igual a la política y a la línea base. |
| ¿Por qué SAC y no PPO o TD3? | Es fuera de política y reutiliza experiencia (PPO la descarta), y ajusta solo la temperatura (TD3 es más sensible a hiperparámetros). |
| ¿Cómo evitan que la comparación sea injusta? | Mismas 100 escenas, mismo evaluador, mismos límites y tolerancias, política evaluada una sola vez con el modelo elegido en validación aparte. |
| ¿Qué hizo cada uno? | L: celda, modelo, línea base y banco de pruebas. C: entorno, MDP, recompensa y entrenamiento. Ambos: contrato de escenarios, análisis y documentación. |
