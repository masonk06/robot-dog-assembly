# RoboDog

A custom 3D-printed quadruped with twelve STS3215 bus servos: CAD, calibrated
hardware tools, MuJoCo/Newton simulation and GPU-resident PPO training.

![RoboDog CAD assembly](cad/RoboDog_preview.png)

## Current progress

- Slow simulated walking with a four-beat reference and learned residuals.
- Newton physics, observations, rewards, normalization and PPO updates on CUDA;
  tested locally and on an OSU H100 GPU allocation.
- Best recorded checkpoint: approximately **16.02 cm forward in 20 seconds**,
  six steps per leg and no falls/sliding resets in three evaluation trials.
- **Rear-left calibration and supported motion transfer confirmed by the user.**
  The faster full-amplitude trial completed with verified torque release.
- Other legs need current calibration reconciliation. Full-body ground walking
  and closed-loop hardware policy deployment are not yet validated; no IMU is
  currently reporting body state to the controller.

## Project map

| Folder | Contents |
| --- | --- |
| [cad](cad/README.md) | Fusion snapshots, STL/STEP sources, placement/build tools |
| [frame V3](cad/frame_v3/README.md) | Separate electronics-packaging revision |
| [hardware](hardware/README.md) | IDs, current/historical calibration, live viewer and supported replay |
| [simulation/mujoco](simulation/mujoco/README.md) | Robot model, scripted previews and dynamics |
| [simulation/rl](simulation/rl/README.md) | CPU/Newton validation, CUDA PPO, evaluation and playback |
| [policies](policies/README.md) | Four selected weight/normalization backups and exact source archives |
| [reports](reports/sim2real/README.md) | Representative hardware tracking and simulator parity evidence |
| [status](docs/STATUS.md) | Current results, limitations and next steps |
| [HPC](docs/HPC.md) | Persistent environments, resume and checkpoint handling |

## Local setup and tests

Use Python 3.12. Install requirements-rl.txt for CPU simulation and training;
requirements-cuda.txt adds the pinned Newton/CUDA stack for compatible NVIDIA
hardware. Keep these environments separate if preserving an existing setup.

```bash
python -m venv .venv
# Activate the environment for your shell.
python -m pip install -r requirements-rl.txt
python -m pytest -q
```

pytest.ini lists only the safe unit-test modules. Hardware motion tools are not
run as tests. Read the [hardware guide](hardware/README.md) before connecting.

In a Newton-capable environment, play the preserved best-distance checkpoint:

```bash
python simulation/rl/play.py policies/best-distance --source simulation/mujoco
```

See [CUDA training](simulation/rl/CUDA_TRAINING.md) and [HPC notes](docs/HPC.md)
for continuation. New runs save separately; preserve normalization with weights.

## Physical calibration

The read-only viewer starts without connecting or moving motors:

```bash
python hardware/calibration_view.py
```

[Current rear-left calibration](hardware/calibrations/rear-left-current.json)
uses hip ID 8 = 1677 and knee ID 9 = 1572 neutral ticks. All four knee
model-to-encoder signs are -1. The supported replay tool requires an explicitly
reviewed generated plan and operator Start; it is not full-body policy deployment.

## Backup boundaries

Selected policies and frozen training sources are included so W&B artifact
cleanup does not erase the useful milestones. Full raw run directories, Python
environments, caches, transfer ZIPs and containers are excluded. Git does not
capture unsaved Fusion state or unexported remote HPC files. The CAD preview
and historical snapshots retain revision-specific context.

No license has been selected. Third-party geometry retains its ownership/terms.
