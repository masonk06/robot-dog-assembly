#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
source .venv-cuda/bin/activate
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export WANDB_BASE_URL=https://api.forge.coreweave.com
if pgrep -u "$(id -u)" -f '^python -u train_cuda[.]py' >/dev/null; then
  echo 'Another CUDA trainer is active. Finish it before starting this experiment.' >&2
  exit 1
fi
python - <<'PY'
import torch,mujoco,newton,wandb
assert torch.cuda.is_available(), 'A CUDA-enabled environment and GPU allocation are required'
print('Torch:',torch.__version__,'GPU:',torch.cuda.get_device_name(0),flush=True)
PY
python -u evaluate_cuda.py speed12-checkpoint --source speed12-source \
  --episodes 5 --seed 10000 --seconds 60 --output speed12-initial-evaluation.json
python - <<'PY'
import json,math,shutil
r=json.load(open('speed12-initial-evaluation.json'))
assert r['reference_stride_m']==.0315 and r['gait_cycle_seconds']==3., 'Wrong gait configuration'
assert r['commanded_speed_m_s']==.012 and r['tracking_reward_weight']==1.375 and r['slip_penalty_weight']==2.2, 'Wrong command/reward settings'
assert all(math.isfinite(v) for v in r.values() if isinstance(v,(int,float))), 'Nonfinite initial evaluation'
for trial in r['per_episode']:
    assert trial['seconds']>=59.9 and trial['fallen']==0 and trial['sliding']==0, 'Incomplete or unstable starting gait; training not launched'
    assert min(trial['steps'].values())>=18, 'A leg is not participating; training not launched'
shutil.copy2('speed12-initial-evaluation.json','speed12-source/baseline-evaluation.json')
print('Fresh baseline:',r['eval/net_speed_m_s']*100,'cm/s; slip score:',r['eval/foot_slip_m2_s2'],flush=True)
print('Continuing existing weights: command 1.2 cm/s, tracking weight 1.375, slip weight 2.2.',flush=True)
PY
exec python -u train_cuda.py --resume speed12-checkpoint --source speed12-source \
  --target-speed 0.012 --tracking-weight 1.375 --slip-weight 2.2 \
  --envs 64 --rollout 128 --minibatch 256 --epochs 5 \
  --eval-episodes 5 --eval-seconds 60 --steps 12000000 --max-seconds 2700 \
  --save-every 500000 --output runs/cuda-speed12-slip22
