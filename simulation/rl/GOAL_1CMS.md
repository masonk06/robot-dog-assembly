# One centimeter per second: simulation check and continuation

Start from the best-distance 24 mm checkpoint in run mmtw7dxi, step 28,309,344.
Keep all four-leg participation rewards and the original 3.0-second stepping
cycle. Change only reference_stride to 0.0255 meters (6.25% above 24 mm).
This retains the learned weights, normalization, model and physical calibration.
It does not command hardware.

We checked the timing hypothesis with five 60-second trials per configuration:

| Reference sweep | Cycle | Mean net speed | Slip score |
| --- | ---: | ---: | ---: |
| 24 mm | 3.0 s | 0.9687 cm/s | 0.00013740 |
| 24 mm | 2.85 s | 0.9739 cm/s | 0.00016190 |
| 24 mm | 2.8 s | 0.9559 cm/s | 0.00016872 |
| 25 mm | 3.0 s | 0.9994 cm/s | 0.00014023 |
| 25.5 mm, ten trials across two batches | 3.0 s | 1.0141 cm/s | 0.00014240 |

All completed without falls/sliding resets. Shortening the cycle did not
meaningfully improve speed and increased slipping. The 25.5 mm setting completed
ten full-minute trials across batches seeded 10000 and 20000. Every trial
exceeded 1 cm/s, with a minimum of 1.0133 cm/s, 19-20 useful steps per leg, and
no falls/sliding resets. Its slip score was about 3.6% higher than the 24 mm
control, versus 18% higher with the 2.85-second cycle. Both raw reports and
the comparisons are in the package.
Net speed means displacement divided by elapsed simulated time,
including the starting ramp. Each report includes individual-world metrics;
worlds use one batch seed rather than independently assigned seed numbers.

These are frozen-policy evaluations after changing the reference geometry,
not additional learned progress. Flat-ground trials with small reset noise do
not establish robustness to pushes, varied terrain, model errors, or real motors.
The original policy/checkpoint remains intact.

To run a continuation on HPC, upload robot-dog-goal-1cms.zip to your home folder:

```bash
cd ~
unzip -o robot-dog-goal-1cms.zip -d robot-dog-newton
cd ~/robot-dog-newton
bash hpc_cuda_goal1cms.sh
```

The existing .venv-cuda is used. Five full-minute starting-policy checks run
before training. Training uses 64 worlds, up to 12 million additional steps or
45 minutes, with checkpoint evaluation every roughly 500,000 steps. Training
episodes stay 20 seconds; checkpoint evaluations now use five 60-second trials.
The new duration and stride are recorded in run configuration and manifests.
Keep the terminal/GPU allocation active through setup, training and final
upload. Finish any preceding trainer before launching this one.

Assess each saved checkpoint on all five individual trial speeds (target >=
0.01 m/s), no falls/resets, every leg contributing, slip and landing impact,
and playback. Reaching the speed target alone is not a reason to accept a
regression in gait quality.
