#!/usr/bin/env bash
set -eo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.bash"
exec ros2 launch uwa_cell_visualization hardware_overlay.launch.py "$@"
