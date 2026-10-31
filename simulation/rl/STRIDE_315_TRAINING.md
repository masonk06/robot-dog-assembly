# 31.5 mm stride: learn corrections with the current rewards

This bundle continues from the selected stride-sweep checkpoint in W&B run
sakq2z9n. Its learned weights come from mmtw7dxi, step 28,309,344; the sweep
changed the reference stride without performing PPO updates. Original weights
and normalization are included. This run adds actual PPO updates at 31.5 mm.

Keep the 3.0-second stepping cycle, 31.5 mm stride, 1 cm/s command, foot lift,
current slip/landing penalties, four-leg rewards, residual filtering and all
other task settings fixed. The goal is less slipping while preserving useful
forward progress. Improvement is an experiment, not a guaranteed result.
The current net speed exceeds the 1 cm/s command; training may also reduce
that overshoot. Compare speed and slip together when choosing a checkpoint.

Starting local check (five 60-second trials, batch seed 20000):

- Net speed: 1.17135 cm/s; distance: 70.293 cm in about 60 seconds.
- Foot-slip score: 0.00017369; each leg took 19-20 useful steps.
- No falls or sliding resets. Only flat ground and small reset noise tested.

The launcher runs a fresh five-trial baseline on the allocated GPU with batch
seed 10000, matching the training checkpoint evaluations. It saves that report
as stride315-source/baseline-evaluation.json, so each run's frozen source artifact
includes its own comparison baseline. Individual trial metrics are retained in
evaluation.json; scalar means appear in W&B.

## Start on HPC

Upload robot-dog-stride315-training.zip to your HPC home directory, then run:

```bash
cd ~
unzip -o robot-dog-stride315-training.zip -d robot-dog-newton
cd ~/robot-dog-newton
bash hpc_cuda_stride315.sh
```

Use the existing .venv-cuda; no reinstall or W&B key is bundled. Existing W&B
login is used for marsdenm-oregon-state-university/robot-dog-rl on Forge.
The launcher checks CUDA availability, rejects an already-running CUDA trainer,
and verifies full baseline trials with all legs participating before training.

The GPU rollout/task/normalization/PPO implementation uses 64 worlds, up to
12 million additional steps or 2700 seconds (45 minutes), saving and evaluating
about every 500,000 steps under runs/cuda-stride315. Training episodes remain
20 seconds; each checkpoint is evaluated in five 60-second worlds. Setup,
baseline evaluation and final saving/upload add time, so leave at least an
hour on the GPU allocation. Keep the terminal open for this foreground command.

## Review after training

Compare each checkpoint with its fresh baseline: net forward speed, slip,
foot forces, landing speed, per-leg steps, episode completion and playback.
Lower slip accompanied by stalling or lost leg participation is not a useful
improvement. Retain the original and select a checkpoint based on this tradeoff;
the final checkpoint is not automatically the best one. Change another
variable only after reviewing this fixed-settings continuation.

This is simulation training only. Model geometry, joint directions and physical
calibration files are not changed by this package.
