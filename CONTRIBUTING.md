# Contributing to Luca

Luca is a hardware-and-simulation learning project. Changes should preserve reproducibility and keep the physical robot safe.

## Before you start

- Read `README.md`, `docs/STATUS.md`, and the relevant component README.
- Use a descriptive branch such as `feature/imu-mapping` or `fix/telemetry-parser`; keep `main` releasable.
- Keep each change focused. Do not mix CAD, calibration, firmware, and policy changes without a clear reason.

## Hardware changes

- Treat `hardware/GETTING_DOG_RUNNING.md` as the physical-robot authority.
- Do not enable torque or command motion without an explicit supported test, accessible cutoff, secured robot, verified IDs/directions, and conservative non-wrapping bounds.
- Preserve raw telemetry, timestamped captures, and prior calibration records. Never replace a measured zero with a generic `2048` tick value.
- State whether a result is an observation, hypothesis, simulation result, or confirmed hardware evidence.

## Code and documentation

- Preserve the active P2S model and the policy's 60-observation contract unless retraining is included.
- Do not commit virtual environments, run caches, W&B working directories, or large temporary artifacts.
- Update documentation when pins, IDs, calibration interpretation, geometry, policy interfaces, or user-facing commands change.
- Run the narrowest relevant verification. Compile firmware; test or compile changed Python modules.

## Pull requests

Use the pull-request template. Record verification, limitations, and any hardware interaction.
