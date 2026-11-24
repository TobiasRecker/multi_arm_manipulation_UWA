#!/usr/bin/env bash
set -eo pipefail
source /opt/ros/lyrical/setup.bash
set -u
export XDG_CACHE_HOME=/output/.cache
export GZ_HOMEDIR=/output/.gz
unset DISPLAY
cmake -S /input -B /output/build -DCMAKE_BUILD_TYPE=Release
cmake --build /output/build -j 4
python3 /input/bake.py
/output/build/render_carton /output/movie.json /output/preview preview
python3 /input/encode.py --preview
if [[ ${1:-preview} == full ]]; then
    /output/build/render_carton /output/movie.json /output
    python3 /input/encode.py
fi
