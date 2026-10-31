#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -u evaluate_cuda.py stride-checkpoint --source stride-source --cycle-seconds 3.0 --stride-m 0.021 \
  --episodes 3 --output stride-initial-evaluation.json
python - <<'PY'
import json
r=json.load(open('stride-initial-evaluation.json'))
assert r['eval/fall_fraction']==0 and r['eval/slide_reset_fraction']==0, 'Stride baseline unstable; training not launched'
assert r['eval/episode_seconds']>=19.9, 'Stride baseline ended early'
assert min(v for k,v in r.items() if k.startswith('eval/steps/'))>=5, 'Stride baseline omits a leg'
print('Stride baseline passed. Continuing existing weights with a 21 mm reference sweep and 3-second cycle.')
PY
exec python -u train_cuda.py --resume stride-checkpoint --source stride-source \
  --cycle-seconds 3.0 --stride-m 0.021 --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --steps 12000000 --max-seconds 2700 --save-every 500000 --output runs/cuda-stride
