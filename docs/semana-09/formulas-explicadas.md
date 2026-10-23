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

**Ejemplo numérico.** Un episodio corto e ilustrativo de 5 pasos (las recompensas son valores de ejemplo, de la
magnitud de los términos del apartado 2): el robot se acerca a la meta, pasa cerca de un obstáculo (castigo de
proximidad), y en el paso 5 llega (+10).

| t | r_t | γᵗ | γᵗ·r_t |
|---|---|---|---|
| 0 | +0.12 | 1.000 | +0.1200 |
| 1 | +0.10 | 0.990 | +0.0990 |
| 2 | −0.50 | 0.980 | −0.4901 |
| 3 | +0.15 | 0.970 | +0.1455 |
| 4 | +10.00 | 0.961 | +9.6060 |
| | | **Retorno G₀** | **9.480** |

- **Suma sin descuento:** 0.12 + 0.10 − 0.50 + 0.15 + 10 = 9.87. El descuento la baja a 9.48, sobre todo porque los
  10 puntos de la meta están 4 pasos adelante: 10·0.99⁴ = 9.61.
- **Forma recursiva (la que usa el código):** se calcula de atrás hacia adelante con G_t = r_t + γ·G_{t+1}.
  G₄ = 10; G₃ = 0.15 + 0.99·10 = 10.05; G₂ = −0.50 + 0.99·10.05 = 9.4495; G₁ = 0.10 + 0.99·9.4495 = 9.455;
  G₀ = 0.12 + 0.99·9.455 = **9.4805**. Es el mismo número. Esta es la ecuación de Bellman,
  Q(s,a) = r + γ·Q(s′,a′), que el crítico de SAC aprende a predecir (`stable_baselines3/sac/sac.py:260`).
- **Por qué importa llegar rápido:** los mismos +10 recibidos en el paso 5 valen 9.61, en el paso 100 valen
  10·0.99⁹⁹ = 3.70 y en el paso 300 (el límite del episodio) valen 10·0.99²⁹⁹ = 0.50. Con γ = 0.99 el agente
  prefiere llegar pronto, aunque el éxito sea el mismo.
- **Qué pasaría con γ = 0:** G₀ = 0.12. El agente solo vería la recompensa inmediata, y nunca aprendería que
  pasar cerca del obstáculo (−0.50) es el precio de llegar (+10).
- **Cuidado al presentar:** el retorno de este ejemplo es solo ilustrativo. Los valores reales de r_t salen de la
  ecuación del apartado 2 y del entorno (`gym_env/entorno.py:124-154`).

### La esperanza E, la recursión y Monte Carlo (cómo se conecta con el código)

Cuatro ideas, en este orden, que juntas explican por qué la fórmula del retorno tiene una **E** y el código no la
calcula en ningún lado.

**1. Qué es el retorno de un episodio y qué es J(π).** Un episodio concreto da **un número**, el retorno
G₀ = r₀ + γ·r₁ + γ²·r₂ + … (el 9.480 del ejemplo). Pero dos episodios con la misma política dan retornos distintos,
porque varían el escenario (el obstáculo se sortea), las acciones (SAC es estocástica y explora) y, en general, la
transición. Un episodio no sirve para juzgar una política: hace falta el retorno **promedio**. Eso es lo que
significa **E_π**: la esperanza (el promedio) de G₀ sobre todos los episodios posibles cuando el robot sigue π.

| Símbolo | Qué es | Ejemplo |
|---|---|---|
| G₀ | retorno de **un** episodio | +9.48 si llega; −10.4 si choca |
| J(π) = E_π[G₀] | retorno **promedio** de la política | cercano a lo que da la media de muchos episodios |
| Q(s,a) = E_π[G_t \| s,a] | retorno promedio **a partir de** un estado y una acción | lo que predice la red crítica |

**2. La recursión de Bellman.** Sacar γ como factor común convierte la suma en una recursión:

$$G_t = r_t + \gamma\,G_{t+1}\qquad\Longrightarrow\qquad Q(s,a)=\mathbb{E}\big[\,r+\gamma\,Q(s',a')\,\big]$$

