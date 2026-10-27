#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -c "import torch; assert torch.cuda.is_available(), 'CUDA PyTorch is required'; print(torch.__version__, torch.cuda.get_device_name(0))"
python fetch_cuda_checkpoint.py --run "${1:-1f0ethf8}"
CUDA_CHECKPOINT=$(python -c "import json; print(json.load(open('cuda-start.json'))['checkpoint'])")
CUDA_SOURCE=$(python -c "import json; print(json.load(open('cuda-start.json'))['source'])")
python -u check_cuda.py --source "$CUDA_SOURCE" --frames 120
python -u evaluate_cuda.py "$CUDA_CHECKPOINT" --source "$CUDA_SOURCE" --episodes 3 --output cuda-before-training.json
python -u train_cuda.py --resume "$CUDA_CHECKPOINT" --source "$CUDA_SOURCE" \
  --envs 64 --rollout 128 --minibatch 256 --epochs 5 --steps 65536 --save-every 32768 \
  --output runs/cuda
