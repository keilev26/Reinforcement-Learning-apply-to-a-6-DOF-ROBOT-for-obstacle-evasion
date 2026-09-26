# rl6gdl_e6_description — modelo corregido del DOBOT Magician E6

**Fuente única** del robot para todo el proyecto: PyBullet (entrenamiento), MoveIt 2 y Gazebo
(línea base) leen este mismo URDF, las mismas mallas y la misma lista de pares excluidos de
colisión.

> **Generado. No editar a mano.** Todo sale de `tools/gen_modelo_e6.py`, a partir del URDF
> oficial de Dobot ([DOBOT_6Axis_ROS2_V4](https://github.com/Dobot-Arm/DOBOT_6Axis_ROS2_V4),
> commit `ec201c40`, licencia MIT en `LICENSE.dobot`). Para cambiar algo, se cambia el generador y
> se regenera.

## Contenido

| Ruta | Qué es |
|---|---|
| `urdf/magician_e6.urdf` | Modelo. Raíz `base_link` apoyada en z = 0; marco `tool0` en la brida |
| `meshes/visual/` | Mallas visuales reducidas (~15 000 triángulos por eslabón) |
| `meshes/collision/` | Piezas convexas de colisión: una por cada elemento `<collision>` |
| `config/colisiones_permitidas.yaml` | Pares que **no** se evalúan en colisión. PyBullet y MoveIt deben leer esta lista |
| `config/informe_generacion.yaml` | Números de la generación: masas, exceso de las colisiones, par estimado |

## Correcciones respecto del URDF oficial

| # | Qué | Oficial | Aquí | Base |
|---|---|---|---|---|
| 1 | Masa total | 0.94 kg | **7.2 kg** | Ficha técnica. El CAD usó densidad ≈ 1000 kg/m³ sobre carcasas huecas. Escalado uniforme (× 7.62): conserva los centros de masa. **Estimación** |
| 2 | Velocidad articular | 300 (marcador) | **2.0944 rad/s** | Ficha técnica: 120 °/s |
| 3 | Par (`effort`) | 300 (marcador) | 9.0 / 32.8 / 14.1 / 4.4 / 1.3 / 1.0 N·m | No publicado. Dinámica inversa con carga útil de 0.75 kg, velocidad y aceleración máximas, × 2. **Estimación**, solo para controladores de simulación |
| 4 | Mallas visuales | 368 000 triángulos | ~110 000 | Reducción cuadrática |
| 5 | Mallas de colisión | Las visuales, huecas y abiertas | 16 piezas convexas | Ver abajo |
| 6 | Raíz | `world` → `dummy_link` a +3 cm | `base_link` en z = 0 | La base del robot apoya en la mesa |
| 7 | Gazebo Classic | `gravity=false`, `gazebo_ros2_control` | Eliminado | No existe en Jazzy; el puerto a Gazebo Harmonic va aparte |
| 8 | `tool0` | No existe | +0.019 m sobre `Link6` | Cara superior de la malla de la brida. **Verificar contra el controlador** |

La **cinemática no cambia**: el generador compara la cinemática directa con la del URDF oficial en
200 posturas aleatorias y aborta si difieren más de 1e-6 (error medido: 3e-8).

### Geometría de colisión

PyBullet usa la envolvente convexa de cada malla de un cuerpo móvil; MoveIt (FCL) usa la malla tal
cual. Con las mallas oficiales, **cada motor vería un robot distinto**. Aquí cada pieza de colisión
ya es convexa, así que ambos motores ven exactamente la misma geometría (lo verifica
`test_piezas_de_colision_son_convexas`).

Cada eslabón se rellena (voxelizado a 2 mm) y se descompone en ≤ 4 piezas con V-HACD. La
descomposición se usa solo si reduce en ≥ 3 mm el exceso sobre la malla real frente a la
envolvente única:

| Eslabón | Piezas | Exceso p95, envolvente única | Exceso p95, usado |
|---|---|---|---|
| base_link | 4 | 20.4 mm | **6.8 mm** |
| Link1 | 1 | 17.2 mm | 17.2 mm |
| Link2 | 4 | 25.4 mm | **14.4 mm** |
| Link3 | 4 | 32.5 mm | **10.1 mm** |
| Link4 | 1 | 12.0 mm | 12.0 mm |
| Link5 | 1 | 12.6 mm | 12.6 mm |
| Link6 | 1 | 7.0 mm | 7.0 mm |

El exceso es **conservador**: la geometría de colisión es algo mayor que el robot real. Parte de
ese exceso se debe a que las mallas oficiales están abiertas en las uniones y la colisión las
cierra, como hace físicamente el eslabón vecino.

### Matriz de colisiones permitidas

Se excluyen **solo los 6 pares adyacentes**. Ningún par no adyacente está en contacto en toda
postura, y en la postura de reposo (q = 0) no hay autocolisión. A diferencia del SRDF oficial, no
se excluyen los pares que "nunca" chocan (`Link1-Link4`, `Link4-Link6`): con esta geometría más
gruesa eso no está garantizado, y evaluarlos cuesta poco.

## Uso

```python
import pybullet as p
from gym_env.robot_e6 import cargar_e6, fijar_q, autocolisiones

modelo = cargar_e6(p.connect(p.DIRECT))   # aplica la matriz de colisiones permitidas
fijar_q(modelo, [0, 0.5, 0.7, 0, -1.5, 0])
autocolisiones(modelo)                    # -> lista de pares en contacto
```

Rendimiento en esta máquina (CPU): ~12 000 pasos/s cinemáticos con consulta de distancia a un
obstáculo.

En ROS 2: `package://rl6gdl_e6_description/urdf/magician_e6.urdf`.

## Pendiente

- **`tool0`**: comparar la cinemática directa con `GetPose()` del controlador real en varias
  posturas (herramienta nula). Si difiere, corregir el desfase en el generador.
- **Masas y par**: son estimaciones. Si hacen falta valores reales, pedir a Dobot o identificarlos
  midiendo corriente en el robot.
