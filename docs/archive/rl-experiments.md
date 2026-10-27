# Historical RL experiments

These notes preserve earlier experiments, not current setup instructions. See simulation/rl/README.md and docs/STATUS.md for the active workflow.

# Slow walking with PPO

## Version 7: conservative residual training

Fresh version 7 training limits residuals to 0.035 radians (2 degrees), filters
them with a 0.12-second time constant, and starts exploration with log standard
deviation -2 (standard deviation 0.135 in action units). PPO uses learning rate
0.0001 and target KL 0.015. The reference gait, slip costs, resets and version 6
step accounting remain. Filtering resets each episode. Use a fresh policy for
this comparison; resuming an old policy retains its optimizer/exploration state.

## Version 6: credit complete stepping cycles

Version 6 measures net forward body displacement between consecutive landings
of each foot, requiring more than 0.5 mm. It retains the existing support,
airtime, clearance, foot travel, cooldown and sliding checks. Brief backward
motion or slowdown at touchdown no longer rejects an otherwise useful cycle.
Versions 1–5 retain their original instantaneous speed gate for reproducible replay.
The seeded 20-second reference now credits six steps per leg, with unchanged
motion (0.1025 m forward). This corrects reward accounting, not trained behavior.
Use fresh training for the next comparison against the unsuccessful version 5 run.

## Current default: version 5 residual PPO

The controller computes a slow four-beat foot trajectory, solves hip/knee IK
using each leg's own model dimensions, and adds the learned action scaled by
0.12 radians (about 6.9 degrees). Desired targets are joint-limited and rate-limited.
Hip roll provides a small reference weight shift; residuals may adjust all 12 joints.
There is a smooth one-second reference ramp from the neutral starting pose.

The initial speed command is 0.01 m/s, cycle time 3 s, reference stride 20 mm,
and Cartesian lift 25 mm (37.5 mm on the shorter rear linkage). These are target
trajectories, not achieved foot clearances. The existing model, actuator force
caps and measured joint ranges are retained. Observations now have 60 values:
the original state, rhythm sin/cos, and twelve reference joint targets.

Start fresh: old 46/48-input weights cannot be resumed into this 60-input policy.
Version 5 checkpoints resume normally. The original direct policies remain available.

Reference screening uses full gravity/contact dynamics, without hardware access:

```sh
python simulation/rl/screen_reference.py
```

In the initial seeded 20 s zero-residual test, the scaffold stayed upright, had
no severe-slip reset and advanced about 0.10 m; it produced 7 front-left and
6 front-right credited steps, but zero rear credited steps. Thus it is an
experimental starting scaffold, not a verified four-leg walking solution.
Residual training must improve rear participation, forward speed and traction.
`screen_reference.py --sweep` runs optional parameter experiments; it does not
automatically change defaults or certify their results.

Train with the standard `train.py` command; in a compact HPC bundle use
`bash simulation/rl/hpc_train.sh`. A fresh 200k-step run logs to W&B. The initial
baseline report is saved and uploaded with the source artifact. Reward terms
remain those of version 4, plus a small penalty on unnecessarily large residuals.
Playback automatically combines the saved reference with policy corrections.

## Previous version 4 patterned walk

Version 4 starts a fresh 48-input network: the original 46 observations plus
sin/cos rhythm inputs. One 2.4 s cycle requests rear-left, front-left,
rear-right, then front-right swings, each occupying 20% of the cycle, leaving
brief all-feet-supported intervals. Reset randomizes the initial rhythm phase.
It is a soft reward target, not prescribed joint trajectories.

Rewards combine forward-speed tracking (0.03 m/s), forward motion, real foot
lifts (0.75 per event), phase-correct lifts (0.25), contact pattern (up to 0.2
per action), swing clearance matching an 8 mm sinusoidal target (up to 0.8),
and the existing complete-step/four-leg bonuses. Meaningful lift events retain
support/airtime/relocation checks and are paid only once per swing.

