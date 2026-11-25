# Source in Bash at build time or when opening a ROS terminal.
source /opt/ros/lyrical/setup.bash
_mpx_ws="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
_mpx_root="$_mpx_ws/.cartographer"
if [[ -d "$_mpx_root/opt/ros/lyrical" ]]; then
  _mpx_arch="$(gcc -print-multiarch)"
  export CMAKE_PREFIX_PATH="$_mpx_root/opt/ros/lyrical:$_mpx_root/usr:${CMAKE_PREFIX_PATH:-}"
  export AMENT_PREFIX_PATH="$_mpx_root/opt/ros/lyrical:$AMENT_PREFIX_PATH"
  export LD_LIBRARY_PATH="$_mpx_root/opt/ros/lyrical/lib:$_mpx_root/usr/lib/$_mpx_arch:${LD_LIBRARY_PATH:-}"
  export CPATH="$_mpx_root/usr/include/$_mpx_arch${CPATH:+:$CPATH}"
fi
if [[ -f "$_mpx_ws/install/local_setup.bash" ]]; then
  source "$_mpx_ws/install/local_setup.bash"
fi
unset _mpx_arch _mpx_root _mpx_ws
