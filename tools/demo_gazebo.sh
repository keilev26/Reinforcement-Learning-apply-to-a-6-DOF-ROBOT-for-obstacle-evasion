#!/usr/bin/env bash
# Demostración en vivo de la línea base (MoveIt + RRT-Connect) ejecutando en Gazebo Harmonic.
#
# Un solo comando: valida la escena, levanta Gazebo con ventana + el E6 + controladores + MoveIt,
# espera a que todo esté listo, ejecuta recoger -> depositar y mide. Deja Gazebo abierto para
# repetir o para enseñar la escena. Al salir cierra TODO (grupo de procesos), sin restos.
#
# Uso:   tools/demo_gazebo.sh <escenario> [variante]
#        tools/demo_gazebo.sh 2
#        tools/demo_gazebo.sh 5 "5 k=2.0"
#        tools/demo_gazebo.sh 8
# Variantes válidas:  .venv/bin/python tools/visor_politica.py --conjunto contrato (lista las 19)
#
# Es la línea base clásica: la política entrenada con RL todavía NO corre en Gazebo/ROS
# (para verla en movimiento, usar tools/visor_politica.py).
set -u
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESC="${1:-}"; VAR="${2:-}"
if [[ -z "$ESC" ]]; then sed -n '2,15p' "$0"; exit 1; fi
LOG="${TMPDIR:-/tmp}/demo_gazebo_launch.log"

# 1. Validar la etiqueta ANTES de lanzar: el launch usa la primera variante si se escribe mal
"$RAIZ/.venv/bin/python" - "$ESC" "$VAR" "$RAIZ" <<'EOF' || exit 1
import sys
sys.path.insert(0, sys.argv[3] + "/shared_scenarios")
import contrato
C = contrato.cargar()
esc, var = int(sys.argv[1]), sys.argv[2]
if esc not in C["escenarios"]:
    sys.exit(f"escenario {esc} no existe: {list(C['escenarios'])}")
etiquetas = [et for et, _ in contrato.variantes(C, esc)]
if var and var not in etiquetas:
    sys.exit(f"variante '{var}' no existe en el escenario {esc}. Válidas: {etiquetas}")
print(f"escena: {var or etiquetas[0]}  ({C['escenarios'][esc]['nombre']})")
EOF

# 2. Entorno de ROS (bash; el workspace ya está compilado)
cd "$RAIZ/ros2_ws" || exit 1
# shellcheck disable=SC1091
set +u    # los setup.bash de ROS usan variables sin definir
source /opt/ros/jazzy/setup.bash && source install/setup.bash
set -u

# 3. Limpieza segura: mata el grupo de procesos que lanzamos, sin patrones que casen con este script
PGID=""
limpiar() {
  [[ -n "$PGID" ]] && { kill -TERM -- "-$PGID" 2>/dev/null; sleep 2; kill -KILL -- "-$PGID" 2>/dev/null; }
  pkill -f "^gz sim" 2>/dev/null; pkill -x move_group 2>/dev/null
}
trap limpiar EXIT INT TERM
limpiar_previo() { pkill -f "^gz sim" 2>/dev/null; pkill -x move_group 2>/dev/null; sleep 1; }
limpiar_previo

ARGS=(escenario:="$ESC" gui:=true)
[[ -n "$VAR" ]] && ARGS+=("variante:=$VAR")
echo "Levantando Gazebo + MoveIt (unos 15-30 s)..."
setsid ros2 launch rl6gdl_e6_gazebo gazebo_e6.launch.py "${ARGS[@]}" >"$LOG" 2>&1 &
PGID=$!

# 4. Esperar a que estén listos el controlador y MoveIt
for _ in $(seq 120); do
  grep -q "Configured and activated brazo_controller" "$LOG" 2>/dev/null \
    && grep -q "You can start planning now" "$LOG" 2>/dev/null && break
  kill -0 "$PGID" 2>/dev/null || { echo "El launch terminó antes de tiempo. Ver $LOG"; exit 1; }
  sleep 1
done
grep -q "Configured and activated brazo_controller" "$LOG" || { echo "No quedó listo en 120 s. Ver $LOG"; exit 1; }
echo "Listo. Ventana de Gazebo abierta."

# 5. Ejecutar y permitir repetir
while true; do
  python3 src/rl6gdl_planning/scripts/ejecutar_e6.py --escenario "$ESC" ${VAR:+--variante "$VAR"}
  echo
  read -r -p "Enter = repetir la tarea · q = cerrar Gazebo: " resp || break
  [[ "$resp" == "q" ]] && break
done
echo "Cerrando..."
