#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source ./hpc_storage.sh
source "${DOG_VENV:-$HOME/robot-dog-newton/.venv-cuda}/bin/activate"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python -c "import torch, newton, mujoco, wandb; assert torch.cuda.is_available(); print('GPU:', torch.cuda.get_device_name(0))"
exec timeout --signal=TERM --kill-after=120s 41700s python -u amble_overnight.py --output "$DOG_WORK/runs/amble-overnight" "$@"
