# Guía: entrenar en una computadora nueva (Ubuntu 24.04, sin nada instalado)

Todos los comandos se escriben en una terminal normal, en este orden. Probados en Ubuntu 24.04 con
Python 3.12, el mismo sistema que el portátil de desarrollo. Tiempo de preparación: 30-60 minutos
(descargas y compilación de `pybullet`).

## 0. Qué necesitas

- Ubuntu 24.04, conexión a internet y espacio de sobra en disco.
- Una cuenta de GitHub con acceso al repositorio.
- No se sabe si la PC tiene GPU: el paso 2 lo detecta y decide qué instalar. Sin GPU todo funciona igual, en CPU.

## Qué NO hace falta en la PC nueva

- **ROS 2, MoveIt y Gazebo:** solo se usan para la línea base de planificadores y la demo. Entrenar y evaluar la política no los necesita.
- **Los STL de la celda (`cad/`) y los mundos `.sdf` de `cad/exportados/mundos/`:** son solo visuales. El entrenamiento usa las primitivas del contrato (caja, cilindro, esfera). Los `.sdf` se regeneran con `tools/exportar_escenarios.py` si alguna vez se quieren.
- **La línea base:** ya está medida y versionada en `results/linea_base_evaluacion_20260930_0648_metricas.csv`. Llega con el `git clone`.
- **`training/runs/` y los modelos `.zip`:** no están en git. La PC nueva entrena desde cero.

## 1. Sistema y herramientas base

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git build-essential cmake python3 python3-venv python3-dev python3-pip tmux htop curl
python3 --version
```

La versión de Python debe ser **3.12.x**. `build-essential` y `python3-dev` hacen falta porque `pybullet`
se compila al instalarlo. `tmux` permite dejar el entrenamiento corriendo aunque se cierre la terminal.

## 2. Detectar la GPU

```bash
lspci | grep -i -E 'nvidia|vga|3d'
```

- Si aparece una **NVIDIA**: instalar el driver y reiniciar (abajo).
- Si no aparece ninguna NVIDIA (solo Intel/AMD o nada): **saltar al paso 3** y usar la opción `cpu` en el paso 4.

```bash
ubuntu-drivers devices
sudo ubuntu-drivers autoinstall
sudo reboot
```

Después de reiniciar:

```bash
nvidia-smi
```

Debe mostrar el nombre de la GPU y una versión de driver. Para el PyTorch con **CUDA 13.0** del paso 4 el
driver debe ser **580 o superior**; con uno anterior, usar la variante `cu126` indicada allí.

## 3. Git y descarga del proyecto

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu_correo@uni.pe"
git config --global pull.rebase true
ssh-keygen -t ed25519 -C "tu_correo@uni.pe"
cat ~/.ssh/id_ed25519.pub
```

Copiar la línea que imprime y añadirla en GitHub: **Settings → SSH and GPG keys → New SSH key**. Después:

```bash
ssh -T git@github.com
git clone git@github.com:keilev26/Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion.git ~/proyecto
cd ~/proyecto
git log --oneline -n 3
```

Sin SSH, también se puede con HTTPS y un token personal:
`git clone https://github.com/keilev26/Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion.git ~/proyecto`.

## 4. Entorno de Python y dependencias

El **orden importa**: PyTorch primero. Si se instalan antes las demás dependencias, `stable-baselines3`
descarga una versión de PyTorch que no se eligió.

```bash
cd ~/proyecto
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip wheel
```

Elegir **una** de estas tres líneas para PyTorch:

```bash
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu130
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu126
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cpu
```

La primera es para GPU con driver 580 o superior, la segunda para un driver anterior y la tercera si no
hay GPU. Después, el resto de dependencias (tarda unos minutos porque compila `pybullet`):

```bash
pip install -r requirements-entrenamiento.txt
```

## 5. Comprobar que todo funciona

```bash
python -c "import torch, pybullet, stable_baselines3, gymnasium; print('torch', torch.__version__, '| GPU:', torch.cuda.is_available())"
python -m pytest -q
```

La primera línea debe decir `GPU: True` si se instaló la versión con CUDA. La segunda debe terminar con
**`91 passed`**. Si algo falla, no seguir: copiar el error y resolverlo antes de entrenar.

## 6. Medir qué configuración conviene en esta máquina

No usar la computadora mientras corre (mide rendimiento). Tarda unos 5-8 minutos.

```bash
python -m training.benchmark_pc
```

Deja `results/benchmark_pc_<equipo>_<fecha>.yaml`. De la sección `recomendacion`, anotar:

- `dispositivo_para_la_red_base`: `cpu` o `cuda`;
- `corridas_en_paralelo`: cuántas corridas lanzar a la vez;
- `horas_para_el_barrido_nucleo_6_corridas`: el tiempo estimado del núcleo.

Los barridos usan `dispositivo: auto`, que elige la GPU si existe. Si el benchmark recomienda `cpu` para
la red base, añadir `--dispositivo cpu` al lanzar el barrido.

## 7. Prueba corta de entrenamiento (unos 5 minutos)

```bash
python -m training.entrenar_sac --config sac_v1 --semilla 99 --pasos 20000 --etiqueta prueba
ls training/runs/sac_v1_prueba_s99_*
```

Debe listar `mejor.zip`, `validacion.csv`, `modelo_final.zip` y `config.yaml`. Después, borrar la prueba:

```bash
rm -rf training/runs/sac_v1_prueba_s99_*
```

## 8. Entrenar

