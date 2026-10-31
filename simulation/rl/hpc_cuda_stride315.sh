#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export WANDB_BASE_URL=https://api.forge.coreweave.com
if pgrep -u "$(id -u)" -f '^python -u train_cuda[.]py' >/dev/null; then
  echo 'Another CUDA training process is active. Finish it before starting this experiment.' >&2
  exit 1
fi
python - <<'PY'
import torch, mujoco, newton, wandb
assert torch.cuda.is_available(), 'CUDA-enabled PyTorch and a GPU allocation are required'
print('Torch:', torch.__version__, 'GPU:', torch.cuda.get_device_name(0), flush=True)
PY
python -u evaluate_cuda.py stride315-checkpoint --source stride315-source \
  --episodes 5 --seed 10000 --seconds 60 --output stride315-initial-evaluation.json
python - <<'PY'
import json
import math
import shutil
r=json.load(open('stride315-initial-evaluation.json'))
assert r['reference_stride_m']==0.0315 and r['gait_cycle_seconds']==3.0, 'Wrong task configuration'
assert all(math.isfinite(v) for v in r.values() if isinstance(v,(int,float))), 'Nonfinite initial evaluation'
for trial in r['per_episode']:
    assert trial['seconds']>=59.9 and trial['fallen']==0 and trial['sliding']==0, 'Incomplete or unstable trial; training not launched'
    assert min(trial['steps'].values())>=18, 'A leg is not participating; training not launched'
shutil.copy2('stride315-initial-evaluation.json','stride315-source/baseline-evaluation.json')
print('Starting baseline:',r['eval/net_speed_m_s']*100,'cm/s; slip score:',r['eval/foot_slip_m2_s2'],flush=True)
print('Continuing learned weights at 31.5 mm. Cadence, rewards and other task settings remain fixed.',flush=True)
PY
exec python -u train_cuda.py --resume stride315-checkpoint --source stride315-source \
  --stride-m 0.0315 --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --eval-episodes 5 --eval-seconds 60 --steps 12000000 --max-seconds 2700 \
  --save-every 500000 --output runs/cuda-stride315
