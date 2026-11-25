#!/usr/bin/env bash
# Execute a learned checkpoint only against the Isaac Sim process started below.
set -e
if [[ $# -ne 2 ]]; then echo "usage: $0 CHECKPOINT NEW_RESULT_DIRECTORY" >&2; exit 2; fi
checkpoint="$(realpath "$1")"
mpx_results="$(realpath -m "$2")"
[[ -f "$checkpoint" ]] || { echo "Missing $checkpoint" >&2; exit 2; }
mkdir "$mpx_results"
src="$(cd "$(dirname "$0")/.." && pwd)"
ws="$(dirname "$src")"
source "$src/tools/lyrical_env.bash"
export ROS_DOMAIN_ID="${WAFFLE_TEST_DOMAIN:-171}" ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
if [[ -n "$(ros2 node list --no-daemon --spin-time 1)" ]]; then echo "Select an empty WAFFLE_TEST_DOMAIN" >&2; exit 2; fi
lab_python="${ISAAC_LAB_PYTHON:-$HOME/IsaacLab/.venv/bin/python}"
sim_python="${ISAAC_SIM_PYTHON:-$HOME/isaacsim6_venv/bin/python}"
python3 "$src/tools/export_urdf.py" "$mpx_results/waffle.urdf"
setsid env PYTHONPATH="$PYTHONPATH:/usr/lib/python3/dist-packages" "$sim_python" "$src/sim/scene.py" "$mpx_results/waffle.urdf" --output "$mpx_results/scene" --headless >"$mpx_results/sim.log" 2>&1 &
sim_pid=$!
control_pid=''
cleanup() {
  if [[ -n "$control_pid" ]]; then kill -TERM -- -"$control_pid" 2>/dev/null || true; fi
  kill -TERM -- -"$sim_pid" 2>/dev/null || true
  wait "$sim_pid" 2>/dev/null || true
  if [[ -n "$control_pid" ]]; then wait "$control_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
timeout 90 ros2 topic echo /isaac/joint_states sensor_msgs/msg/JointState --once --field name >"$mpx_results/simulator-joints.txt"
setsid ros2 launch turtlebot3_manipulation_bringup robot.launch.py mode:=isaac >"$mpx_results/control.log" 2>&1 &
control_pid=$!
export PYTHONPATH="$ws/.learning-deps:$PYTHONPATH:/usr/lib/python3/dist-packages"
timeout 150 "$lab_python" "$src/learning/ros_policy.py" --policy "$checkpoint" --instruction pick_and_place --execute --frames 32 --hz 4 --trace "$mpx_results/trace.jsonl" --ros-args -p use_sim_time:=true
python3 "$src/learning/check_trace.py" "$mpx_results/trace.jsonl"
