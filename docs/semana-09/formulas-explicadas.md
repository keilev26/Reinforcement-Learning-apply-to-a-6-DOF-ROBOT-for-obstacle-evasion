# Las fórmulas del proyecto, explicadas

Para cada ecuación: qué dice, qué significa cada símbolo y **dónde aparece en lo que hicimos** (con los números
reales del proyecto). Sirve para estudiar antes de la exposición y para responder preguntas.

Idea de fondo: un robot que decide cada 30 ms qué articulación mover. No sabemos programar a mano la mejor
decisión para toda celda posible, así que **definimos qué es hacerlo bien (la recompensa) y dejamos que un
algoritmo lo aprenda probando**. Las fórmulas son, en este orden: cómo se plantea el problema, cómo se define
"bien", cómo aprende SAC, cómo se mueve el robot y cómo se mide el resultado.

---

## 1. El problema como proceso de decisión de Markov (MDP)

Un MDP es la tupla (S, A, P, r, γ):

| Símbolo | Significado | En el proyecto |
|---|---|---|
| s ∈ S | estado: lo que ve el agente | vector de **43 números** |
| a ∈ A | acción: lo que decide | **6 números** en [−1, 1] (uno por articulación) |
| P | cómo cambia el estado al actuar | cinemática: q ← q + Δq cada 30 ms |
| r | recompensa: nota inmediata | ecuación del apartado 2 |
| γ | descuento: cuánto importa el futuro | **0.99** |

**Estado (43):** 6 posiciones articulares normalizadas + 6 del incremento anterior + 3 de error de posición del
efector a la meta + 4 de error de orientación (cuaternión) + 6 distancias mínimas (una por eslabón) + 18
direcciones unitarias (3 por eslabón). Los últimos 24 valores son la geometría de los obstáculos vista desde cada
eslabón. Por eso la política **no usa cámara**: recibe distancias calculadas.

**Acción:** Δq = 0.05 · a (rad). Con 30 ms por paso, el máximo es 0.05/0.03 ≈ 1.67 rad/s ≈ 95 °/s por
articulación. Se eligió Δq (incremento articular) y no velocidad cartesiana porque cerca de una singularidad
(apartado 6) una orden cartesiana pediría velocidades articulares enormes.

### Retorno

$$J(\pi)=\mathbb{E}_\pi\Big[\sum_{t=0}^{\infty}\gamma^{t}\,r(s_t,a_t)\Big],\qquad \gamma=0.99$$

Es la suma de todas las recompensas futuras, pero las lejanas pesan menos. La política π es la que hace máxima esa
suma. **Con γ = 0.99, una recompensa a 100 pasos pesa 0.99¹⁰⁰ ≈ 0.37 y a 300 pasos (el límite del episodio)
0.99³⁰⁰ ≈ 0.05.** γ cercano a 1 hace que el agente "piense a largo plazo": rodear un obstáculo cuesta
recompensa ahora y rinde después, y un γ chico no lo aprendería.

---

## 2. La recompensa (qué significa "hacerlo bien")

$$r_t = 10\frac{\Delta d}{L}+5\,\Delta\theta+10\,\Delta\Phi-w_p-w_s-0.01-10\,\mathbb{1}_{\rm col}+10\,\mathbb{1}_{\rm éxito}$$

La recompensa es la **única forma de decirle al agente qué queremos**. Cada término es una intención:

