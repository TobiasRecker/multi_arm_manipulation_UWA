# Local UWA hardware tools use domain66; the GUI selects domain67 for Mock.
# Separate from Gazebo domain64 and camera65. For direct mock CLI calls export67.
_uwa_control_repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export UWA_WS="${UWA_WS:-$(cd -- "$_uwa_control_repo/../.." && pwd)}"
if [[ -n "${ROS_DISTRO:-}" && "$ROS_DISTRO" != lyrical ]]; then
  echo "Frisches Terminal verwenden: ROS_DISTRO ist bereits $ROS_DISTRO." >&2
  return 1
fi
source /opt/ros/lyrical/setup.bash
source "$UWA_WS/install_lyrical/setup.bash"
export ROS_DOMAIN_ID=66 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST QT_QPA_PLATFORM=xcb
export ROS_LOG_DIR="$UWA_WS/setup/logs/uwa-control/ros"
mkdir -p "$ROS_LOG_DIR"
unset _uwa_control_repo
