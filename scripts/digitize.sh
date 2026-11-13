#!/usr/bin/env bash
# Camera-only digitization jobs; no robot motion command is exposed.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/control_env.bash"
exec python3 -m uwa_cell_control.digitization_job "$@"