| Término | Qué premia o castiga | Ejemplo numérico |
|---|---|---|
| 10·Δd/L | **Progreso**: acercar el efector a la meta. Δd es lo que se redujo la distancia en este paso; L = 0.427 m es la longitud de la tarea (normaliza) | Acercarse 5 mm: 10·0.005/0.427 = **+0.117** |
| 5·Δθ | **Orientación**: reducir el error angular (la herramienta debe quedar hacia abajo) | Reducir 0.02 rad: +0.10 |
| 10·ΔΦ | **Precisión** (potencial, abajo) | Ver ejemplo: +0.39 |
| −w_p | **Proximidad**: castigo por acercarse a un objeto; w_p = máx(0, 1 − d_min/0.02) | A 1 cm: 1 − 0.5 = **−0.5**; a ≥ 2 cm: 0 |
| −w_s | **Suavidad**: castiga cambios bruscos de Δq; w_s = 0.05·‖(Δq_t − Δq_{t−1})/0.05‖²/6 | Movimiento fluido: ≈ 0 |
| −0.01 | **Tiempo**: cada paso cuesta algo, para no dilatar | 300 pasos = −3 |
| −10·𝟙_col | **Colisión**: 𝟙_col vale 1 si choca (y el episodio termina) | −10 |
| +10·𝟙_éxito | **Éxito**: llegar a ≤ 5 mm y ≤ 0.05 rad sin chocar | +10 |

### El potencial de precisión (Φ)

$$\Phi(d,\theta)=e^{-d/0.02}\;e^{-\theta/0.10},\qquad \Delta\Phi=\Phi_t-\Phi_{t-1}$$

Φ vale 1 cuando el efector está exactamente en la meta (d = 0, θ = 0) y cae rápido al alejarse: con d = 2 cm y
θ = 0.1 rad, Φ = e⁻¹·e⁻¹ ≈ 0.135. Premiar la **diferencia** ΔΦ (y no Φ) es *conformación por potencial*: no
cambia cuál es la mejor política, pero da una señal fuerte justo cerca de la meta, donde el término de progreso es
casi nulo. Ejemplo: pasar de d = 2 cm a d = 1.5 cm con θ = 0.1: Φ sube de 0.135 a 0.174 y 10·ΔΦ = **+0.39**, más
del triple del +0.117 del progreso lineal por 5 mm. Eso es lo que empuja al agente a "terminar bien" y alcanzar la
tolerancia de 5 mm.

**Hipótesis sobre los fallos observados (no demostrada):** casi todos son *tiempo agotado a 3 a 7 cm de la meta*.
Una explicación posible es que, con obstáculos grandes, acercarse al obstáculo cuesta (−w_p) y quedarse quieto solo
cuesta −0.01 por paso, un óptimo local cómodo. Es lo que la versión 2 del plan (penalizar quedarse parado)
quiere comprobar.

---

## 3. Soft Actor-Critic (SAC): cómo aprende

SAC tiene tres redes: un **actor** π_φ (decide la acción) y **dos críticos** Q_θ₁, Q_θ₂ (estiman cuánto vale
tomar una acción en un estado). Todas son redes de 256 × 256 neuronas. Aprende de un **búfer de experiencia**
(1 M de transiciones) con lotes de 256, y puede reutilizar cada experiencia muchas veces (*fuera de política*).

### 3.1 Objetivo con entropía

$$J(\pi)=\sum_t \mathbb{E}\big[r(s_t,a_t)+\alpha\,\mathcal{H}(\pi(\cdot\mid s_t))\big]$$

Maximiza recompensa **más** α veces la entropía H. La entropía mide cuán aleatoria es la política: si siempre
elige igual, H es baja; si reparte probabilidad, H es alta. Sumarla obliga a **explorar** y evita que la política
se encierre pronto en una mala solución. **En el proyecto:** al inicio el brazo se mueve casi al azar; con el
entrenamiento se va volviendo preciso, y α controla cuánto se permite esa aleatoriedad.

### 3.2 Valor objetivo

$$y=r+\gamma(1-d)\Big(\min_i Q_{\bar\theta_i}(s',a')-\alpha\log\pi_\phi(a'\mid s')\Big),\quad a'\sim\pi_\phi(\cdot\mid s')$$

Es "la nota que *debería* tener" tomar la acción a en s: la recompensa inmediata r, más el valor del siguiente
estado. d = 1 si el episodio terminó (entonces no hay futuro). Detalles que importan:

