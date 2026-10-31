#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python -u evaluate_cuda.py goal-checkpoint --source goal-source --stride-m 0.0255 \
  --episodes 5 --seed 20000 --seconds 60 --output goal-initial-evaluation.json
python - <<'PY'
import json
import math
r=json.load(open('goal-initial-evaluation.json'))
assert all(math.isfinite(v) for v in r.values() if isinstance(v,(int,float))), 'Nonfinite evaluation; training not launched'
for trial in r['per_episode']:
    assert trial['seconds']>=59.9 and trial['fallen']==0 and trial['sliding']==0, 'Incomplete or unstable trial; training not launched'
    assert min(trial['steps'].values())>=18, 'A leg is not participating; training not launched'
print('Five 60-second gait checks passed. Minimum net speed:',min(t['net_speed_m_s'] for t in r['per_episode']),'m/s')
PY
exec python -u train_cuda.py --resume goal-checkpoint --source goal-source \
  --stride-m 0.0255 --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --eval-episodes 5 --eval-seconds 60 --steps 12000000 --max-seconds 2700 \
  --save-every 500000 --output runs/cuda-goal1cms
