# Overnight staggered lateral-gait experiment

Starts from the preserved overnight walking checkpoint (about 1.78 cm/s held-out). Training uses Newton/CUDA and PPO continuation. It gradually moves same-side swing phases closer from 0.25 to 0.12 of a cycle; it does not force simultaneous pacing. Target speed, stride and cycle remain unchanged initially so this experiment isolates gait timing.

Eight slots of up to 80 minutes are available. Each candidate must pass five 60-second simulation trials (no falls or severe sliding, at least 15 steps per leg, net speed at least 1 cm/s, mean slip cost below 0.0006 in each trial). Otherwise the stage repeats from the last accepted checkpoint. These are experiment-selection criteria, not hardware safety limits. The original policy is preserved in the package. No result is guaranteed.

The per-run checkpoints and matching sources upload to W&B. A summary artifact `robodog-amble-<run-id>` includes the final accepted checkpoint and source. Scratch is node-local; preserve artifacts before the allocation ends. The outer limit is 11 hours 35 minutes with two minutes to terminate; the 12-hour allocation must stay active. If a slot fails, inspect its log under `$DOG_WORK/runs/amble-overnight/` and W&B. Offline mode requires later synchronization.

Upload the archive to your home directory, then:

```bash
mkdir -p ~/robot-dog-amble
cd ~/robot-dog-amble
unzip ~/robot-dog-amble-overnight.zip
source ./hpc_storage.sh
nohup bash hpc_amble_overnight.sh > "$DOG_WORK/amble-overnight.log" 2>&1 &
tail -F "$DOG_WORK/amble-overnight.log"
```

The existing `~/robot-dog-newton/.venv-cuda` is reused; set `DOG_VENV` if it is elsewhere. Ctrl+C exits only the log viewer. Results are simulation-only and are not cleared for deployment to the physical robot.