Continuous planted-slip cost is `-2 * clip(mean_squared_foot_speed / 0.03**2,
0, 10)`. Airborne foot speed is excluded; average is across all four feet.
Tiny numerical slip has a small cost. Significant slip can outweigh tracking
and progress, whose combined maximum is 2 per action. Balance, smoothness,
effort and hard-landing penalties remain.

Resets now require 0.5 s of sustained excessive planted-foot movement:
more than 20 mm stance drift or 0.08 m/s horizontal speed, after the existing
0.30 s settling grace. Brief slips receive penalties without ending an episode.
Falls still terminate normally. These thresholds are initial experiment settings.

Start fresh (do not use a version 1–3 checkpoint with the new observation size):

```sh
python simulation/rl/train.py --source source --parallel --envs 6 --torch-threads 2 --steps 200000 --project robot-dog-rl
```

The `--source source` argument is for compact HPC bundles. In the full local
repository omit it to use `simulation/mujoco/robot_dog_v2.xml`. The model's joint
geometry, limits, collision proxies and torque caps are unchanged. Older
checkpoints remain playable with their saved 46-input configurations; upgrading
them to version 4 is explicitly rejected instead of silently misloading weights.
Version 4 checkpoints can be resumed normally.

W&B records the rhythm configuration, individual reward terms, contact/clearance
match, foot lifts, full stepping cycles, slip resets, speed, and falls. Standing
can achieve a high contact-match score alone, so assess it together with swing
clearance, per-leg step counts and forward progress. Training success requires
playback review, not just a high scalar reward.

## Previous version 3: lift rewards and sliding resets

New runs and `--upgrade-rewards` use version 3. Each foot earns a one-time 0.25
lift bonus after prior support, 8 mm clearance, 4 mm horizontal relocation and
at least 0.08 s airtime. Hovering cannot earn repeated bonuses. A lift alone
does not earn the existing four-leg lift-and-touchdown bonus.

After 0.30 s reset grace, feet planted for at least 0.08 s trigger a reset if
drift exceeds 4 mm or horizontal speed exceeds 0.04 m/s for 0.08 s continuously.
Contact gaps under 0.04 s are debounced. Sliding terminates the episode with
a -5 penalty and no speed/progress reward on that action. Training resets
automatically; airborne foot motion is excluded.

These are simulation tolerances, not hardware limits. Foot collisions still
use sphere proxies rather than physical sole shapes. W&B reports sliding
reset fraction separately from falls, plus episode duration.

Checks: the old final policy triggered resets in 3/3 seeded episodes (mean
0.378 s). Zero joint targets ran 20 s without slipping. Six tests passed.
This validates the detector, not a new walking gait.

This is a learned joint-position policy, separate from the scripted gait in
`simulation/mujoco/`. Default command: 0.03 m/s forward (negative local X).
Physics runs at 500 Hz, the policy at 50 Hz. The floating base is free.
The supplied XML joint ranges and 1 Nm actuator force caps are preserved.
Actions are offsets of up to 0.35 radians from the zero-angle stance, clipped
to joint ranges and rate-limited to 1.5 rad/s. These are simulation parameters,
not a new physical servo calibration.

## Install and authenticate (PowerShell, repository root)

```powershell
# Use Python 3.12 in an isolated environment.
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements-rl.txt
.venv\Scripts\wandb.exe login
```

Complete authentication locally. Never put API keys in code, Git, or chat.

## Train

```powershell
.venv\Scripts\python.exe simulation/rl/train.py --steps 200000 --envs 4 --project robot-dog-rl
```

Use `--entity TEAM` to select a team, or omit it for your W&B default entity.
CPU training is intentional for this small MLP and ordinary CPU MuJoCo.
`--mode offline` records everything locally if you are not signed in;
`wandb sync "wandb/offline-run-..."` uploads it after login.
W&B upload is only confirmed when syncing completes and a run URL is available.

The first run is experimental, not a promise of walking within 200k steps.
Watch evaluation speed, displacement and falls, rather than training reward alone.
The objective rewards target-speed tracking and forward motion, penalizing tilt,
lateral/vertical motion, rotation, effort, abrupt actions and falls. It does not
yet require a particular footfall pattern, so sliding or other reward exploits
must be checked in playback.