- **min de dos críticos:** un solo crítico tiende a *sobreestimar* valores (creer que una acción es mejor de lo que
  es). Tomar el mínimo de dos independientes lo corrige.
- **−α·log π:** es la bonificación de entropía llevada al futuro.
- **Q̄ (con barra):** redes objetivo, copias lentas de los críticos (apartado 3.5), para que el objetivo no se mueva
  con cada paso y el aprendizaje sea estable.

### 3.3 Pérdida del crítico

$$J_Q(\theta_i)=\mathbb{E}\big[(Q_{\theta_i}(s,a)-y)^2\big]$$

El crítico aprende a acercar su estimación Q a la nota y: es un error cuadrático (regresión). **En el proyecto:**
de cada lote de 256 transiciones (s, a, r, s′) calcula y y ajusta los críticos para que coincidan.

### 3.4 Pérdida del actor

$$J_\pi(\phi)=\mathbb{E}\big[\alpha\log\pi_\phi(a\mid s)-\min_i Q_{\theta_i}(s,a)\big],\qquad a=\tanh(\mu_\phi+\sigma_\phi\odot\varepsilon)$$

El actor se mueve para que sus acciones tengan Q alto (−min Q) y a la vez alta entropía (α log π). La red entrega
una media μ y una desviación σ; la acción es a = tanh(μ + σ·ε), con ε ruido normal (*truco de reparametrización*:
permite derivar a través del muestreo). La **tanh** mantiene a en [−1, 1], que es justo el rango de nuestra acción
(Δq = 0.05·a). Durante la evaluación la política es **determinista** (se usa solo μ), por eso cada escena da el
mismo resultado.

### 3.5 Temperatura automática y redes objetivo

$$J(\alpha)=\mathbb{E}\big[-\alpha(\log\pi_\phi(a\mid s)+\bar{\mathcal{H}})\big],\ \ \bar{\mathcal{H}}=-\dim(\mathcal{A})=-6;\qquad \bar\theta_i\leftarrow\tau\theta_i+(1-\tau)\bar\theta_i,\ \tau=0.005$$

- **α automático:** si la política es demasiado determinista (entropía < −6), α sube y fuerza explorar; si es muy
  aleatoria, α baja. La entropía objetivo −6 es la regla general "menos la dimensión de la acción" (6 articulaciones).
  Esto evita ajustar α a mano, que es una razón para elegir SAC.
- **Actualización suave (τ = 0.005):** cada paso, la red objetivo se acerca solo un 0.5 % a la red real; tarda del
  orden de 1/τ = 200 pasos en seguirla. Es la "inercia" que estabiliza el objetivo y.

**Hiperparámetros del proyecto:** tasa de aprendizaje 3·10⁻⁴, γ = 0.99, lote 256, búfer 10⁶, red 256 × 256, τ =
0.005, 4 entornos en paralelo, 10⁶ pasos por semilla. Los barridos exploratorios (lr 10⁻³, γ = 0.995, τ = 0.01,
red 512 × 512) fueron peores que esta configuración base.

---

## 4. Cinemática y singularidades

### Cinemática directa (Denavit-Hartenberg)

$$T_0^6(q)=\prod_{i=1}^{6}A_i(\theta_i)$$

Cada articulación i aporta una matriz homogénea A_i (4×4) que depende de su ángulo y de cuatro parámetros fijos
(a, α, d, θ₀) del robot. Multiplicarlas da la posición y orientación del efector respecto a la base. **En el
proyecto:** el entorno calcula esto en cada paso para saber dónde está el efector (error a la meta, trayectoria
cartesiana) y para posicionar cada eslabón y medir su distancia a los obstáculos. La cinemática del modelo
corregido es idéntica a la oficial del E6.

### Jacobiano y manipulabilidad

$$\dot x = J(q)\,\dot q,\qquad w(q)=|\det J(q)|$$

