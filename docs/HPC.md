# OSU HPC training

The current project uses standalone Newton/MuJoCo Warp, not the earlier
Isaac Lab container. A reported dgxh-1 allocation exposes an H100 MIG 4g.40gb
slice (40 GiB). Use the actual job's CPU/GPU/time allocation, not a whole-node
assumption. Python module: python/3.12.

## Persistent environment

The uploaded project is ~/robot-dog-newton. Its CUDA environment is .venv-cuda
in persistent home storage. Home quota was 25 GB; disposable Apptainer cache
cleanup freed installation space. Use --no-cache-dir and node /tmp for install
temporary files if needed. Node-local /scratch does not follow jobs between
nodes. Keep policies in persistent storage and W&B.

```bash
module load python/3.12
python -m venv .venv-cuda
source .venv-cuda/bin/activate
python -m pip install --no-cache-dir -r requirements-cuda.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Newton 1.7.0 uses the pinned MuJoCo/MuJoCo Warp 3.15 dependencies. CPU-only
Torch cannot run train_cuda.py. See [CUDA training](../simulation/rl/CUDA_TRAINING.md).

## Resume from the repository

From the repository root in an active GPU allocation:

```bash
python simulation/rl/train_cuda.py \
  --resume policies/best-distance --source simulation/mujoco \
  --envs 64 --steps 65536 --save-every 32768 --output runs/cuda
```

Weights and normalization are restored. Checkpoints receive three 20-second
evaluations. Compare physical metrics, not raw return across reward changes.
The shell launchers are historical recipes expecting the flat uploaded package
layout; the Python command above works from the repository layout. Preserved
repository checkpoints do not require W&B artifact download access. Logging
uses the user's existing W&B login; credentials are never committed.

## Stopping

Use --max-seconds for unattended bounded runs. Foreground Ctrl+C requests an
interrupted checkpoint. nohup may inherit ignored SIGINT; the original long
run was stopped with SIGTERM, retaining periodic saves but no final interrupted
save. A stale W&B running label does not prove a process remains alive.
Check the actual job/process before relaunching. Keep policy.zip, normalize.pkl,
environment.json and matching source together. Do not close a GPU allocation
before checkpoint/artifact saving completes. Simulator checkpoints do not
contain real-world calibration.
