# 1.2 cm/s command with stronger tracking and slip rewards

Continue the final lower-slip policy from j6ett8qi, step 36,943,712. Preserve
the learned network, optimizer state and observation normalization. Change:

| Setting | Parent | New run |
| --- | ---: | ---: |
| Commanded forward speed | 0.010 m/s (1 cm/s) | 0.012 m/s (1.2 cm/s) |
| Speed-tracking weight | 1.25 | 1.375 (+10%) |
| Foot-slip penalty weight | 2.0 | 2.2 (+10%) |

Keep the reference stride at 31.5 mm, the complete stepping cycle at 3 seconds,
and all other settings fixed. A command is the desired speed supplied to the
policy and reward; measured speed is an evaluation outcome. Increasing the
tracking weight encourages closeness to the command, not unlimited speed.

The parent averaged 1.1411 cm/s in five 60-second trials with foot-slip score
0.00016250 and no falls/sliding resets. Raising the command also changes a
policy observation; the frozen starting weights must therefore be evaluated
again. The new baseline runs before training and is copied into the new run's
source artifact. Parent results are preserved as parent-evaluation.json, rather
than labeled as an evaluation of the new command.

Local frozen-policy baseline at the new command: 1.0745 cm/s and slip score
0.00024455 over five full-minute trials, with all legs participating and no
falls/sliding resets. This is initially slower and more slippery than the
parent. The command observation is different while normalization and weights
are retained; training needs to adapt. Do not label the command increase as
an already-achieved gait improvement.

Both the command and two reward weights change in this user-requested combined
experiment, so results cannot isolate the contribution of each change. The
slip multiplier is now recorded explicitly in the task manifest and is applied
in both CPU and CUDA environments. Older manifests default to the original 2.0.

## HPC launch

Upload robot-dog-speed12-slip22.zip to your HPC home directory:

```bash
cd ~
unzip -o robot-dog-speed12-slip22.zip -d robot-dog-newton
cd ~/robot-dog-newton
bash hpc_cuda_speed12.sh
```

Use the existing .venv-cuda and Forge W&B login. Do not start a second trainer
in the same allocation. After five full-minute baseline checks, the launcher
trains 64 parallel worlds for up to 12 million additional steps or 45 minutes.
It saves/evaluates about every 500,000 steps under runs/cuda-speed12-slip22 and
logs to marsdenm-oregon-state-university/robot-dog-rl. Training episodes remain
20 seconds; each checkpoint evaluation runs five 60-second trials. Allow at
least an hour for baseline/setup, training and final upload. Keep the terminal
and GPU allocation active.

Compare net speed and command error, slip, per-leg step counts, full episode
completion, landing impact and playback against the fresh baseline. Reduced
slip caused by stalling is not a successful improvement. The final checkpoint
need not be the best tradeoff. Original policies are preserved.

The input task manifest declares the new command/reward settings, while the
input weights and normalization remain the parent's. New saved checkpoints
record actual PPO continuation steps. No IMU firmware or motor commands are
included; this package is simulation training only.

## Verification and known limitation

27 CPU tests pass, including reward-isolation and command-observation checks.
The configured GPU reward/command check verifies identical physical rollouts
under prescribed actions, the intended reward changes, and no hot-loop host
tensor reads. The separate legacy check_cuda.py CPU/single-world versus GPU/
batched trajectory gate fails its 0.05 maximum raw-observation tolerance on
both the unchanged parent and this configuration, with the identical error
sequence (maximum about 0.08495). That broad equivalence gate remains unresolved;
its tolerance was not relaxed. Training and its baseline/evaluation all use the
CUDA implementation. Do not treat CPU playback as numerically equivalent or
these results as hardware-deployment validation. Diagnostic logs are included.
