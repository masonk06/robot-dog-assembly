# 24 mm stride comparison

Continue from the final 21 mm policy in W&B run d08cd5td, step 19,167,072.
Change only reference_stride from 0.021 to 0.024 meters (14.3% more foot sweep).
Use the same starting weights as the 23 mm experiment so the geometry changes
can be compared. This does not include learning from a subsequent 23 mm HPC run.
Retain the original 3.0-second cycle and all other task and PPO settings.
Preserve earlier policies; this experiment does not command hardware.

The ZIP includes stride24-local-baseline.json and stride23-local-baseline.json,
evaluated with the same frozen 21 mm weights in three 20-second trials each.
The original 21 mm evaluation is in stride24-checkpoint/evaluation.json.

| Reference sweep | Distance in 20 s | Slip score | Peak foot force |
| --- | ---: | ---: | ---: |
| 21 mm, saved final policy | 0.16804 m | 0.00014087 | 13.82 N |
| 23 mm, frozen starting weights | 0.18236 m | 0.00014477 | 14.21 N |
| 24 mm, frozen starting weights | 0.18623 m | 0.00014525 | 14.61 N |

All checks completed the episode with six useful steps per leg and no falls or
sliding resets. At 24 mm, distance increased 2.1% versus 23 mm, while slip score
increased 0.3% and peak foot force 2.8%. This is before further training.

No falls is only one criterion: compare forward distance, slip, landing impact,
all-leg participation and playback. Short trials do not establish robustness.

Upload robot-dog-stride-24mm.zip to your HPC home directory, then run:

```bash
cd ~
unzip -o robot-dog-stride-24mm.zip -d robot-dog-newton
cd ~/robot-dog-newton
bash hpc_cuda_stride24.sh
```

Keep the terminal and GPU allocation open. Use the existing .venv-cuda.
Finish the preceding experiment before launching another trainer in the same
allocation. The launcher evaluates 24 mm first and checks finite metrics, full
duration, all legs participating, no falls and no sliding resets. Training uses
64 worlds for at most 12 million additional steps or 2700 seconds (45 minutes),
with checkpoints/evaluations about every 500,000 steps under runs/cuda-stride24.
Setup and final saving/upload take additional time. The stride override is
recorded in new manifests and W&B configuration, while bundled source weights
and checkpoint manifests remain unchanged.
