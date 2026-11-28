# Starting Walking IK Gait

Accepted by the operator on November 27, 2026 as the reference for future IK
work, after reporting that the motion looked good in the supported-test workflow.
This is an operator observation, not validation of unsupported walking.

Run from the repository root on the Pi:

```bash
python3 hardware/starting_walking_ik_gait.py
```

The named entry point fixes the accepted baseline:

- 30 mm total fore-aft foot stroke, 15 mm lift.
- Four-second cycle, 144 Hz target sampling (576 intervals, 577 rows including
  the closing endpoint).
- Rear left, front right, rear right, front left swing order; one swing leg at
  a time, zero hip-roll sway.

Optional `--cycles` and `--output-dir` select repetition count and a new output
directory. Timing/stride/lift arguments cannot override this named baseline.
Use `generate_pi_crawl.py` directly for subsequent parameter experiments.
Outputs are model radians in timestamped `runs/pi-crawl/` folders; existing
outputs are never overwritten. No serial port is opened and no torque enabled.

Dependencies are `hardware/generate_pi_crawl.py`,
`simulation/p2s_crawl/generate_ik_crawl.py`, and
`simulation/p2s_crawl/generate_ik_diagnostic.py`; generation uses Python's
standard library only.

Local validation checked IK reachability, active MuJoCo model import and all
577 forward-kinematic poses, model joint limits, timing and cycle closure.
Conversion against the saved calibration records passed with a 15-tick margin.
Maximum joint displacement was approximately 0.365 radians and maximum
adjacent encoder target change was six ticks. The generator's 0.40-radian
envelope is an offline check, not a replacement for physical limits.

For later supported replay, follow [GETTING_DOG_RUNNING.md](GETTING_DOG_RUNNING.md):
use verified all-joint mapping and conservative limits, fresh receiver feedback,
feet clear, an accessible physical cutoff, and confirmed torque release.
Only one process may own the ESP32 port; stop the telemetry-only ROS bridge
before replay. This baseline does not change firmware, servo limits, or policy
observations. Actual 144 Hz hardware timing and dynamic balance are unverified.
