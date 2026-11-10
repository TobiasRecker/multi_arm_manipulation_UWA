#!/usr/bin/env bash
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/control_env.bash"
exec ros2 run uwa_cell_control uwa_control_gui "$@"
