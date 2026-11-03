# Entrenamiento `sac_v3` (kit de obstáculos y pares recoger/depositar, ≈ 72 h)

Todo está preparado y probado en corto; **el entrenamiento largo no se ha lanzado**. Se lanza en la PC potente.

## 1. Qué cambia respecto a `sac_v2`

| Cambio | Dónde | Efecto |
|---|---|---|
| Sin castigo por quedarse quieto | `sac_v3.yaml` (base `sac_v1`) | Recompensa v1; el castigo no ayudó en `sac_v2` |
| Obstáculos del kit físico | `gym_env/kit.py`, `entorno.py` (`muestreo: kit`) | Cada episodio sortea 1-6 piezas de las 22 del kit (P01-P08, R01-R09 y las altas T01-T05, de 300 a 450 mm) |
| Pares recoger/depositar | `entorno.py` (`pares`), `shared_scenarios/pares_kit.yaml` | En `sac_v3p` cada episodio sortea un par entre N0, N1, N2, N3 y N7 |
| 16 M de pasos | `sac_v3.yaml` | Para dar cabida a ≈ 72 h |
| Validación del kit cada 100 000 pasos | `kit_validacion*.yaml` | 200 escenas del mismo muestreo |

Sin tocar: red 256×256, lr 3e-4, γ = 0.99, τ = 0.005, lote 256, búfer de 1 M, 4 entornos por corrida y el contrato compartido (`escenarios.yaml` no cambió; los archivos nuevos solo se añaden).

### Muestreo de obstáculos (`gym_env.kit.muestrear`)
- Piezas con su envolvente (caja o cilindro), igual que el contrato trata a los obstáculos.
- Posición en la rejilla M6 (centros en 25 mod 50 mm), a ≤ 520 mm de la base, giro 0°/90°/180°/270°.
- Nunca sobre el CNC, la bandeja ni la base, ni solapadas entre sí.
- Las piezas de más de 200 mm no tapan los pasillos de la base a recoger y a depositar (ancho 220 mm).
- Número de piezas: 1-6 con probabilidades 0.20/0.20/0.20/0.15/0.15/0.10.
- Cada escena debe tener cinemática inversa libre en recoger y depositar; si no, se vuelve a sortear.
- **No se sortean** portales, filas de muros ni vigas elevadas: esas composiciones solo están en la evaluación.

### Pares
- La observación normaliza el error a la meta con la distancia nominal (424 mm), así que sigue en metros para cualquier par; la recompensa de progreso sí usa la distancia del par.
- Vistos en el entrenamiento de `sac_v3p`: N0, N1, N2, N3, N7. No vistos (solo evaluación): N4, N9, N5, N6, N10.

## 2. Corridas (`training/barridos/v3_72h.yaml`)

| Corrida | Config | Semilla | Para qué |
|---|---|---|---|
| 1-2 | `sac_v3` | 0, 1 | Kit de obstáculos con el par nominal |
| 3-4 | `sac_v3p` | 0, 1 | Lo mismo y además pares sorteados |

La diferencia entre las dos configuraciones responde si variar el par ayuda o perjudica. Con dos semillas por brazo es una respuesta indicativa, no definitiva: en `sac_v1` la variación entre semillas llegó a 0.44.

## 3. Conjuntos de escenas (`shared_scenarios/`)

| Archivo | Escenas | Uso |
|---|---|---|
| `kit_evaluacion.yaml` | 196 | Evaluación, una sola vez por modelo |
| `kit_validacion.yaml` | 199 | Elegir `mejor.zip` en `sac_v3` |
| `kit_validacion_pares.yaml` | 200 | Elegir `mejor.zip` en `sac_v3p` |

Composición de `kit_evaluacion.yaml`:

| Grupo | Escenas | Qué es |
|---|---|---|
| `S` | 22 | Las 22 combinaciones A-V del kit con el par nominal |
| `SP` | 44 | Las mismas con un par visto y otro no visto |
| `R` | 80 | Sorteo del muestreo, par nominal |
| `RPv` | 25 | Sorteo con par visto |
| `RPn` | 25 | Sorteo con par no visto |

- Todas las escenas se comprobaron con un RRT-Connect propio (no MoveIt/OMPL) con 5 s de límite; las que no tenían solución se descartaron.
- Las validaciones no repiten ninguna escena de la evaluación (comprobado en `test_kit.py`).
- Los sorteos son de la misma distribución del entrenamiento: con pocas piezas puede coincidir una escena exacta. Lo no visto de verdad son las combinaciones estructuradas, que el sorteo nunca produce, y los pares no vistos.
- Las 100 escenas heredadas (`evaluacion.yaml`) se siguen usando para comparar con `sac_v1`/`sac_v2`.
- **Pendiente con Leonardo:** repetir RRT-Connect y LazyPRM\* en MoveIt sobre `kit_evaluacion.yaml` (con los pares) y exportar los mundos a Gazebo.

