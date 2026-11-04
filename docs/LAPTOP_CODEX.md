# Luca on a second laptop

The canonical repository is:

```text
https://github.com/masonk06/robot-dog-assembly.git
```

Clone it, create a clean Python 3.12 virtual environment, and install the CPU
requirements:

```powershell
git clone https://github.com/masonk06/robot-dog-assembly.git
cd robot-dog-assembly
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-rl.txt
python -m pytest -q
```

## Orientation for a new Codex chat

Tell Codex that this is Luca, a 12-STS3215 quadruped. The project has:

- `cad/frame_v7`: latest frame, Pi/electronics packaging, and camera mast;
- `hardware`: ESP32 receiver, calibration records, IMU tools, and supported
  replay utilities;
- `simulation`: MuJoCo/Newton physics and PPO training tools;
- `docs/sim-to-real`: supported simulation-to-real evidence; and
- `revision_four_leg`: review-only power-distribution board source.

The present prototype has temporary mass distribution. Its measured load split
was 570 g front / 800 g rear, putting the temporary COM about 19 mm rearward of
the front/rear midpoint. Keep existing policies and simulations intact; use the
quasi-static robustness track rather than fitting a final walking policy to the
temporary frame.

## Safety and repository boundaries

The laptop can inspect, edit, run tests, simulate, and prepare replay plans.
Do not run a physical motion command unless the operator deliberately connects
the appropriate serial port, secures the robot, and supplies `--execute`.
Do not change physical torque/current limits as part of simulation work.

`runs/`, `wandb/`, local environments, caches, and terminal logs are excluded
because they are regenerable or machine-specific. Selected policies, source
archives, simulation results, CAD, calibration data, firmware, videos, and
electrical design files are included in Git.

The `manufacturing` package and `revision_four_leg` contain explicit hold/review
notes. They are versioned so design work can continue on another laptop; their
presence does not authorize ordering a PCB.
