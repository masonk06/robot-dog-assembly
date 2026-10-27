#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python fetch_cuda_checkpoint.py --run w2p0ffha --pointer cuda-tracking-start.json
CUDA_CHECKPOINT=$(python -c "import json; print(json.load(open('cuda-tracking-start.json'))['checkpoint'])")
CUDA_SOURCE=$(python -c "import json; print(json.load(open('cuda-tracking-start.json'))['source'])")
python -u train_cuda.py --resume "$CUDA_CHECKPOINT" --source "$CUDA_SOURCE" \
  --tracking-weight 1.25 --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --steps 262144 --save-every 65536 --output runs/cuda-tracking
