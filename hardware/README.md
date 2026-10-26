# Hardware and calibration

STS3215 servos connect through a Waveshare Bus Servo Adapter (A) with a 12 V supply. These Python utilities use the PC serial bus directly.

| Reference | Purpose |
| --- | --- |
| [servo_id_map.md](servo_id_map.md) | ID assignments and direction observations |
| `physical_neutral_pose.json` | User-confirmed physical neutral waypoint |
| `neutral_pose.json` | Earlier centering reference |
| `manual_range_of_motion.json` | Manually collected observations |
| `joint_safety_config.json` | Provisional pose-dependent constraints |

## Tools

- Status: `servo_usb_scan.py`, `servo_read_status.py`, `inspect_servo_registers.py`.
- IDs: `assign_servo_id.py`, `assign_knee_id.py`.
- Calibration: `record_manual_limits.py`, `calibrate_front_left_manual.py`, `calibrate_remaining_legs_manual.py`.
- Motion experiments: `single_leg_trot.py`, `rear_left_ik_trot.py`, `probe_hip_roll.py`, and `test_*.py`.
- Dry-run translation: `sim2real_lateral_pair_plan.py` prints a plan without opening the port.

Several scripts have top-level serial actions and hardcoded ports/IDs. Read before executing; do not batch-run or import them as tests. The `test_*.py` names describe physical experiments, not unit tests.

After checking the port, a read-only scan is:

```sh
python hardware/servo_usb_scan.py COM5
```

Install root `requirements.txt`. The ignored root `.servo_tools/` is an optional local pyserial installation. Secure the robot for motion, keep legs clear, and review interference before using recorded limits.
