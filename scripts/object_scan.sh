#!/usr/bin/env bash
# Explicit hardware scan / separate STOP window; opening it never moves robots.
set -eo pipefail
for key in GTK_PATH GTK_EXE_PREFIX GTK_IM_MODULE_FILE GIO_MODULE_DIR GSETTINGS_SCHEMA_DIR; do
  if [[ "${!key:-}" == *"/snap/"* ]]; then unset "$key"; fi
done
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/control_env.bash"
case "${1:-gui}" in
  gui) exec ros2 run uwa_cell_control parallel_scan_gui ;;
  check) shift; exec ros2 run uwa_cell_control parallel_scan --check-only "$@" ;;
  run) shift; exec ros2 run uwa_cell_control parallel_scan --pause-after-initial "$@" ;;
  *) echo 'Usage: bash object_scan.sh {gui|check --plan FILE --analysis FILE --output NEW_DIR|run --plan FILE --analysis FILE --output NEW_DIR}' >&2; exit 2 ;;
esac
