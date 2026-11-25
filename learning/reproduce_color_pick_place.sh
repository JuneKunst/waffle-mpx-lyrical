#!/usr/bin/env bash
# Generate color demonstrations, fit a fresh adapter, and evaluate unseen positions.
set -euo pipefail
if [[ $# -ne 4 ]]; then
    echo "Usage: $0 SCENE.usda HF_DATASET PARENT_VLA.pt NEW_RUN_DIRECTORY" >&2
    exit 2
fi
scene="$(realpath -e "$1")"
hf="$(realpath -e "$2")"
parent="$(realpath -e "$3")"
run="$(realpath -m "$4")"
src="$(cd "$(dirname "$0")/.." && pwd)"
sim_python="${ISAAC_SIM_PYTHON:-$HOME/isaacsim6_venv/bin/python}"
lab_python="${ISAAC_LAB_PYTHON:-$HOME/IsaacLab/.venv/bin/python}"
mkdir "$run"
"$sim_python" "$src/sim/evaluate_pick_place.py" "$scene" - "$run/demos" \
    --controller teacher --layouts 8 --seed 73 --decisions 92
PYTHONPATH="$(dirname "$src")/.learning-deps:${PYTHONPATH:-}" "$lab_python" \
    "$src/learning/color_imitation.py" "$hf" "$run/demos" "$run/color.npz" \
    --dataset "$run/mixed" --parent-vla "$parent"
"$sim_python" "$src/sim/evaluate_pick_place.py" "$scene" "$run/color.npz" "$run/heldout" \
    --parent-vla "$parent" --controller color --layouts 4 --seed 8601 --decisions 92
python3 "$src/learning/audit_color_eval.py" "$run/color.npz" "$run/heldout"
