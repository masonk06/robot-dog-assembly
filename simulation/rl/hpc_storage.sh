#!/usr/bin/env bash
# Source this in the same shell that launches training.
export DOG_WORK="${DOG_WORK:-/scratch/$USER/robot-dog-rl}"
if [[ "$DOG_WORK" != /* ]]; then
  echo 'DOG_WORK must be an absolute writable path.' >&2
  return 1
fi
mkdir -p "$DOG_WORK"/{runs,cache,wandb,wandb-data,tmp} || return 1
if [[ ! -w "$DOG_WORK" ]]; then
  echo "Training storage is not writable: $DOG_WORK" >&2
  return 1
fi
export XDG_CACHE_HOME="$DOG_WORK/cache"
export WARP_CACHE_PATH="$DOG_WORK/cache/warp"
export CUDA_CACHE_PATH="$DOG_WORK/cache/nvidia"
export TORCH_HOME="$DOG_WORK/cache/torch"
export TORCHINDUCTOR_CACHE_DIR="$DOG_WORK/cache/torchinductor"
export TRITON_CACHE_DIR="$DOG_WORK/cache/triton"
mkdir -p "$CUDA_CACHE_PATH" || return 1
export PIP_CACHE_DIR="$DOG_WORK/cache/pip"
export WANDB_DIR="$DOG_WORK/wandb"
export WANDB_CACHE_DIR="$DOG_WORK/cache/wandb"
export WANDB_DATA_DIR="$DOG_WORK/wandb-data"
export WANDB_BASE_URL=https://api.forge.coreweave.com
export PYTHONPYCACHEPREFIX="$DOG_WORK/cache/pycache"
export TMPDIR="$DOG_WORK/tmp"
echo "Training files and caches: $DOG_WORK"
df -h "$DOG_WORK"
