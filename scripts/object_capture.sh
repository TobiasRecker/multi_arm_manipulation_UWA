#!/usr/bin/env bash
# Camera-only: does not start robot drivers or issue motion commands.
set -eo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$script_dir/camera_capture.sh" --five-cameras "$@"
