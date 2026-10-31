#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -u evaluate_cuda.py stride24-checkpoint --source stride24-source --stride-m 0.024 \
  --episodes 3 --output stride24-initial-evaluation.json
python - <<'PY'
import json
import math
r=json.load(open('stride24-initial-evaluation.json'))
assert all(math.isfinite(v) for v in r.values() if isinstance(v, (int, float))), 'Nonfinite stride evaluation; training not launched'
assert r['eval/fall_fraction']==0 and r['eval/slide_reset_fraction']==0, 'Stride baseline unstable; training not launched'
assert r['eval/episode_seconds']>=19.9, 'Stride baseline ended early'
assert min(v for k,v in r.items() if k.startswith('eval/steps/'))>=5, 'Stride baseline omits a leg'
print('24 mm baseline passed. Continuing the saved 21 mm policy with the original 3-second cycle.')
PY
exec python -u train_cuda.py --resume stride24-checkpoint --source stride24-source \
  --stride-m 0.024 --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --steps 12000000 --max-seconds 2700 --save-every 500000 --output runs/cuda-stride24
