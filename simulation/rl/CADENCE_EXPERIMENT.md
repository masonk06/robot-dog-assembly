# Small cadence continuation

Resume the preserved 9516896-step best-distance policy. Change only
gait_cycle_seconds from 3.0 to 2.85 (5% shorter period, about 5.3% higher cadence).
Keep target speed 0.01, tracking weight 1.25, stride/lift, residual scale/filter,
slip/landing penalties and PPO settings. This changes reference timing, not
the architecture, joint directions or physical calibration.

Frozen starting-policy evaluations (three 20-second trials):

| Cycle | Forward distance | Slip metric | Falls/resets |
| --- | ---: | ---: | --- |
| 3.0 s, original saved evaluation | 0.16017 m | 0.00013978 | 0/0 |
| 2.85 s, new local evaluation | 0.15684 m | 0.00016268 | 0/0 |
| 2.7 s, rejected larger change | 0.15158 m | 0.00018911 | 0/0 |

The quicker timing is initially worse in distance/slip. Training tests whether
small learned corrections adapt; it is not a guaranteed improvement. Preserve
the original and compare saved evaluations/playback rather than raw return.

The flat HPC ZIP includes selected weights and exact model/assets, so it does
not rely on a W&B download or restart learning from scratch. Use the existing
.venv-cuda. hpc_cuda_cadence.sh first evaluates the changed cadence and refuses
to train if the baseline falls, slide-resets, ends early or omits a leg.

Training uses 64 worlds, at most 12 million additional steps or 2700 seconds
(45 minutes), saves/evaluates about every 500000 steps, and writes runs/cuda-cadence.
The timer begins after setup; final checkpoint/evaluation adds a little time.
Keep the GPU allocation alive for the run and upload. No hardware is involved.
