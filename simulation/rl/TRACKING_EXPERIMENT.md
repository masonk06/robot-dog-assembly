# Tracking-weight continuation

Resume frozen checkpoint w2p0ffha, not a fresh policy. Change only
tracking_reward_weight from its backward-compatible default 1.0 to 1.25.
The target speed, reference gait, action limits, slip/landing costs, architecture,
optimizer state and observation normalization are retained. Existing checkpoints
without this field still replay with weight 1.0.

The CUDA launcher runs 262144 additional steps across 64 worlds and saves/evaluates
every 65536 steps. Task configuration is written into both the source artifact
and each checkpoint, so evaluation uses the changed objective consistently.

Original baseline: 20-second evaluations averaged 0.105320 m forward, 6 steps
per leg, no falls or slide resets, mean slip metric 0.000318567 m^2/s^2.
Judge the continuation by physical metrics/playback, not raw reward across
different weight settings. A larger tracking reward does not guarantee progress.

Upload/unpack the ZIP into the existing ~/robot-dog-newton folder, then run:

    bash hpc_cuda_tracking.sh

No new dependencies or environment installation are needed. The launcher
downloads the immutable latest w2p0ffha artifact pair to a separate input folder
and retains the original policy. Results go under runs/cuda-tracking and W&B.
