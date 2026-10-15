# Presentación del proyecto (15 min)

Archivos en esta carpeta:

| Archivo | Para qué |
|---|---|
| `presentacion.pptx` | 14 diapositivas en 16:9, con notas del orador. Se puede subir a Canva |
| `video_semillas.mp4` | Video de 41 s (1080p) con tres paneles, uno por semilla, a 100 k, 300 k, 600 k y 1 M de pasos |
| `img/` | Ecuaciones de SAC y gráficos como imágenes (PNG) |

## Cómo llevarla a Canva

1. En Canva: **Crear un diseño → Importar archivo** y elegir `presentacion.pptx`.
2. Los textos quedan editables. Las ecuaciones y los gráficos entran como imágenes.
3. En la diapositiva 10, el recuadro gris con el fotograma es un marcador: subir `video_semillas.mp4`
   (Subidos → Subir archivos), arrastrarlo encima y ajustar el tamaño. El video no va incrustado en el
   `.pptx` porque Canva no lo importa de forma fiable.
4. Completar en la diapositiva 1 los nombres completos, el curso y la fecha.

## Tiempos

| # | Diapositiva | Tiempo |
|---|---|---|
| 1 | Título | 0:30 |
| 2 | El problema y la pregunta | 0:50 |
| 3 | El robot, la celda y la tarea | 0:50 |
| 4 | Una misma vara de medir | 1:00 |
| 5 | Línea base clásica (MoveIt 2 + OMPL) | 0:50 |
| 6 | RL como problema de decisión | 1:20 |
| 7 | SAC: recompensa y entropía | 1:00 |
| 8 | SAC: las ecuaciones | 1:30 |
| 9 | Cómo se entrena (semillas y corridas) | 1:30 |
| 10 | Video de las tres semillas | 1:00 |
| 11 | Resultados frente a la línea base | 1:50 |
| 12 | Dónde falla y cómo generaliza | 1:00 |
| 13 | Qué sigue | 0:50 |
| 14 | Conclusiones y preguntas | 0:30 |
| | **Total** | **14:30** |

Quedan 30 s de margen.

## Cifras usadas y su origen

| Cifra | Origen |
|---|---|
| RRT-Connect 296/300, LazyPRM* 99/100, 103 ms y 5043 ms | `results/linea_base_20260929_0025_metricas.csv` |
| SAC `sac_v1`: 0.68, 0.43 y 0.87 en 100 escenas (media 0.66) | `results/politica_sac_v1_s{0,1,2}_1M_pc_evaluacion.csv` |
| Cómputo 19.4 ms contra 97.8 ms, holgura 30 mm contra 4 mm, ejecución p = 0.87 | `python -m evaluation.comparar` de las tres semillas contra RRT-Connect |
| Éxito por tamaño de obstáculo, fallos por tiempo agotado, coincidencia entre semillas | análisis de las 100 escenas de evaluación (semillas 0, 1 y 2) |
| 0 % en los escenarios 3 y 8 y 0-67 % en el 7 | `results/politica_sac_v1_s*_1M_pc_contrato.csv` |
| 3 h 45 min por corrida y 6 h 15 min el núcleo | marcas de tiempo de `training/runs/` (4 corridas a la vez, GTX 1080) |

## Sobre el video

`tools/video_semillas.py` carga, para cada semilla, los modelos guardados a 100 k, 300 k, 600 k y 1 M de pasos
y ejecuta la misma escena de evaluación (E088: cilindro con k = 1.48 en mitad del camino). No es el entrenamiento
en vivo, sino la política que había en cada punto. Se regenera con:

```bash
.venv/bin/python tools/video_semillas.py --escena E088 --salida docs/presentacion/video_semillas.mp4
```

## Ecuaciones de SAC (para el texto del informe)

- Objetivo: J(π) = Σₜ E[ r(sₜ,aₜ) + α·H(π(·|sₜ)) ]
- Valor objetivo: y = r + γ(1−d)( minᵢ Q̄ᵢ(s′,a′) − α·log π(a′|s′) )
- Crítico: J_Q(θᵢ) = E[ (Q_θᵢ(s,a) − y)² ]
- Actor: J_π(φ) = E[ α·log π_φ(a|s) − minᵢ Q_θᵢ(s,a) ], con a = tanh(μ_φ + σ_φ ⊙ ε)
- Temperatura: J(α) = E[ −α( log π(a|s) + H̄ ) ], con H̄ = −dim(A) = −6
- Redes objetivo: θ̄ᵢ ← τθᵢ + (1−τ)θ̄ᵢ, con τ = 0.005
- Recompensa del entorno: r = 10·Δd/L + 5·Δθ + 10·ΔΦ − w_p − w_s − 0.01 − 10·1_col + 10·1_éxito, con
  Φ(d,θ) = exp(−d/0.02)·exp(−θ/0.10)
