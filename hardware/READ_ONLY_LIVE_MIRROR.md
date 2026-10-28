# Read-only live simulation mirror

This is the safe bridge between hand calibration and the first supported motion test. It renders a simulation reference with every joint at 0 degrees beside the latest ESP32 encoder mirror.

`esp32_live_mirror.py` is receive-only. It opens the ESP32 USB console at 115200 baud with DTR and RTS disabled and parses `servo,...` CSV lines. It cannot write a servo goal, enable torque, change an ID, change EEPROM, or upload firmware.

## Before opening it

1. Support the dog with its feet clear and keep hands away from the joints.
2. Confirm every servo reports **torque OFF** before moving a joint by hand.
3. Close Arduino Serial Monitor, the zero-capture window, and any other program using COM7.
4. Confirm the ESP32 is running the CSV telemetry sketch and COM7 is the correct Windows port.

## Start

From the repository root in PowerShell:

```powershell
.venv\Scripts\python.exe hardware\esp32_live_mirror.py
```

Choose `COM7` if needed and click **Connect CSV 115200**. Wait for rows to show `LIVE`. The current round-robin telemetry sketch reports each servo about once per 1.2 seconds, so pause briefly after moving a joint.

## Verify a joint

Move one supported, torque-off joint only a few degrees by hand. The matching leg and joint in the live-rendered robot should move in the same physical direction. Return it to the starting pose before selecting another joint.

`NO DATA` means the ESP32 is not producing servo CSV. `STALE` means the USB stream stopped. `SERVO STATUS ...` means stop moving that joint and investigate its reported status. The mirror clamps its display to MuJoCo model ranges; that is a display safeguard, not a physical limit.

The live mirror is a validation tool only. A visually correct mirror does not establish travel limits, command safety, balance, or permission to walk.