J relaciona velocidades articulares con la velocidad del efector. Cuando w → 0 el brazo está en una
**singularidad**: pierde la capacidad de moverse en alguna dirección, y para seguir una velocidad cartesiana
pediría velocidades articulares enormes. En el E6 hay una singularidad de muñeca (J5 cerca de 0). **Consecuencia
de diseño:** por eso la acción son incrementos articulares acotados y no velocidades cartesianas. El mapa de
alcanzabilidad (figura de la diapositiva 15) usa w para mostrar que recoger y depositar están en la zona de buena
manipulabilidad (0.71 y 0.74 del máximo).

---

## 5. Planificación clásica (la línea base)

No hay una ecuación única, pero hay que saber cómo funcionan:

- **RRT-Connect:** crece un árbol desde el inicio y otro desde la meta en el espacio de configuraciones (los 6
  ángulos), eligiendo puntos al azar y extendiéndose hacia ellos si están libres de colisión; cuando los árboles
  se tocan, hay camino. Es *probabilísticamente completo* (si existe camino, la probabilidad de hallarlo tiende a
  1), rápido, pero el camino sale quebrado. **En nuestras medidas:** 296 de 300 intentos, unos 98 ms.
- **LazyPRM\*:** construye un grafo de configuraciones y **pospone** el chequeo de colisión de cada arista hasta que
  una ruta candidata lo necesita; con el criterio asintótico de PRM\* converge a rutas cortas si se le da tiempo
  (usamos hasta 5 s). **En nuestras medidas:** 99 de 100, unos 5 s.
- La colisión se verifica con FCL (mallas de colisión del robot y de la celda).

**Diferencia clave con SAC:** el planificador *busca* un camino nuevo en cada escena (tiempo variable); la política
*evalúa una red ya entrenada* (tiempo casi constante) y **no tiene garantía de completitud**: si la escena es muy
distinta a las de entrenamiento, puede fallar sin aviso.

---

## 6. Métricas y estadística

Para N escenas, con 𝟙_i = 1 si la escena i fue un éxito (meta en tolerancia, **cero colisiones** y antes del
límite):

$$\mathrm{M1}=\frac{1}{N}\sum_{i=1}^{N}\mathbb{1}_i\qquad L_{\rm cart}=\sum_k\lVert p(t_{k+1})-p(t_k)\rVert_2\qquad L_{\rm art}=\sum_k\lVert q(t_{k+1})-q(t_k)\rVert_2$$

$$d_{\min}=\min_k\;\min_j\; d\big(\text{eslabón}_j(t_k),\text{obstáculos}\big)$$

| Métrica | Qué mide | Cómo se calcula aquí |
|---|---|---|
| M1 tasa de éxito | fracción de escenas resueltas | N = 100 escenas de evaluación (también 19 variantes del contrato) |
| M2 colisiones | entradas en contacto, por par (eslabón, objeto) | con histéresis de 5 mm, para no contar rebotes |
| M3 longitud | cuán larga es la trayectoria | L_cart (punta del efector, en m) y L_art (articular, en rad) |
| M4 tiempo | cómputo (suma de inferencias de la política, o tiempo de OMPL) y ejecución | 19.4 ms contra 97.8 ms por episodio |
| M5 distancia mínima | holgura al obstáculo más cercano | 30 mm (política) contra 4 mm (RRT-Connect) |

**Lectura de los resultados:** RRT-Connect gana en éxito (0.99 contra 0.66) porque *busca* hasta encontrar camino;
la política gana en cómputo (≈ 5 veces menos) y en holgura, porque la recompensa la castiga por acercarse a
obstáculos (−w_p) mientras que RRT-Connect solo exige no chocar.

### Prueba de Wilcoxon de rangos con signo (comparación pareada)

