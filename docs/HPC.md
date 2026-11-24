# OSU HPC training

The current project uses standalone Newton/MuJoCo Warp, not the earlier
Isaac Lab container. A reported dgxh-1 allocation exposes an H100 MIG 4g.40gb
slice (40 GiB). Use the actual job's CPU/GPU/time allocation, not a whole-node
assumption. Python module: python/3.12.

## Persistent environment

The uploaded project is ~/robot-dog-newton. Its CUDA environment is
~/.venv-cuda-py312 in persistent home storage. Home quota was 25 GB; disposable Apptainer cache
cleanup freed installation space. Use --no-cache-dir and node /tmp for install
temporary files if needed. Node-local /scratch does not follow jobs between
nodes. Keep policies in persistent storage and W&B. Run the requirements command
from the repository checkout, not from `~`.

On dgxh-1, `/raid` is the available 25 TiB node-local RAID workspace. Use it
for this 12-hour allocation's virtual environment, caches, and active run
files. It is not a shared or persistent filesystem: copy selected checkpoints
and outputs to backed-up project storage before the allocation ends, and expect
to recreate the environment if a later job runs on another node.

```bash
cd ~/robot-dog-newton
module load python/3.12
python --version  # Must report Python 3.12.x before creating the environment.
export LUCA_FAST="/raid/$USER/luca"
mkdir -p "$LUCA_FAST/tmp"
export TMPDIR="$LUCA_FAST/tmp"
python -m venv "$LUCA_FAST/.venv-cuda-py312"
source "$LUCA_FAST/.venv-cuda-py312/bin/activate"
python --version  # Must still report Python 3.12.x.
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -r requirements-cuda.txt
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

Newton 1.7.0 uses the pinned MuJoCo/MuJoCo Warp 3.15 dependencies. CPU-only
Torch cannot run train_cuda.py. See [CUDA training](../simulation/rl/CUDA_TRAINING.md).

## Resume from the repository

From the repository root in an active GPU allocation:

```bash
python simulation/rl/train_cuda.py \
  --resume policies/tracking-baseline --source simulation/mujoco \
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

## Current P2S training run

For the current chassis, use the [P2S IK + PPO walking
workflow](../simulation/p2s_crawl/README.md), not the historical fast-gait
command above. It builds a portable source tree from the P2S model, runs a
CUDA import gate, then trains a 25 mm-stride, 3-second IK walk with PPO
residual actions across provisional centre-of-mass and friction scenarios. It
uses 128 CUDA worlds, preserves the 60-observation input contract, and does
not control hardware.

## Scoped upload to OSU HPC

The local workspace may contain unrelated CAD and PCB work. Transfer only the
simulation and HPC documentation patch unless those other changes are also
intended for the cluster. From this repository on the local machine, create a
patch after reviewing it:

```powershell
git diff --check
git diff -- simulation/p2s_crawl simulation/rl docs/HPC.md > luca-ik-ppo-hpc.patch
scp .\luca-ik-ppo-hpc.patch YOUR_OSU_USERNAME@YOUR_OSU_HOST:~/
```

On the OSU login node, update the repository to the same base revision and
apply the patch only after its dry run succeeds:

```bash
cd ~/robot-dog-newton
git pull --ff-only
git apply --check ~/luca-ik-ppo-hpc.patch
git apply ~/luca-ik-ppo-hpc.patch
module load python/3.12
source .venv-cuda/bin/activate
```

Then obtain the approved 12-hour GPU allocation and, inside it, launch:

```bash
cd ~/robot-dog-newton
bash simulation/p2s_crawl/hpc_run_quasistatic.sh
```

The launcher performs its CUDA import gate before training and uses W&B online
logging by default. Copy the selected checkpoint from node-local scratch to
persistent storage before the allocation ends.
