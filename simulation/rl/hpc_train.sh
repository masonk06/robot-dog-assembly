#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
module load python/3.12
source "$HOME/training/.venv/bin/activate"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -m pytest simulation/rl/test_env.py -q
# Version 7 starts fresh with small, filtered residuals and low exploration.
exec python simulation/rl/train.py --source source --parallel --envs 6 \
  --torch-threads 2 --steps 200000 --save-every 20000 --project robot-dog-rl
