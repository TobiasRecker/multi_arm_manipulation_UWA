#!/usr/bin/env bash
# Source only in a dedicated FoundationPose subprocess; no profile changes.
export UWA_FP_ROOT=/media/ubuntu22/RAID1_L/uwa-foundationpose-ubuntu22
export CONDA_PREFIX="$UWA_FP_ROOT/envs/foundationpose"
export CONDA_PKGS_DIRS="$UWA_FP_ROOT/packages"
export CONDA_ENVS_PATH="$UWA_FP_ROOT/envs"
export CUDA_HOME=/usr/local/cuda-12.3
export PATH="$CONDA_PREFIX/bin:$CUDA_HOME/bin:/usr/local/bin:/usr/bin:/bin"
export LD_LIBRARY_PATH="$CUDA_HOME/lib64:$CONDA_PREFIX/lib"
export TMPDIR="$UWA_FP_ROOT/tmp"
export XDG_CACHE_HOME="$UWA_FP_ROOT/cache"
export PIP_CACHE_DIR="$XDG_CACHE_HOME/pip"
export TORCH_EXTENSIONS_DIR="$XDG_CACHE_HOME/torch_extensions"
export CUDA_CACHE_PATH="$XDG_CACHE_HOME/cuda"
export MPLCONFIGDIR="$XDG_CACHE_HOME/matplotlib"
export NUMBA_CACHE_DIR="$XDG_CACHE_HOME/numba"
export WARP_CACHE_PATH="$XDG_CACHE_HOME/warp"
export PYTHONNOUSERSITE=1
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 MAX_JOBS=4
export TORCH_CUDA_ARCH_LIST=7.5
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH="$UWA_FP_ROOT/FoundationPose:$UWA_FP_ROOT/FoundationPose/mycpp/build"