La primera es una igualdad exacta para un episodio concreto (la comprobaste con los números: 9.4805 de las dos
maneras). La segunda es la misma idea **en valor esperado**: el valor de ahora es la recompensa inmediata más el
valor del paso siguiente, descontado. Por eso no hace falta esperar a que termine el episodio para aprender: basta
un paso `(s, a, r, s')`.

**3. Dónde entra la esperanza en el código: en la pérdida, no en una operación.** En SAC (línea 260 de
`stable_baselines3/sac/sac.py`) cada transición guardada produce **un solo** objetivo:

```
objetivo = r + (1 − done) · γ · Q_objetivo(s', a')
```

Ese número usa el `s'` que de verdad ocurrió y **una** acción `a'` muestreada. No se promedia sobre todos los
`s'` y `a'` posibles; no hay una esperanza calculada. La esperanza aparece al entrenar la red con error cuadrático:

```
critic_loss = 0.5 · mse(Q(s,a), objetivo)
```

El valor que minimiza el error cuadrático es la **media**: si a la misma (s,a) le llegan muchos objetivos
ruidosos, la red converge a su promedio, E[objetivo | s,a]. Es un resultado estadístico estándar. Así que el código
**no calcula** la esperanza: la red la **aprende** viendo muchas muestras. Un caso límite lo aclara: si el entorno
y la política fueran deterministas (mismo `s'` y sin exploración), no habría nada que promediar, E sería un solo
valor y la recursión coincidiría exactamente con la suma de tu ejemplo de 5 pasos.

Tres detalles del mismo objetivo:
- `(1 − done)`: si el episodio termina por éxito o choque, no hay paso siguiente y el término γ·Q(s′) vale 0.
- **Bootstrapping:** el objetivo usa Q(s′,a′) **estimado por la propia red** (la red objetivo), no el retorno real.
  Al comienzo del entrenamiento esa estimación es mala y mejora poco a poco; la igualdad con el retorno solo se
  cumple en el punto al que converge el entrenamiento.
- **Entropía:** SAC resta `ent_coef · log π(a′|s′)` al valor siguiente, para premiar la exploración. Por eso
  maximiza "retorno + entropía" y no exactamente J(π); con la temperatura α → 0 vuelve a ser el retorno normal.

**4. La aproximación de Monte Carlo.** Calcular una esperanza exacta exigiría sumar sobre **todos** los escenarios,
acciones y transiciones posibles (infinitos). El método de Monte Carlo la reemplaza por **la media de muestras
aleatorias**:

$$\mathbb{E}[X]\;\approx\;\frac{1}{N}\sum_{i=1}^{N}x_i\qquad (x_i\ \text{muestras independientes de}\ X)$$

La ley de los grandes números garantiza que, al crecer N, la media muestral tiende a la esperanza verdadera, y el
error baja aproximadamente como 1/√N. Ejemplo clásico, el dado: E[dado] = 3.5. Simulando tiradas al azar, la media
fue 3.40 con 10 tiradas, 3.72 con 100 y 3.501 con 10 000.

En el proyecto Monte Carlo aparece, de forma **explícita o implícita**, en cuatro lugares:

| Dónde | Qué se promedia | ¿Explícito? |
|---|---|---|
| **Evaluación** (100 escenas, CSV de `results/`) | Retornos o éxitos de N episodios: J ≈ (1/N)·Σ G₀⁽ⁱ⁾; el 0.68 de éxito es una media de 100 casos | Sí, es una media en el código |
| **Pérdida del crítico** (`mse_loss`) | El error de las 256 transiciones del lote | Sí, `reduction="mean"` |
| **Objetivo de Bellman** | Una muestra de `s′` y de `a′` por transición; la red promedia al entrenar | Implícito |
| **Término de entropía** | Una muestra de a′ ~ π para estimar E[−log π] | Implícito |

Resumen: la **E** está en la fórmula porque la teoría necesita un valor bien definido aunque el entorno sea
aleatorio; el **código** nunca la calcula, la **aproxima con muestras** (Monte Carlo), y es el error cuadrático el
que hace que lo aprendido sea el promedio y no el ruido de cada muestra. La estimación es ruidosa con pocas
muestras, y por eso se reportan siempre las tres semillas y 100 escenas, y no un solo episodio.

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

