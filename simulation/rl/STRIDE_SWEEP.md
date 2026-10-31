# Frozen-weight stride search

Start from the preserved 25.5 mm configuration of the best 24 mm learned policy
(mmtw7dxi, step 28,309,344). The policy weights and normalization stay fixed.
Keep the 3-second cycle, 1 cm/s command, foot lift, reward weights and geometry.
This finds a useful reference setting; it does not demonstrate new learning or
tracking of additional speed commands.

Run with the existing CUDA environment:

```powershell
.venv-newton\Scripts\python.exe -u simulation/rl/sweep_stride.py --checkpoint runs/goal-1cms-255/checkpoint --source runs/goal-1cms-255/source --output runs/stride-sweep-20261027
```

The search rechecks 25.5 mm, then tests 26, 27, 28 mm and so on in three matched
60-second worlds (batch seed 10000). It stops on the first less than 0.5% speed
gain or unacceptable gait quality, and checks one intermediate stride when
possible. Each candidate first samples the CPU reference at 601 cycle phases
to reject unreachable foot targets and configured joint-limit violations; this
avoids treating clipped inverse kinematics as a valid longer stride.

Practical comparison budgets, fixed relative to the 25.5 mm starting gait:

- No falls, sliding resets or early-ending trials; every leg must contribute.
- At most 25% more slip score, 20% more peak foot force, and 20% more peak
  landing speed (these peak metrics are means of each trial's peak).
- At least 0.5% more net forward speed than the preceding accepted best.

These budgets are experimental selection rules, not physical motor limits or
proof that no better stride exists beyond the first rejected candidate.
The initial search bound is 60 mm. Reaching it is reported as a bound, not a
found optimum. Candidate processes are isolated to release GPU allocations.

The selected setting is checked in five additional 60-second worlds with batch
seed 20000 and a matched 25.5 mm control. If it fails those checks, the search
falls back through preceding accepted candidates. Individual trial data,
rejection reasons, source/model, and a portable best/ checkpoint are saved and
uploaded to W&B as an evaluation run with zero new training steps. No hardware
is controlled, and the original checkpoints remain intact.
