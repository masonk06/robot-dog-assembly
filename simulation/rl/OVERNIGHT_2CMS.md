# Four-hour CUDA continuation toward 2 cm/s

This continues the existing policy and normalization from W&B run j6ett8qi
(iconic-dust-32), final cumulative step 36,943,712. Its five 60-second trials
averaged 1.141 cm/s with no falls or severe-slide resets. The original policy
and its exact source are included unchanged as a fallback. No hardware runs.

## Storage and launch

Use an H100 allocation with at least four hours remaining. The previously
checked `/nfs/hpc/share` was not writable. This package defaults to
`/scratch/$USER/robot-dog-rl`, which is local to the current compute node.
Scratch is working storage; W&B artifact uploads are the persistent backup.
The existing home `.venv-cuda` is reused without downloading another environment.

Upload `robot-dog-overnight-2cms.zip` to your HPC home, then:

```bash
cd ~/robot-dog-newton
unzip -o ~/robot-dog-overnight-2cms.zip
source ./hpc_storage.sh
nohup bash hpc_cuda_overnight.sh > "$DOG_WORK/overnight.log" 2>&1 &
echo $! > "$DOG_WORK/overnight.pid"
tail -F "$DOG_WORK/overnight.log"
```

Ctrl+C stops the log viewer; training continues. Keep the GPU allocation
active. `nohup` does not extend an allocation or survive its cancellation.
Use a new log filename if launching again so the previous log remains available.
The launcher refuses a recognized duplicate CUDA trainer.

`hpc_storage.sh` redirects checkpoint output, W&B logs, artifact staging and
cache, Warp/Python caches, pip cache, and temporary files away from home.
It also sets the correct W&B server. Credentials stay in the existing netrc.
If administrators provide a persistent writable shared directory, set
`export DOG_WORK=/actual/granted/path/robot-dog-rl` before sourcing it.

## Planned curriculum

| Stage | Command | Reference stride | Four-leg cycle | Training budget |
|---|---:|---:|---:|---:|
| 1 | 1.25 cm/s | 34 mm | 3.0 s | 35 min |
| 2 | 1.50 cm/s | 38 mm | 2.9 s | 50 min |
| 3 | 1.75 cm/s | 43 mm | 2.75 s | 60 min |
| 4 | 2.00 cm/s | 48 mm | 2.6 s | 75 min |

All use the current residual PPO controller with tracking weight 1.375 and
slip penalty weight 2.2. Foot lifting, four-leg participation, soft landings,
joint limits, action smoothing, and severe-slide resets remain in effect.
These are gradual task changes, not fresh randomly initialized policies.

Each stage starts from the fastest accepted checkpoint, including its saved
normalization and optimizer state. It saves approximately every million
transitions and at completion. Five full-minute trials evaluate checkpoints.
Before increasing the task, every trial must achieve at least 80% of its
current speed command. Failure repeats that stage in the next time slot;
the schedule does not force a failing gait to a faster command.

Selection rejects falls, severe-slide resets, early endings, or missing leg
participation. Every individual trial must stay above 95% of the original
baseline speed. Slip score may be at most twice the original baseline;
peak force and landing speed may be at most 1.5 times baseline. These are
experimental comparison budgets, not hardware safety or sim2real criteria.
Only candidates at least as fast as the current accepted policy replace it.

Training budgets total 220 minutes. The orchestrator targets at most 230
minutes including evaluation; a process-group timeout starts shutdown at
238 minutes and forces exit a minute later. Checkpoint evaluations and
W&B uploads can consume part of the budget. Output includes per-slot logs,
selection reasons, original/accepted/best policy-source pairs, and a final
held-out evaluation using seed 20000. `goal_2cms_met` is true only if every
held-out 60-second trial reaches 2 cm/s and passes the comparison checks.
Reaching that speed is an experiment, not a guaranteed four-hour outcome.

Training checkpoints/source artifacts upload to W&B under
`marsdenm-oregon-state-university/robot-dog-rl` as usual. A final
`overnight-2cms-summary` run uploads the comparison reports and selected
policy/source pair as `robodog-overnight-RUNID:latest`. Check for upload
errors and let W&B finish before releasing the node. An optional small
home copy of the summary is:

```bash
mkdir -p ~/robot-dog-reports
cp "$DOG_WORK"/runs/overnight-2cms/*/summary.json ~/robot-dog-reports/
```

Read `goal_2cms_met`, `heldout_speed_cm_s`, and rejection reasons before
calling the result successful. Policies can be downloaded from their W&B
model/source artifacts for later playback on this PC.

## Validation and limits

All four stride/cycle combinations pass 601-phase CPU inverse-kinematics
and joint-limit checks. The frozen starting policy at stage 1 completed
three 20-second CUDA trials at about 1.132 cm/s without falls or severe
slides; slip increased, motivating training and the comparison gates.
The local two-stage GPU smoke checks continuation, saving, source pairing,
evaluation, and selection. Its 0.2-second evaluations are plumbing tests,
not evidence of walking performance. CPU unit tests cover reward changes,
per-trial selection, and checkpoint cleanup.

The existing broad CPU/GPU observation comparison has an unresolved
maximum difference of about 0.085 at 31.5 mm, including unchanged original
source. Its tolerance has not been relaxed. This experiment uses CUDA for
both training and evaluation; CPU playback and real hardware require their
own validation. No four-hour local performance claim is made.
