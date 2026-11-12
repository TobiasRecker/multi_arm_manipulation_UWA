#!/usr/bin/env bash
set -eo pipefail
for key in GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR; do
  if [[ "${!key:-}" == *"/snap/"* ]]; then unset "$key"; fi
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/control_env.bash"
exec ros2 run uwa_cell_control board_capture_gui "$@"
