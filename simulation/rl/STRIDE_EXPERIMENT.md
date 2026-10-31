# Small stride continuation

Resume the preserved 9,516,896-step best-distance policy from run 58cjy6ku.
Change reference_stride from 0.020 to 0.021 meters (5% more foot sweep).
Keep the original 3.0-second cycle, target speed 0.01 m/s, tracking weight 1.25,
foot lift, residual scale/filter, reward terms, model and PPO settings.
This preserves learned weights and normalization. It does not change physical
servo calibration or run the hardware.

The cadence experiment jwmozh4a stayed stable but its best distance improved
only 0.6% over the previous best. This experiment starts from that previous
best with its original timing, so only stride changes.

Frozen starting-policy check, three 20-second local CUDA trials at 21 mm:

- Mean forward distance: 0.16645 m (previous saved 20 mm result: 0.16017 m).
- Foot-slip score: 0.00014169 (previous saved result: 0.00013978).
- No falls or sliding resets; six useful steps per leg.

These are initial simulation checks, not evidence that further training has
improved the policy. Compare checkpoints by evaluation distance, slip, landing
speed, falls, all-leg participation and playback, rather than raw return.

The ZIP includes stride-checkpoint/ with policy and normalization, stride-source/
with the exact XML/assets, the CUDA implementation and hpc_cuda_stride.sh.
Use the existing .venv-cuda; no environment reinstall is needed.

On HPC, upload robot-dog-stride-21mm.zip into the home directory, then run:

```bash
cd ~
unzip -o robot-dog-stride-21mm.zip -d robot-dog-newton
cd ~/robot-dog-newton
nohup bash hpc_cuda_stride.sh > stride.log 2>&1 < /dev/null &
tail -F stride.log
```

The launcher first evaluates the changed stride and refuses training if it
falls, slide-resets, ends early or omits a leg. It then trains 64 parallel
worlds for up to 12 million additional steps or 2700 seconds (45 minutes),
saving/evaluating about every 500,000 steps into runs/cuda-stride. Setup and
final saving/evaluation add time beyond the training timer. Keep the GPU
allocation active through the final upload. Ctrl+C exits tail, not training.
