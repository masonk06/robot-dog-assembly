# 23 mm stride continuation

Continue from the final 21 mm policy in W&B run d08cd5td, step 19,167,072.
Change only reference_stride from 0.021 to 0.023 meters: 9.5% more reference
foot sweep. Retain the 3.0-second cycle, target speed, rewards, residual filter,
normalization, model and learned weights. Preserve both preceding policies.
This is a simulation experiment; it does not command hardware.

The 21 mm policy's saved evaluation traveled 0.16804 m in 20 seconds, with
slip score 0.00014087, six useful steps per leg and no falls/sliding resets.
The package includes a local frozen-policy evaluation at 23 mm for comparison.
That three-episode check traveled 0.18236 m in 20 seconds (8.5% farther), with
slip score 0.00014477 (2.8% higher), six useful steps from each leg, and no
falls/sliding resets. Peak landing speed remained 0.15050 m/s. These results
precede further training and do not establish robustness beyond these trials.
Initial geometry effects and improvement from additional learning should be
reported separately. A larger reference sweep does not guarantee faster travel.

Upload robot-dog-stride-23mm.zip to your HPC home folder, then run:

```bash
cd ~
unzip -o robot-dog-stride-23mm.zip -d robot-dog-newton
cd ~/robot-dog-newton
nohup bash hpc_cuda_stride23.sh > stride23.log 2>&1 < /dev/null &
tail -F stride23.log
```

Use the existing .venv-cuda. The launcher evaluates the starting policy at
23 mm and checks finite metrics, no falls/sliding resets, full episode duration,
and participation from every leg before starting training. It trains 64 worlds
for at most 12 million additional steps or 2700 seconds (45 minutes), saving
and evaluating about every 500,000 steps under runs/cuda-stride23. Setup and
final saving/upload take additional time. Keep the GPU allocation active.
Check that another training job has finished before launching this experiment.
Ctrl+C exits tail, not the background trainer.

Compare distance, slip, landing speed, all-leg participation, falls/resets and
playback against the saved 21 mm baseline. The original checkpoint manifests
in stride23-checkpoint/ remain unchanged; the CLI override is recorded in the
new run's task manifests and W&B configuration.
