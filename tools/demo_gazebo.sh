#!/usr/bin/env bash
set -u
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ESC="${1:-}"; VAR="${2:-}"
if [[ -z "$ESC" ]]; then echo 'Uso: tools/demo_gazebo.sh <escenario> [variante]   (ej.: tools/demo_gazebo.sh 5 "5 k=2.0")'; exit 1; fi
LOG="${TMPDIR:-/tmp}/demo_gazebo_launch.log"

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

cd "$RAIZ/ros2_ws" || exit 1
set +u
source /opt/ros/jazzy/setup.bash && source install/setup.bash
set -u

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

for _ in $(seq 120); do
  grep -q "Configured and activated brazo_controller" "$LOG" 2>/dev/null \
    && grep -q "You can start planning now" "$LOG" 2>/dev/null && break
  kill -0 "$PGID" 2>/dev/null || { echo "El launch terminó antes de tiempo. Ver $LOG"; exit 1; }
  sleep 1
done
grep -q "Configured and activated brazo_controller" "$LOG" || { echo "No quedó listo en 120 s. Ver $LOG"; exit 1; }
echo "Listo. Ventana de Gazebo abierta."

while true; do
  python3 src/rl6gdl_planning/scripts/ejecutar_e6.py --escenario "$ESC" ${VAR:+--variante "$VAR"}
  echo
  read -r -p "Enter = repetir la tarea · q = cerrar Gazebo: " resp || break
  [[ "$resp" == "q" ]] && break
done
echo "Cerrando..."
