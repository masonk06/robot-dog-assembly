# Newton training pilot

The NewtonDogEnv adapter uses Newton/MuJoCo Warp CUDA physics, including actual
GPU contact normal forces, and the original CPU observations/reward accounting.
It resumes the selected version 7 checkpoint and normalization statistics.
Training/evaluation use Newton, and saved manifests identify the backend.

This is a single-world validation bridge, not GPU-batched training. Do not
request hundreds of worlds or launch subprocess GPU workers with this adapter.
Local smoke throughput was about 9 steps/s, so this is not a speed improvement
over CPU MuJoCo. A batched implementation remains required for large HPC runs.

Validated locally: 12 existing environment tests; a 30-frame zero-action CPU/GPU
parity check (max normal force difference about 0.004 N); and 256 PPO continuation
steps with checkpoint, normalization and W&B artifact saving. That training smoke
used one 1-second evaluation solely to check integration, not gait quality.

HPC pilot: unpack into the existing robot-dog-newton directory, activate its
.venv, install wandb and tensorboard, and run bash hpc_newton_pilot.sh.
It first runs the short contact parity gate, then 2048 additional PPO steps.
Checkpoints receive three full 20-second evaluations including slip, steps,
falls, forward progress and landing impacts. Original checkpoint is retained.
The script must be run from an active GPU allocation. Keep the same W&B login.

The CPU reference baseline is also logged by train.py for comparison; its
baseline/ metrics are CPU MuJoCo, whereas eval/ metrics use the selected backend.
