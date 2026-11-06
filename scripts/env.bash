# Source this file for commands aimed at the simulated cell, never real hardware.
_uwa_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export UWA_WS="${UWA_WS:-$(cd -- "$_uwa_repo/../.." && pwd)}"
if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != lyrical ]]; then
  echo "Open a fresh terminal: ROS_DISTRO is already $ROS_DISTRO." >&2
  return 1
fi
source /opt/ros/lyrical/setup.bash
if [[ ! -f "$UWA_WS/install_lyrical/setup.bash" ]]; then
  echo "Build the UWA packages into $UWA_WS/install_lyrical first." >&2
  return 1
fi
source "$UWA_WS/install_lyrical/setup.bash"
export ROS_DOMAIN_ID=64 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
export GZ_PARTITION=uwa_cell_sim GZ_IP=127.0.0.1 QT_QPA_PLATFORM=xcb
export ROS_LOG_DIR="$UWA_WS/setup/logs/uwa-cell"
unset _uwa_repo
