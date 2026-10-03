# Análisis de pares de las trayectorias (paquete 2.1, versión preliminar)

**Herramienta:** `tools/analisis_pares.py` · **Datos:** `results/analisis_pares_e6.yaml`

## Pregunta

El entorno de entrenamiento es cinemático (`q ← q + Δq`): no simula fuerzas y **no impone ningún
límite de par**. ¿Podría la política exigir al robot real un par que este no pueda dar?

## Qué se limita hoy

| Magnitud | ¿Se limita? | Cómo |
|---|---|---|
| Posición articular | Sí | Rangos de la ficha técnica |
| Velocidad | Sí | Δq ≤ 0.05 rad por paso = 1.67 rad/s, el 80 % de 2.0944 rad/s |
| Aceleración | Sí | 4.72 rad/s², igual que la línea base (`metricas.yaml` 2.1) |
| Par | No | Ningún código lo aplica ni lo comprueba |
| Sacudida (jerk) | No | La aceleración puede invertirse de un paso al siguiente |

Los campos `effort` del URDF (9.0, 32.8, 14.1, 4.4, 1.3 y 1.0 N·m) son **estimaciones**, no datos del
fabricante, que no publica el par. Se obtuvieron como el doble del peor caso por dinámica inversa, a
velocidad y aceleración máximas simultáneas, con una carga de 0.75 kg (`tools/gen_modelo_e6.py`).

## Método

Dinámica inversa de PyBullet (`calculateInverseDynamics`) con gravedad y 0.75 kg añadidos en Link6, la
carga útil máxima. Velocidad y aceleración se obtienen por diferencias finitas de la trayectoria cada
30 ms. Se aplica a:

- la **política SAC** (1 M de pasos, semilla 0), en las 19 variantes del contrato;
- los **planes exitosos de RRT-Connect** de esas mismas variantes, remuestreados a 30 ms.

## Resultados

| N·m | J1 | J2 | J3 | J4 | J5 | J6 |
|---|---|---|---|---|---|---|
| Límite estimado en el URDF | 9.0 | 32.8 | 14.1 | 4.4 | 1.3 | 1.0 |
| **Política SAC**, par máximo | 1.18 | 8.75 | 6.24 | 1.82 | 0.41 | 0.02 |
| fracción del límite | 13 % | 27 % | 44 % | 41 % | 31 % | 2 % |
| **RRT-Connect**, par máximo | 1.30 | 9.66 | 5.98 | 1.90 | 0.42 | 0.02 |
| fracción del límite | 14 % | 29 % | 42 % | 43 % | 32 % | 2 % |
| Solo gravedad, quieto | 0.00 | 7.48 | 4.19 | 1.43 | 0.02 | 0.00 |

- Ninguna articulación supera el **44 %** del límite estimado. Como ese límite es el doble del peor
  caso teórico, J3 y J4 son las más cercanas, con el 88 % y el 82 % del peor caso.
- La **política no exige más par que el planificador**: ambos respetan los mismos límites de velocidad
  y aceleración, y los picos son casi iguales.
- **La gravedad domina**: en J2 aporta 7.48 N·m de un pico de 8.75. Moverse rápido añade poco.

## Límites de esta medición

1. La capacidad real de los motores no se conoce: el margen de 2× es una suposición.
2. Las masas son estimaciones: se escalaron todas por el mismo factor (7.62) hasta los 7.2 kg de la
   ficha. El reparto real puede ser distinto.
3. No se modelan fricción, juego en los engranajes, cables ni calentamiento.
4. La carga de 0.75 kg es la máxima; en la simulación el efector pesa 0.1 kg.
5. La sacudida no está acotada: la política puede invertir la aceleración en pasos consecutivos, lo
   que en un robot real puede producir vibraciones aunque el par de pico sea aceptable.
6. Es una sola semilla, y las trayectorias son las de las 19 variantes, no las de las 100 escenas.

## Cómo explicarlo

> El entrenamiento es cinemático y no impone un límite de par. Verificamos con dinámica inversa que
> los movimientos de la política exigen un par similar al del planificador, dentro de lo estimado para
> el E6. El par real del fabricante no está publicado y las masas son estimadas; la validación
> definitiva es la prueba en el robot real, que es trabajo adicional.

## Reproducir

```bash
.venv/bin/python tools/analisis_pares.py
.venv/bin/python tools/analisis_pares.py --modelo <otro modelo.zip> --carga 0.1
```

## Trabajo futuro

Penalizar la sacudida en la recompensa y repetir el análisis con las 100 escenas de evaluación y con
las tres semillas.
