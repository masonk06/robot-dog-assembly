# RoboDog STS3215 Servo IDs

Verified assignments as of 2026-10-23. All assignments were made with each servo isolated on COM5 at 1 Mbps; no motion commands were sent.

| Position | Joint | Servo ID | Status |
| --- | --- | ---: | --- |
| Front-left | Hip roll | 1 | Previously verified |
| Front-left | Hip pitch | 2 | Previously verified |
| Front-left | Knee pitch | 3 | Previously verified |
| Front-right | Hip roll | 4 | Verified |
| Front-right | Hip pitch | 5 | Verified |
| Front-right | Knee pitch | 6 | Verified |
| Rear-left | Hip roll | 7 | Verified |
| Rear-left | Hip pitch | 8 | Verified |
| Rear-left | Knee pitch | 9 | Verified |
| Rear-right | Hip pitch | 10 | Verified; this was assigned before the hip-roll servo by mistake |
| Rear-right | Hip roll | 11 | Verified; assigned after hip pitch |
| Rear-right | Knee pitch | 12 | Verified |

## Important correction

Rear-right hip pitch intentionally keeps ID 10. IDs are arbitrary on the serial bus, so no reassignment was needed.

## Current model-to-servo knee mapping

Corrected by the user's live comparison on 2026-10-26: front-left knee ID 3
and front-right knee ID 6 both use **-1**, matching the existing rear-knee
conversion. The shared source is `joint_mapping.py`.

| Model joint | Servo ID | Model angle → encoder delta sign |
| --- | ---: | ---: |
| Front-left knee pitch | 3 | -1 |
| Front-right knee pitch | 6 | -1 |
| Rear-left knee pitch | 9 | -1 |
| Rear-right knee pitch | 12 | -1 |

`ticks = physical_neutral_ticks + sign × model_degrees × 4096 / 360`.
Viewer inversion uses the same sign. This maps hardware to the existing model;
simulation joint axes and learned policies retain their original coordinates.

## Historical raw-encoder motion observations

The following records describe increasing **raw ticks**, not increasing model
angles. They are retained as observations; use the conversion above for model
commands. The older front-knee model-sign +1 assumption is superseded.

| Servo ID | Joint | Positive-command direction | Test result |
| ---: | --- | --- | --- |
| 2 | Front-left hip pitch | Leg swings backward | +114 ticks (~10 degrees), returned, torque released |
| 1 | Front-left hip roll | Leg swings to robot-right | +114 ticks (~10 degrees), returned, torque released |
| 3 | Front-left knee pitch | Leg extends away from body | +114 ticks (~10 degrees), returned, torque released |
| 4 | Front-right hip roll | Leg swings to robot-right | +114 ticks (~10 degrees), returned, torque released |
| 5 | Front-right hip pitch | Leg swings backward | +114 ticks (~10 degrees), returned, torque released |
| 6 | Front-right knee pitch | Leg extends away from body | +114 ticks (~10 degrees), returned, torque released |
| 7 | Rear-left hip roll | Leg swings to robot-left | +114 ticks (~10 degrees), returned, torque released |
| 8 | Rear-left hip pitch | Leg swings backward | +114 ticks (~10 degrees), returned, torque released |
| 9 | Rear-left knee pitch | Leg bends toward body | +114 ticks (~10 degrees), returned, torque released |
| 11 | Rear-right hip roll | Leg swings to robot-left | +114 ticks (~10 degrees), returned, torque released |
| 10 | Rear-right hip pitch | Leg swings backward (inferred) | -114 ticks moved forward, returned, torque released |
| 12 | Rear-right knee pitch | Leg bends toward body (inferred) | -114 ticks extended away, returned, torque released |