### 3.6 Cómo se conectan las seis ecuaciones con el retorno

Las seis ecuaciones están en la diapositiva 14 (cada una es una imagen de `docs/presentacion/p1/img/`). Forman una
cadena: la primera dice **qué se maximiza** y las otras cinco son las piezas para lograrlo. Todas parten del
retorno de la diapositiva 13, J(π) = E_π[Σ γᵗ r].

```
Retorno (diap. 13)   J = E[Σ γᵗ r]
        │  se le suma un premio por entropía
        ▼
(1) Objetivo SAC     J = Σ E[ r + α·H ]                       ← qué se maximiza
        │  recursión de Bellman (G_t = r_t + γ·G_{t+1})
        ▼
(2) Valor objetivo   y = r + γ(1−d)( min Q̄ − α log π )
        │
        ├─► (3) Crítico: minimiza (Q − y)²           ← aprende el retorno con entropía
        ├─► (4) Actor:   minimiza α log π − min Q    ← mejora la política (sube J)
        ├─► (5) α:       mantiene la entropía en −6  ← regula la exploración
        └─► (6) Q̄:       sigue a Q despacio (τ)      ← estabiliza y
```

| # | Imagen de la diapositiva 14 | Cuadro | Relación con el retorno | Dónde está en el código | La E es… |
|---|---|---|---|---|---|
| 1 | `eq_objetivo.png` | Objetivo con entropía | El retorno con un término extra, r + α·H en cada paso; con α = 0 vuelve el retorno normal | No se calcula: es la definición de lo que se maximiza | Definición teórica |
| 2 | `eq_objetivo_suave.png` | Valor objetivo | La recursión de Bellman del retorno, con mínimo de dos críticos y entropía | `sac.py:260` (`target_q_values`) | Una muestra de s′ y de a′ por transición |
| 3 | `eq_critico.png` | Crítico | Hace que Q aprenda el retorno esperado (sin sumar episodios completos) | `critic_loss = 0.5·mse_loss(Q, y)` | Media del lote de 256 (Monte Carlo) |
| 4 | `eq_actor.png` | Actor | Es el paso que **sube J**: elige acciones de Q alto y entropía alta | `actor_loss = (ent_coef·log_prob − min_q).mean()` | Media del lote de 256 (Monte Carlo) |
| 5 | `eq_alfa.png` | Temperatura (H̄ = −6) | Ajusta el peso α de la entropía que aparece en (1) y (2) | `ent_coef_loss`, `ent_coef: auto` en `sac_v0.yaml` | Media del lote de 256 (Monte Carlo) |
| 6 | `eq_objetivo_blando.png` | Redes objetivo (τ = 0.005) | Mantiene quieta la Q̄ que aparece en (2) | `polyak_update` | No tiene esperanza |

Cosas que conviene tener claras:

- **Quién minimiza el error cuadrático:** solo el crítico (3). El actor (4) minimiza otra pérdida, y α (5) otra
  distinta. Las tres son medias sobre el lote de 256 transiciones, es decir, aproximaciones de Monte Carlo de la E.
- **Qué aprende cada red:** el crítico aprende a **predecir el retorno** (con entropía) de una acción; el actor
  aprende a **elegir** acciones que el crítico valora alto. El crítico evalúa y el actor decide.
- **Por qué hay una E en la fórmula 3 aunque el código no la calcule:** el error cuadrático converge a la media
  condicional del objetivo y (apartado "La esperanza E, la recursión y Monte Carlo", §1). La red termina
  representando E[y | s, a].
- **γ en la diapositiva:** la ecuación (1) de la diapositiva omite γ para simplificar; el descuento sí está en (2).
  Si preguntan, es una simplificación de notación, no un cambio de algoritmo.
- **Política estocástica y determinista:** la acción de (4) es a = tanh(μ + σ⊙ε), estocástica en el entrenamiento.
  En todas las evaluaciones del proyecto se usa `deterministic=True`, que toma solo μ (sin ruido), y por eso cada
  escena da el mismo resultado.

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
