#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source ./hpc_storage.sh
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export WANDB_BASE_URL=https://api.forge.coreweave.com
if pgrep -u "$(id -u)" -f '^python -u (train_cuda|overnight_cuda)[.]py' >/dev/null; then
  echo 'A CUDA trainer is already active. Stop it before launching another.' >&2
  exit 1
fi
python - <<'PY'
import torch,newton,mujoco,wandb
assert torch.cuda.is_available(), 'CUDA-enabled Python and an active GPU allocation are required'
print('GPU:',torch.cuda.get_device_name(0),flush=True)
PY
# Last-resort process-group wall cap, with one minute for graceful checkpointing.
exec timeout --signal=TERM --kill-after=60s 14280s python -u overnight_cuda.py \
  --output "$DOG_WORK/runs/overnight-2cms" "$@"