### Reward version 2: gentle landings and four-leg participation

Version 2 introduced foot participation. Foot forces and velocities are sampled every physics
step (2 ms), rather than only once per policy action. Downward touchdown speed
above 0.15 m/s and normal forces above three times the nominal per-foot static
load incur a penalty. Planted-foot sliding is penalized as well. These are
initial tuning thresholds for this simulated robot, not measured impact limits.

A useful step requires prior ground support, at least 0.12 s of airtime, 4 mm
of clearance above liftoff, and 4 mm of horizontal relocation. Credit is gated
on forward body movement above 25% of the requested speed and has a 0.5 s
per-leg cooldown. Initial drops, hovering, standing and stationary tapping earn
no step credit. Each useful step earns a small bonus; all four legs completing
a step within 12 s earns another bonus. A small penalty after the first 4 s
discourages leaving legs unused. No particular leg order is imposed.

W&B logs impact force, touchdown speed, sliding, per-leg evaluation step counts,
and complete four-leg cycles. Inspect these alongside speed and falls: reward
changes require additional learning and do not immediately change saved weights.

Fine-tune an older checkpoint with the new objective explicitly:

```powershell
.venv\Scripts\python.exe simulation/rl/train.py --resume "runs/slow-walk/TIMESTAMP-RUNID/final" --upgrade-rewards --steps 200000
```

Without `--upgrade-rewards`, resume preserves the saved reward version (old
checkpoints default to version 1). The original checkpoint is retained.

### More CPU workers / HPC

Use `--parallel --envs 4` to run four MuJoCo processes. On HPC request enough
CPU cores for those workers plus the learner, and stay within your allocation.
`--torch-threads 2` limits learner threading. A larger GPU alone does not speed
up this CPU MuJoCo implementation. Measure samples/sec before adding workers.

On another machine restore the policy artifact and its source artifact, then:

```sh
python simulation/rl/train.py --resume /path/to/checkpoint --source /path/to/source --parallel --envs 4 --steps 200000
```

The source override avoids relying on a Windows path saved in `source.json`.
Run under an allocated job, not on an HPC login node. Keep the same task,
observation/action order and model snapshot when continuing a policy.

## Checkpoints and W&B

Local files appear under `runs/slow-walk/TIMESTAMP-RUNID/` (ignored by Git).
Periodic `step-N/` bundles and `final/` contain:

- `policy.zip`: PPO actor, critic and optimizer state.
- `normalize.pkl`: observation and reward statistics needed for resume/replay.
- `environment.json`: settings, joint ordering/ranges and model hash.
- `source.json`: local source location and the corresponding W&B source artifact.
- `evaluation.json`: deterministic evaluation on three fixed seeds.

W&B receives versioned `robodog-policy-RUNID` model artifacts and a separate
`robodog-source-RUNID` artifact containing the exact XML, meshes, training source,
and package versions. The `latest` alias points to the last uploaded policy;
it is not necessarily the best policy. Source/weights are uploaded to your
selected W&B project; use its privacy settings to control access.

## Watch and resume

```powershell
.venv\Scripts\python.exe simulation/rl/play.py "runs/slow-walk/TIMESTAMP-RUNID/final"
.venv\Scripts\python.exe simulation/rl/train.py --resume "runs/slow-walk/TIMESTAMP-RUNID/final" --steps 200000
```

Playback opens MuJoCo and runs at real time, resetting at falls or episode ends.
Resume means additional timesteps and starts a new W&B run. Use trusted checkpoint
files only: PPO and normalizer files use Python serialization.
For another machine, download both artifacts; pass `--source DIRECTORY` to playback.
For resume, update the `path` in `source.json` to the downloaded source directory.

## Validation and scope

```powershell
.venv\Scripts\python.exe -m pytest simulation/rl/test_env.py -q
```

Tests check Gymnasium compatibility, deterministic reset, bounded targets,
and fall versus timeout handling. No training or test script opens a serial port.
Observations include simulated body velocity, which would require an estimator
for deployment. Existing simplified contact proxies/masses remain unchanged.
Physical deployment is a separate task.
