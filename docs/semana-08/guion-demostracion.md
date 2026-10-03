# Guion de demostración en vivo

Todo lo que se muestra existe y se ha probado. Duración sugerida: **12-15 min** de demo.
Todos los comandos se lanzan desde la raíz del proyecto, en una terminal normal (zsh o bash).

## Antes de empezar (5 min, la noche anterior y 10 min antes)

- [ ] Cerrar entrenamientos y programas pesados (`uptime` con carga baja).
- [ ] Ensayar **los dos comandos principales una vez** (abajo). La ventana de PyBullet y la de
      Gazebo deben abrir en la pantalla que vas a proyectar.
- [ ] Si usas dos monitores: lanzar cada ventana ya en el monitor correcto.
- [ ] Tener abiertos en otra pestaña `results/figures/1.6_alcanzabilidad_e6.png` y
      `results/figures/1.7_singularidades_e6.png`.
- [ ] Modelo a usar (1 M de pasos, semilla 0):
      `training/runs/sac_v1_s0_20260930_0705/modelo_final.zip`

## Parte 1 — Las escenas (1-2 min)

```bash
.venv/bin/python tools/visor_politica.py --conjunto contrato
```
Muestra la celda, el robot y el obstáculo de cada una de las **19 variantes**. Teclas: **n** siguiente,
**p** anterior, **q** salir. Qué decir: *"Todo sale de un solo contrato: PyBullet, MoveIt y Gazebo
ven exactamente la misma geometría"* (comprobado: diferencias de 10⁻¹⁷).

## Parte 2 — La línea base en Gazebo (3 min)

```bash
tools/demo_gazebo.sh 5 "5 k=2.0"
```
Levanta Gazebo con ventana, el E6, los controladores y MoveIt (15-30 s), planifica con RRT-Connect y
ejecuta recoger → depositar. Imprime error de seguimiento (~0.008 rad), error del TCP (< 1 mm) y estados en
colisión (**0**). Al terminar, **Enter** repite y **q** cierra todo.

Si quieres otra escena: `tools/demo_gazebo.sh 8`, o `tools/demo_gazebo.sh 4 "4 dx=+0.08"`.
El script **rechaza una etiqueta mal escrita** y lista las válidas.

> Es la línea base clásica. La política entrenada con RL **no corre aún en Gazebo/ROS**; no lo
> presentes como si lo hiciera.

## Parte 3 — La política entrenada frente a la línea base (4-5 min)

**3a. Donde funciona.** Verde: el camino de la política. Amarillo: el que planificó RRT-Connect.
```bash
M=training/runs/sac_v1_s0_20260930_0705/modelo_final.zip
.venv/bin/python tools/visor_politica.py --modelo $M --conjunto contrato --escena 2 --linea-base
```
Pulsa **n** para pasar a otras escenas del contrato. Aciertan: 1, 2, 4 dx=+0.08, 4 dy=−0.08,
5 k=0.6, 5 k=1.0 y las tres del 6.

**3b. Escenas del conjunto de evaluación donde acierta con poco error** (en ambas semillas):
```bash
.venv/bin/python tools/visor_politica.py --modelo $M --conjunto evaluacion --escena E060 --linea-base
```
También: `E015`, `E057`, `E066`, `E053`.

**3c. Donde falla (hay que enseñarlo).**
```bash
.venv/bin/python tools/visor_politica.py --modelo $M --conjunto contrato --escena "5 k=2.0" --linea-base
.venv/bin/python tools/visor_politica.py --modelo $M --conjunto contrato --escena 8 --linea-base
.venv/bin/python tools/visor_politica.py --modelo $M --conjunto evaluacion --escena E013 --linea-base
```
`5 k=2.0` es el obstáculo más grande: no llega. El `8` es la prueba de generalización (componentes
que nunca vio): tampoco llega, pero **sin chocar**. `E013` queda a ~40 cm de la meta.

**Mostrar siempre la franja de abajo:** al terminar, el visor escribe ÉXITO, COLISIÓN o TIEMPO
AGOTADO, el error en mm y el tiempo.

## Parte 4 — Los números (2 min), en una diapositiva o en los CSV

| Métrica | Política (2 semillas, 1 M de pasos) | RRT-Connect | Gana |
|---|---|---|---|
| Éxito (conjunto de 100 escenas) | 44 % | 99 % | Línea base |
| Cómputo | 22 ms | 91 ms | Política |
| Holgura con obstáculos | 36 mm | 4 mm | Política |
| Tiempo de ejecución | 2.04 s | 1.96 s | Empate (p = 0.30) |

Más el mapa de alcance (`1.6_...png`) y las singularidades (`1.7_...png`).

## Lo que hay que decir con honestidad

- La política **todavía no supera** a la línea base en éxito: 44 % frente a 99 %.
- Son **2 semillas**; el protocolo pide 3. La tercera y el currículo se detuvieron a 780 000 pasos.
- Los CAD de la celda aún no están: hoy los obstáculos son formas simples.
- Lo sólido: las métricas se calculan con **el mismo código** para ambos métodos, la comparación es
  pareada por escena (Wilcoxon) y los tres motores se verificaron equivalentes.

## Si algo falla en vivo

| Problema | Qué hacer |
|---|---|
| La ventana de PyBullet no recibe teclas | Hacer clic en la ventana primero; las teclas solo funcionan con el foco ahí |
| La política va lenta o a trompicones | `--velocidad 2` la acelera; la física no cambia |
| Gazebo no abre o tarda más de 2 min | `Ctrl+C`; ver `/tmp/demo_gazebo_launch.log`; relanzar. Plan B: mostrar `results/` y los resultados del documento semana 5, sección 3.8 |
| Quedó Gazebo abierto de un intento anterior | `pkill -f "^gz sim"` y `pkill -x move_group`, y relanzar |
| Una escena se muestra distinta de lo esperado | El visor usa la etiqueta exacta; las 19 se listan con `--conjunto contrato` |

## Referencia rápida del visor

`tools/visor_politica.py --help`. Opciones útiles: `--conjunto {contrato,evaluacion,entrenamiento}`,
`--escena <etiqueta>`, `--linea-base`, `--velocidad 2`, `--auto 5` (avanza solo cada 5 s tras
terminar). Teclas: **n/→** siguiente, **p/←** anterior, **r** repetir, **espacio** pausa, **q** salir.
