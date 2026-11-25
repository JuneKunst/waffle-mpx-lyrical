# Source on the NVIDIA GPU host, with either system packages or the workspace overlay.
_mpx_src="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$_mpx_src/tools/lyrical_env.bash"
_mpx_gpu_root="$(dirname "$_mpx_src")/.isaac-ros"
_mpx_gpu_prefix="$_mpx_gpu_root/opt/ros/lyrical"
if [[ -d "$_mpx_gpu_prefix/share/ament_index" ]]; then
  export AMENT_PREFIX_PATH="$_mpx_gpu_prefix:$AMENT_PREFIX_PATH"
  export CMAKE_PREFIX_PATH="$_mpx_gpu_prefix:${CMAKE_PREFIX_PATH:-}"
  export PATH="$_mpx_gpu_prefix/bin:$PATH"
  export PYTHONPATH="$_mpx_gpu_prefix/lib/python3.12/site-packages:$_mpx_gpu_prefix/local/lib/python3.12/dist-packages:${PYTHONPATH:-}"
  export LD_LIBRARY_PATH="$_mpx_gpu_prefix/lib:$_mpx_gpu_prefix/lib/x86_64-linux-gnu:$_mpx_gpu_root/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
  for _mpx_extra in "$_mpx_gpu_prefix"/opt/*/lib "$_mpx_gpu_prefix"/opt/*/lib64; do
    if [[ -d "$_mpx_extra" ]]; then export LD_LIBRARY_PATH="$_mpx_extra:$LD_LIBRARY_PATH"; fi
  done
fi
if [[ -d "$(dirname "$_mpx_src")/.learning-deps/av" ]]; then
  export PYTHONPATH="$(dirname "$_mpx_src")/.learning-deps:${PYTHONPATH:-}"
fi
unset _mpx_src _mpx_gpu_root _mpx_gpu_prefix _mpx_extra
_mpx_gpu_plugin="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.cumotion-build/install"
if [[ -f "$_mpx_gpu_plugin/local_setup.bash" ]]; then source "$_mpx_gpu_plugin/local_setup.bash"; fi
unset _mpx_gpu_plugin
