#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -u check_newton_rewards.py --source source
python -u train.py --backend newton --envs 1 --torch-threads 2 \
  --resume checkpoint --source source --steps 2048 --save-every 2048 \
  --project robot-dog-rl --entity marsdenm-oregon-state-university \
  --output runs/newton-pilot
