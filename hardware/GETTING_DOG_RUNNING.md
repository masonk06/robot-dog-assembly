# From calibration to the first safe robot test

This is the current practical sequence for the new frame and NodeMCU ESP32S. It intentionally separates **read-only validation** from powered motion.

## 1. Hardware baseline

- Servo bus: Waveshare Bus Servo Adapter (A), jumper at **A**, 12 V servo supply, common ground.
- Controller: NodeMCU ESP32S. Servo UART is GPIO17 TX / GPIO16 RX through the adapter; PC USB is normally COM7 at 115200 baud.
- Never power the ESP32 or MPU board from the 12 V servo supply.
- Keep an accessible physical power cutoff. Do not work near pinching joints.

Current physical IDs, in model joint order:

| Leg | Hip roll | Hip pitch | Knee pitch |
| --- | ---: | ---: | ---: |
| Front left | 4 | 5 | 6 |
| Front right | 1 | 2 | 3 |
| Rear left | 7 | 8 | 9 |
| Rear right | 11 | 10 | 12 |

## 2. Collect zero poses, directions, and limits

The current approximate model-zero ticks are in [`calibrations/zero-points-current.json`](calibrations/zero-points-current.json). They are not factory centers and must not be replaced with a generic 2048 value.

For a new capture, use the receive-only tools:

```powershell
.venv\Scripts\python.exe hardware\esp32_zero_view.py
.venv\Scripts\python.exe hardware\esp32_joint_check_view.py
```

Follow [ESP32_ZERO_CHECK.md](ESP32_ZERO_CHECK.md) and [ESP32_DIRECTIONS_LIMITS.md](ESP32_DIRECTIONS_LIMITS.md). Preserve timestamped captures; do not overwrite prior observations.

The hand-direction observations are in [`calibrations/manual-physical-directions-20261028.json`](calibrations/manual-physical-directions-20261028.json). They still require the screen-mirror verification below. Conservative physical endpoints are also still required before powered replay.

## 3. Confirm simulation-to-encoder correspondence without commanding motors

Close every other COM7 consumer, then run:

```powershell
.venv\Scripts\python.exe hardware\esp32_live_mirror.py
```

Follow [READ_ONLY_LIVE_MIRROR.md](READ_ONLY_LIVE_MIRROR.md). Move one torque-off joint by hand at a time. The simulated live leg must move the same way as the physical leg. This application cannot command servos.

If a joint mirrors backward, stop and correct the direction record before any future command conversion. Do not compensate by swapping wires, changing a servo ID, or redefining an arbitrary zero.

## 4. Requirements before a supported powered test

1. The live mirror matches all 12 physical joints.
2. Each joint has conservative non-wrapping encoder endpoints with clearance from hard stops and frame interference.
3. A dedicated ESP32 command transport exists with explicit arm/start/stop, fresh feedback, target bounds, and a communication watchdog. The current CSV sketch is telemetry-only and is **not** this transport.
4. The robot is secured with feet clear and a person can reach the physical cutoff.
5. Start with a tiny, one-joint or one-supported-leg reference motion. Do not send a full walking policy first.

## 5. Before ground walking

Ground walking additionally needs a mounted/calibrated IMU, correct robot-axis mapping, fall handling, conservative torque/velocity settings, and a gradual stand-to-step progression. The simulation policy has only been validated in simulation; it is not yet authorized for free ground deployment.

See [SIM2REAL_HANDOFF.md](SIM2REAL_HANDOFF.md) for the policy checkpoint, observation contract, command-rate requirements, and known limitations.
