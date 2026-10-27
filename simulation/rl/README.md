# Walking policy and training

The active controller is version 7: a programmed four-beat foot trajectory
plus learned corrections limited to 0.035 rad (about 2 degrees), filtered over
0.12 s. Control runs at 50 Hz; physics uses ten 0.002 s substeps. Body -X is
forward. Observations have 60 values: gravity, angular/linear body velocity,
speed command, joint positions/speeds, previous actions, gait phase and targets.

The default speed command is 0.01 m/s. The approved continuation uses tracking
weight 1.25; old checkpoints missing that field retain weight 1.0. Reference
stride is 20 mm, cycle 3 s and lift target 25 mm (rear multiplier 1.5). These
are requested trajectories, not measured ground clearance. Useful steps require
support, airtime, clearance, foot relocation and progress between landings.
Planted slip, hard landings, instability and abrupt corrections are penalized.

## Tools

| Tool | Purpose |
| --- | --- |
| train_cuda.py | CUDA physics/task/normalization/GAE/PPO continuation |
| cuda_task.py / cuda_runner.py | Vectorized task and shared-stream CUDA graph |
| evaluate_cuda.py | Frozen-policy, frozen-normalization GPU evaluation |
| play.py | Human viewer, selecting the checkpoint's physics backend |
| train.py / env.py | CPU trainer and shared reference task; bridge comparison |
| newton_env.py / newton_batch.py | Single/batched GPU physics with CPU task logic, for validation |
| check_cuda.py | Numerical parity, reset, no-host-transfer and optimizer gates |
| check_newton_*.py / newton_probe.py | Import/contact/batch validation |
| screen_reference.py / diagnose_gait.py | Zero-residual reference screening/diagnostics |

newton_policy.py and newton_reference.py preserve the initial migration gates.
Historical shell launchers expect the flat uploaded HPC package layout, not
the nested repository layout. Use the Python commands below from this root.

## Playback and continuation

Install the appropriate pinned environment first; see [HPC](../../docs/HPC.md).
Only load trusted serialized checkpoint files.

```bash
python simulation/rl/play.py policies/best-distance --source simulation/mujoco
python simulation/rl/train_cuda.py \
  --resume policies/best-distance --source simulation/mujoco \
  --envs 64 --steps 65536 --save-every 32768 --output runs/cuda
```

Use --tracking-weight only for an explicit reward experiment. For unattended
runs, --max-seconds stops at a rollout boundary and saves a time-limit checkpoint.
Training logs to the configured W&B account; no credentials belong in Git.
Each run/checkpoint preserves configuration, weights, normalization, evaluation
and a source reference. Do not compare raw rewards across reward-weight changes.

The CUDA task has parity/reset/optimizer tests and three-trial walking
evaluations. Its per-minibatch KL decisions stay on GPU; logging/checkpointing
intentionally transfers summaries to CPU. See [implementation notes](CUDA_TRAINING.md).
Training speedups do not establish hardware transfer or better gait quality.

## Preserved results

[Policies](../../policies/README.md) contains original-v7, tracking-baseline,
best-distance and latest-long-run. Best distance was about 16.02 cm / 20 s at
9.52 million steps; performance plateaued in the later long run. Three seeded
evaluations are a limited benchmark, not a robustness certificate.

The user confirmed rear-left supported open-loop transfer. Full policy
deployment needs calibrated hardware mappings/limits and real body-state
observations; an encoder-only playback does not supply those observations.

Earlier reward/controller experiments are retained as
[historical notes](../../docs/archive/rl-experiments.md), not current setup advice.
