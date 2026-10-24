# RoboDog Assembly

CAD assembly, source geometry, MuJoCo model, and hardware bring-up tools for the RoboDog quadruped.

## Contents

- `RoboDog.f3d` — Fusion 360 assembly.
- `revision_sources/`, `solid_sources/`, and `source/` — original and converted mechanical source files.
- `mujoco_v2/` — MuJoCo model and viewer.
- `servo_id_map.md` — physical joint-to-servo-ID map and direction observations.
- `physical_neutral_pose.json` — user-confirmed as-built neutral controller waypoint.
- `joint_safety_config.json` — temporary, pose-dependent software safety constraints and collision observations.
- `*_servo*.py`, `test_*.py`, and `sweep_*.py` — serial-bus diagnosis and controlled test utilities.

## Hardware safety

All motion tests are intended for a secured robot on a stand. Servo torque is disabled after each test. Do not use broad independent joint limits as a collision guarantee: the front-left hip-pitch/frame interference requires a coordinated trajectory.

## Current servo IDs

IDs 1–12 are assigned. See `servo_id_map.md` for the full mapping.
