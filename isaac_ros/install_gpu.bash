#!/usr/bin/env bash
# Install the Isaac ROS 5 experiments on a configured Lyrical NVIDIA GPU host.
set -euo pipefail
mpx_dir="$(cd "$(dirname "$0")" && pwd)"
mapfile -t mpx_packages < <(sed -e '/^#/d' -e '/^$/d' -e 's/^/ros-lyrical-/' "$mpx_dir/packages.txt")
if [[ "${1:-}" == "--preview" ]]; then
  exec apt-get -s --no-install-recommends install "${mpx_packages[@]}"
fi
exec sudo apt-get install --no-install-recommends "${mpx_packages[@]}"
