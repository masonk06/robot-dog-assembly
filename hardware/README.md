# Hardware and calibration

STS3215 servos connect through a Waveshare Bus Servo Adapter (A) with a 12 V supply. These Python utilities use the PC serial bus directly.

## Current workflow

Rear-left calibration and supported transfer were confirmed on 2026-10-26.
Use [rear-left-current.json](calibrations/rear-left-current.json): IDs 8/9 have
neutral ticks 1677/1572. The physical neutral file and viewer defaults reflect
that update; the original neutral capture remains in calibrations. Other legs
still need their historical bounds reconciled before powered full-body replay.

- calibration_view.py: read-only live/reference display and manual capture.
- prepare_policy_transfer.py: offline policy-target preview and range checks.
- supported_replay_view.py: explicit-start, monitored rear-left motion on a stand.
- [Supported replay guide](SUPPORTED_REPLAY.md): tested profiles and limitations.

The current controller acknowledges and verifies each selected-joint torque
release. No movement begins on opening its window. Temperature is shown/logged;
its software temperature abort is disabled per the user's request. Internal
servo protections remain unchanged. These supported tests do not deploy the
feedback policy or establish full-body ground walking.

| Reference | Purpose |
| --- | --- |
| [servo_id_map.md](servo_id_map.md) | ID assignments and direction observations |
| `physical_neutral_pose.json` | User-confirmed physical neutral waypoint |
| `neutral_pose.json` | Earlier centering reference |
| `manual_range_of_motion.json` | Manually collected observations |
| `joint_safety_config.json` | Provisional pose-dependent constraints |
| `joint_mapping.py` | Shared model-to-encoder knee directions; front IDs 3/6 corrected to -1 on 2026-10-26 |

## Tools

- Status: `servo_usb_scan.py`, `servo_read_status.py`, `inspect_servo_registers.py`.
- IDs: `assign_servo_id.py`, `assign_knee_id.py`.
- Calibration: `record_manual_limits.py`, `calibrate_front_left_manual.py`, `calibrate_remaining_legs_manual.py`.
- Motion experiments: `single_leg_trot.py`, `rear_left_ik_trot.py`, `probe_hip_roll.py`, and `test_*.py`.
- Dry-run translation: `sim2real_lateral_pair_plan.py` prints a plan without opening the port.
- Live comparison: `calibration_view.py` displays simulated reference and encoder pose side by side, read-only.

Model angles and raw encoder-positive movement are distinct. All knee model
angles currently map to encoder deltas with sign -1. Shared signs feed the
viewer defaults, IK motion experiment, and sim-to-real plan. Existing raw-tick
observations/neutral values are retained. Updating a display-only zero does not
silently change a motion script's physical neutral waypoint.

Historical ID/centering tools may have top-level serial actions and hardcoded
ports/IDs. Read before executing; do not batch-run or import them as tests.
The obsolete one-off physical test_*.py experiments and forced-return script
were removed; Git history preserves them. pytest.ini selects only the mock
calibration/replay tests and simulated environment tests, with no hardware I/O.

After checking the port, a read-only scan is:

```sh
python hardware/servo_usb_scan.py COM5
```

Install root `requirements.txt`. The ignored root `.servo_tools/` is an optional local pyserial installation. Secure the robot for motion, keep legs clear, and review interference before using recorded limits.
