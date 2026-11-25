#!/usr/bin/env bash
# Build NVIDIA's plugin against the MoveIt actually installed on this GPU host.
set -e
mpx_src="$(cd "$(dirname "$0")/.." && pwd)"
source "$mpx_src/tools/isaac_env.bash"
mpx_work="$(dirname "$mpx_src")/.cumotion-build"
mkdir -p "$mpx_work"
if [[ ! -d "$mpx_work/upstream/.git" ]]; then
  git clone --depth=1 --filter=blob:none --sparse --branch release-5.0 https://github.com/NVIDIA-ISAAC-ROS/isaac_ros_cumotion.git "$mpx_work/upstream"
  git -C "$mpx_work/upstream" sparse-checkout set isaac_ros_cumotion_moveit
fi
git -C "$mpx_work/upstream" fetch --depth=1 origin 4744ab9e29e4df73e11e0eb5c75cdbe07bcd99fe
git -C "$mpx_work/upstream" checkout --detach FETCH_HEAD
cd "$mpx_work"
colcon build --base-paths upstream/isaac_ros_cumotion_moveit --merge-install --cmake-args -DBUILD_TESTING=OFF -DCMAKE_BUILD_TYPE=Release