Como ambos métodos resuelven **las mismas escenas**, se comparan por pares. Para cada escena i se calcula la
diferencia d_i = métrica_política − métrica_línea base, se ordenan |d_i| de menor a mayor (rangos), se suman los
rangos de las diferencias positivas (W⁺) y de las negativas (W⁻), y el estadístico es el menor de los dos. Si el
método A fuera igual al B, ambas sumas serían parecidas; si una domina, el **valor p** es pequeño.

- **No supone** que las diferencias sean normales (con 100 escenas y métricas sesgadas es lo prudente).
- Se usa **α = 0.05**: p < 0.05 se declara "diferencia significativa".
- Resultados: éxito p = 5·10⁻¹¹ (la línea base es mejor), cómputo y holgura p ≈ 6·10⁻¹⁴ (la política es mejor),
  tiempo de ejecución p = 0.87 (**sin diferencia significativa**).
- Honestidad: p pequeño dice que la diferencia *no es casualidad en estas escenas*, no que el resultado
  generalice a toda celda posible.

### Varias semillas

El entrenamiento tiene aleatoriedad (inicialización, exploración), así que una corrida no basta: **tres semillas**
dieron 0.68, 0.43 y 0.87 de éxito. Por eso reportamos siempre las tres (media 0.66) y no solo la mejor. La
semilla 2 (0.87) se usa para las demostraciones, y se eligió por validación, no mirando las 100 escenas de
evaluación (que se usan una sola vez).

---

## 7. Cómo encaja todo, de punta a punta

1. El **contrato** define la tarea, las tolerancias (5 mm, 0.05 rad), el límite de 300 pasos y las métricas.
2. El **entorno** (cinemática DH + transición q ← q + Δq) simula el E6 cada 30 ms y calcula el estado (43 valores).
3. La **recompensa** (apartado 2) convierte "evitar obstáculos y llegar con precisión" en un número por paso.
4. **SAC** (apartado 3) ajusta actor y críticos con esa recompensa durante 10⁶ pasos.
5. La política entrenada se **evalúa** sin aleatoriedad en 100 escenas fijas, igual que la línea base.
6. Las **métricas y Wilcoxon** (apartado 6) dicen quién gana en qué, y la generalización (escenarios 3, 7 y 8)
   dice dónde sigue siendo necesario el planificador clásico.

## 8. Preguntas de ecuaciones que pueden hacer

| Pregunta | Respuesta |
|---|---|
| ¿Qué es la entropía en SAC y para qué sirve? | Mide cuán aleatoria es la política. Sumarla a la recompensa obliga a explorar y evita quedarse en una solución mediocre; α la regula y se ajusta solo. |
| ¿Por qué dos críticos? | Un solo crítico sobreestima valores; tomar el mínimo de dos independientes lo corrige y estabiliza el entrenamiento. |
| ¿Para qué las redes objetivo y τ? | Para que el valor objetivo y no cambie en cada paso. Se actualizan despacio (τ = 0.005, unos 200 pasos de inercia). |
| ¿Por qué γ = 0.99? | Para que importen las recompensas lejanas; rodear un obstáculo cuesta ahora y rinde después. |
| ¿Por qué la recompensa tiene tantos términos? | Cada uno corrige un fallo observado: progreso (avanzar), orientación y precisión (llegar bien), proximidad (no rozar), suavidad (movimiento realista), tiempo (no dilatar). |
| ¿Qué es el potencial Φ? | Una función que vale 1 en la meta y cae al alejarse; premiar su diferencia no cambia la política óptima pero da señal fuerte cerca de la meta. |
| ¿Por qué acción en Δq y no cartesiana? | Por la singularidad de muñeca: w(q) = \|det J\| → 0 haría pedir velocidades articulares enormes. |
| ¿Por qué Wilcoxon y no una prueba t? | Las diferencias no son normales y las escenas son pareadas; Wilcoxon no supone normalidad. |
| ¿Por qué la política tiene más holgura? | Porque la recompensa castiga la proximidad (−w_p); RRT-Connect solo exige no chocar y pasa rozando (4 mm). |
