#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python fetch_cuda_checkpoint.py --run qfwutfdb --pointer cuda-long-start.json
CUDA_CHECKPOINT=$(python -c "import json; print(json.load(open('cuda-long-start.json'))['checkpoint'])")
CUDA_SOURCE=$(python -c "import json; print(json.load(open('cuda-long-start.json'))['source'])")
# Retain the saved 1.25 tracking weight and original checkpoint. Stop at the
# first rollout boundary after 110 minutes; final evaluation adds a little time.
exec python -u train_cuda.py --resume "$CUDA_CHECKPOINT" --source "$CUDA_SOURCE" \
  --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --steps 20000000 --max-seconds 6600 --save-every 1000000 --output runs/cuda-long
