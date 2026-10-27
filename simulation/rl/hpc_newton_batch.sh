#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
# Validate replicated physics, independent controls, terminal observations,
# selective resets and warm throughput on this GPU before learning.
python -u check_newton_batch.py --source source --envs 16 --frames 100
python -u train.py --backend newton-batch --envs 16 --torch-threads 2 \
  --resume checkpoint --source source --steps 32768 --save-every 8192 \
  --project robot-dog-rl --entity marsdenm-oregon-state-university \
  --output runs/newton-batch