Abrir una sesión de `tmux` para que el entrenamiento siga aunque se cierre la terminal:

```bash
tmux new -s entrenamiento
cd ~/proyecto && source .venv/bin/activate
```

**Un solo modelo** (1 M de pasos, una semilla):

```bash
python -m training.entrenar_sac --config sac_v1 --semilla 0 --pasos 1000000
```

**Varias corridas a la vez** (lo recomendado). Primero ver qué comandos lanzaría, sin ejecutarlos:

```bash
python -m training.lanzar_barrido training/barridos/exploratorio.yaml --simular
```

y después lanzar de verdad, con el número de corridas en paralelo que dijo el benchmark:

```bash
python -m training.lanzar_barrido training/barridos/exploratorio.yaml --paralelo 2
```

Orden recomendado:

| Barrido | Corridas | Para qué |
|---|---|---|
| `exploratorio.yaml` | 8 de 300 000 pasos | Orientarse: comparar hiperparámetros antes de gastar horas |
| `nucleo.yaml` | 6 de 1 M de pasos | **Las 3 semillas del protocolo**, con `sac_v1` y `sac_v1c` |
| `extension.yaml` | 4 de 1 M de pasos | Semillas 3 y 4, si sobra tiempo |

Para dejarlo corriendo y salir de la sesión: **Ctrl+b**, luego **d**. Para volver:

```bash
tmux attach -t entrenamiento
```

Si el barrido se interrumpe, volver a lanzar **el mismo comando**: omite las corridas ya completas.

## 9. Ver cómo va

```bash
python -m training.lanzar_barrido training/barridos/nucleo.yaml --resumen
tail -f training/runs/barridos/nucleo/*.log
htop
nvidia-smi -l 5
```

`--resumen` muestra, por corrida, el estado y el mejor punto según la validación. `htop` muestra la carga de
la CPU y `nvidia-smi -l 5` la de la GPU, cada 5 segundos (salir con Ctrl+C).

## 10. Evaluar y comparar al terminar

Cada corrida deja `mejor.zip` (el mejor punto según validación) y `modelo_final.zip`. La evaluación en las
100 escenas se hace **una sola vez por modelo elegido**:

```bash
python -m evaluation.evaluar_politica training/runs/<corrida>/mejor.zip --conjunto evaluacion
python -m evaluation.evaluar_politica training/runs/<corrida>/mejor.zip --conjunto contrato
```

Con las tres semillas, la comparación con la línea base:

```bash
python -m evaluation.comparar results/linea_base_evaluacion_20260930_0648_metricas.csv --planner RRTConnect \
    training/runs/<corrida_s0>/mejor_metricas_evaluacion.csv \
    training/runs/<corrida_s1>/mejor_metricas_evaluacion.csv \
    training/runs/<corrida_s2>/mejor_metricas_evaluacion.csv
```

## 11. Traer los resultados al portátil

`training/runs/` no se sube a git. Para los modelos y registros, desde el **portátil**:

```bash
rsync -av --include='*/' --include='mejor.*' --include='modelo_final.zip' --include='*.csv' --include='*.json' \
    --include='config.yaml' --exclude='*' usuario@IP_DE_LA_PC:~/proyecto/training/runs/ \
    "/home/calebcamargo/UNI/10mo_CICLO/PROYECTO MECATRONICO/training/runs/"
```

Para versionar los resultados, **en la PC nueva**:

```bash
cp training/runs/<corrida>/mejor_metricas_evaluacion.csv results/politica_<config>_s<semilla>_mejor_evaluacion.csv
cp training/runs/<corrida>/validacion.csv results/validacion_<config>_s<semilla>.csv
git add results
git commit -m "Resultados del entrenamiento en la PC nueva"
git pull --rebase origin main
git push origin main
```

## 12. Problemas frecuentes

| Síntoma | Qué hacer |
|---|---|
| `pip install` falla al compilar `pybullet` | Comprobar `sudo apt install build-essential python3-dev` |
| `No space left on device` | Revisar con `df -h`; si la raíz se llena, `export TMPDIR=<carpeta en otra partición>` y `pip install --no-cache-dir ...` |
| `nvidia-smi` falla tras actualizar el kernel | `sudo dkms autoinstall && sudo modprobe nvidia` |
| `torch.cuda.is_available()` da `False` | El driver no está activo o se instaló PyTorch sin CUDA: repetir los pasos 2 y 4 |
| `ModuleNotFoundError` | Olvidaste `source .venv/bin/activate` en esta terminal |
| Una corrida se cortó a mitad | Relanzar el mismo barrido; o continuar desde un punto: `--desde training/runs/<corrida>/modelo_<paso>.zip` |
| Se cerró la terminal y se detuvo el entrenamiento | Se lanzó fuera de `tmux`; repetir dentro de `tmux` |

## Resumen de comandos mínimos

```bash
sudo apt update && sudo apt install -y git build-essential cmake python3 python3-venv python3-dev python3-pip tmux htop curl
git clone git@github.com:keilev26/Reinforcement-Learning-apply-to-a-6-DOF-ROBOT-for-obstacle-evasion.git ~/proyecto && cd ~/proyecto
python3 -m venv .venv && source .venv/bin/activate && python -m pip install --upgrade pip wheel
pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu130
pip install -r requirements-entrenamiento.txt
python -m pytest -q
python -m training.benchmark_pc
tmux new -s entrenamiento
python -m training.lanzar_barrido training/barridos/nucleo.yaml --paralelo 2
```
