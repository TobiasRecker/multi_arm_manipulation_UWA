#!/usr/bin/env bash
# Run after the dedicated Python 3.11 environment and CUDA PyTorch are present.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/foundationpose_titanpc_env.bash"
test "$(id -un)" = ubuntu22
test -O "$UWA_FP_ROOT"
test -x "$CONDA_PREFIX/bin/python"
cd "$UWA_FP_ROOT/FoundationPose"
# Upstream hardcodes /tmp for OBJ plus shared material filenames. Keep those
# temporary model files inside this experiment's private directory as well.
python - <<'PY'
from pathlib import Path
p = Path('estimater.py')
original = "self.mesh_path = f'/tmp/{uuid.uuid4()}.obj'"
replacement = "self.mesh_path = os.path.join(os.environ['TMPDIR'], f'{uuid.uuid4()}.obj')"
text = p.read_text()
if original in text:
    assert text.count(original) == 1
    p.write_text(text.replace(original, replacement))
elif replacement not in text:
    raise RuntimeError('Unexpected upstream temporary mesh export path')
PY
git diff -- estimater.py > "$UWA_FP_ROOT/logs/upstream-local.patch"
constraints="$UWA_FP_ROOT/tools/foundationpose_titanpc_constraints.txt"
python -m pip install --no-cache-dir -c "$constraints" -r requirements.txt \
  pybind11 setuptools wheel ninja gdown
# Compile only for this TITAN RTX; do not invoke upstream's unbounded -j(nproc).
python -m pip install --no-cache-dir --no-build-isolation --no-deps \
  git+https://github.com/facebookresearch/pytorch3d.git@V0.7.8
python -m pip install --no-cache-dir --no-build-isolation --no-deps \
  git+https://github.com/NVlabs/nvdiffrast.git@v0.3.3
python -m pip install --no-cache-dir iopath
cmake -S mycpp -B mycpp/build -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR="$(python -m pybind11 --cmakedir)" \
  -DPYTHON_EXECUTABLE="$CONDA_PREFIX/bin/python"
cmake --build mycpp/build -j4
python -m pip check
python -m pip freeze > "$UWA_FP_ROOT/logs/pip-freeze.txt"
git rev-parse HEAD > "$UWA_FP_ROOT/logs/foundationpose-commit.txt"
printf '\nINSTALL COMPLETE\n'