## 4. Duración

| Concepto | Valor |
|---|---|
| Ritmo medido de `sac_v2` (4 corridas en paralelo en la PC) | 3.8 h por millón de pasos, con validación incluida |
| Costo extra del entorno con el kit | de 931 a 475 pasos/s del entorno solo (medido en el portátil): ≈ +1 ms por paso, ≈ +4 % del paso completo |
| Validación de 200 escenas del kit | ≈ 150 s cada 100 000 pasos (estimada, 0.75 s por escena) → ≈ +0.4 h por millón |
| **Total estimado** | ≈ 4.4 h por millón → 16 M ≈ **70 h** |

**No está medido en la PC con esta configuración.** Revisar a la hora de lanzar: a ≈ 70 pasos/s cada fila de `validacion.csv` (cada 100 000 pasos) debe salir cada ≈ 26 min; si tarda más de ≈ 30 min, el barrido pasará de 72 h. Las corridas guardan `mejor.zip` y un punto de control cada 500 000 pasos, así que se puede detener antes y evaluar lo que haya (como ocurrió con `sac_v2`). La corrida no se reanuda: el búfer no se guarda.

## 5. Cómo lanzar en la PC potente

```bash
git pull
.venv/bin/python -m pytest -q
.venv/bin/python -m training.lanzar_barrido training/barridos/v3_72h.yaml --simular
nohup systemd-inhibit --what=sleep:idle .venv/bin/python -m training.lanzar_barrido training/barridos/v3_72h.yaml > barrido_v3.log 2>&1 &
```

Comprobar a los 30-60 minutos:

```bash
.venv/bin/python -m training.lanzar_barrido training/barridos/v3_72h.yaml --resumen
tail -n 3 training/runs/sac_v3_s0_*/validacion.csv
```

## 6. Qué mirar al terminar

```bash
for r in sac_v3_s0 sac_v3_s1 sac_v3p_s0 sac_v3p_s1; do
  m=$(ls -d training/runs/${r}_2* | tail -1)/mejor.zip
  .venv/bin/python -m evaluation.evaluar_politica $m --archivo shared_scenarios/kit_evaluacion.yaml
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto evaluacion
  .venv/bin/python -m evaluation.evaluar_politica $m --conjunto contrato
done
.venv/bin/python -m tools.resumen_kit training/runs/sac_v3_s*_2*/mejor_metricas_kit_evaluacion.csv training/runs/sac_v3p_s*_2*/mejor_metricas_kit_evaluacion.csv
```

1. Éxito por grupo (`S`, `SP`, `R`, `RPv`, `RPn`) y por brazo. Lo que se espera: `R` ≈ el de la validación; `S` menor (composiciones nunca vistas); `RPn` menor en `sac_v3p` que `RPv`, y `sac_v3` con peor resultado en todos los pares distintos del nominal.
2. Comparar con `sac_v2`/control en las 100 escenas heredadas, para saber si ampliar el muestreo costó éxito en lo que ya se resolvía.
3. Comparar con el RRT-Connect propio sobre `kit_evaluacion.yaml` y, cuando Leonardo los tenga, con MoveIt/OMPL.

## 7. Qué no se hizo

- No se entrenó con las combinaciones estructuradas, para poder medir la generalización.
- No se evaluó ningún modelo con estos conjuntos (no hay modelo entrenado en este contrato).
- La escena del kit es una envolvente por pieza (caja o cilindro), no la malla del STEP.
- El muro de 1.60 m no existe en el kit: sigue solo en las escenas de demostración.

## 8. Verificación hecha

- Pruebas: 9 nuevas en `gym_env/tests/test_kit.py` (muestreo reproducible y sin conflictos, pares, conjuntos sin solape, configuraciones) y las 94 anteriores, todas aprobadas; el entorno por defecto no cambia.
- Prueba de humo en el portátil (CPU): 6 000 pasos de `sac_v3p` y 4 000 de `sac_v3`, con la validación de 200 escenas del kit corriendo dos veces y una vez, y `mejor.zip`/`modelo_final.zip` escritos. El éxito 0 es lo esperado con tan pocos pasos; no sirve para medir ritmo.
- `evaluar_politica --archivo shared_scenarios/kit_evaluacion.yaml` evaluó las 196 escenas con pares en 94 s con un modelo sin entrenar, y `tools/resumen_kit.py` las agrupó bien.
- Las mallas de los renders se generan con `tools/convertir_step.py`, que necesita `cadquery` y `trimesh` en un entorno aparte; el entrenamiento no las usa.
