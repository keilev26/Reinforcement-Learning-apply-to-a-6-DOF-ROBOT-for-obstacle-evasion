# Plan: entrenar en una VM en la nube

Objetivo: correr más corridas a la vez y más rápidas que en la PC potente. Los precios salen de agregadores de
terceros (Holori, DevZero), no de las páginas oficiales: **confirmarlos antes de contratar**.

## Punto de partida medido

- PC potente: **8 núcleos, 64 GB de RAM**. 4 corridas en paralelo dieron ≈75 pasos/s cada una (5 M de pasos
  en ≈18 h); con 2 corridas, ≈109 pasos/s cada una. Es decir, **≈2 núcleos por corrida**: la simulación casi no
  carga la CPU y lo que pesa es el hilo de entrenamiento de cada corrida.
- La actualización de la red es secuencial: una corrida no se acelera con más núcleos, solo con más núcleos
  libres (menos competencia) o con un reloj más rápido.
- GPU: no ayuda con una red 256×256 y lote 256 (medido en el portátil: 181 s en CPU frente a 183 s en GPU por
  20 000 pasos; con 2 corridas la GPU es 2.7 veces más lenta). No se sabe en qué dispositivo corrieron los
  barridos de la PC potente: comprobar con `nvidia-smi` o `training/benchmark_pc.py`. Contratar solo CPU.
- Una corrida interrumpida **se repite desde cero** (el búfer de experiencia no se guarda).

## Estimación para la nube (extrapolada, no medida en la VM)

| Reparto | Pasos/s por corrida | 5 M de pasos |
|---|---|---|
| 2 núcleos por corrida (como la PC) | ≈75 | ≈18 h |
| 4 núcleos por corrida | ≈109 | ≈13 h |

| Instancia | Núcleos | Precio | Corridas con 4 núcleos | Costo de ≈13 h |
|---|---|---|---|---|
| **AWS c8a.8xlarge** (AMD, 1 vCPU = 1 núcleo) | 32 | ≈1.72 USD/h | **8** | **≈22 USD** |
| AWS c8a.16xlarge | 64 | ≈3.45 USD/h | 16 | ≈45 USD |
| GCP c4d-standard-32 (AMD) | 32 | ≈1.5 USD/h (spot ≈0.6) | 8 | ≈20 USD |
| Hetzner AX162 (EPYC 9454P) | 48 núcleos / 96 hilos | 199 EUR/mes + 79 EUR de alta | 12 | (mensual) |

- Memoria: ≈1.5 GB por corrida (estimado), no limita.
- Chips Arm (Graviton, Axion): más baratos, pero sin probar PyBullet y PyTorch ahí; no usarlos sin prueba.
- **Spot:** la tercera parte del precio, pero una interrupción mata la corrida. Antes hay que implementar el
  guardado del búfer y la reanudación.
- **Cuota de AWS:** las cuentas nuevas suelen tener un límite bajo de vCPU y hay que pedir aumento (horas o
  días). Pedirlo antes (regla general, sin confirmar para esta cuenta).
- Créditos de estudiante posibles: Azure for Students (100 USD, 12 meses) y DigitalOcean (200 USD) vía GitHub
  Student Pack. No se sabe si el correo `@uni.pe` se verifica.

## Recomendación

1. Pedir la cuota de AWS (o activar los créditos de estudiante).
2. Levantar una **c8a.8xlarge** con Ubuntu y seguir `docs/semana-08/guia-pc-nueva.md` (clonar, `venv`,
   `requirements-entrenamiento.txt`, `pytest`, solo CPU).
3. Correr `training/benchmark_pc.py` (≈8 min, < 1 USD) y decidir las corridas en paralelo con el dato medido.
4. Lanzar un barrido de **8 corridas**:
   - `sac_v1_5m` semillas 1, 2, 3, 4 (el control),
   - `sac_v2` semillas 3 y 4,
   - 2 plazas para `sac_v3` (muestreo de obstáculos grandes) si se decide probarlo, avisando antes a Leonardo
     porque cambia el contrato compartido.
5. Al terminar: `rsync` de `training/runs/` a la PC, apagar la instancia (cobra por hora), evaluar cada
   `mejor.zip` una sola vez en las 100 escenas de evaluación y en el contrato.

## Pendiente de decidir

- Proveedor (AWS, GCP, Hetzner o créditos de estudiante).
- Si vale la pena implementar guardado de búfer y reanudación para poder usar spot.
- Qué corridas concretas llevan las 8 plazas.
