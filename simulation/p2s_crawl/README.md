# P2S HPC quasi-static crawl

This is the active starting point for training the current P2S chassis. It
does not reuse an old fast gait as a hardware command. Instead, it continues
from the conservative checkpoint with the existing quasi-static crawl preset:
slow target speed, deliberate weight transfer, and three-leg stance.

The curriculum holds total modeled mass constant while evaluating five
temporary-prototype scenarios: nominal COM, ±15 mm fore/aft COM, and friction
between 0.70 and 0.90. It also varies the simulation-only actuator response
proxy. This avoids overfitting to Luca's current incomplete battery/Pi/PDB
layout while preserving the 60-observation policy contract.

## On an allocated H100 session

Clone or pull the repository, activate the existing CUDA environment, and run:

```bash
cd ~/robot-dog-assembly
chmod +x simulation/p2s_crawl/hpc_run_quasistatic.sh
bash simulation/p2s_crawl/hpc_run_quasistatic.sh
```

Defaults are six 6,600-second stages (about 11 hours total), 64 parallel
worlds, and W&B online logging. Override only before launch, for example:

```bash
P2S_CRAWL_SLOTS=2 P2S_CRAWL_SLOT_SECONDS=900 WANDB_MODE=offline \
  bash simulation/p2s_crawl/hpc_run_quasistatic.sh
```

The script writes caches and run data under `/scratch/$USER/robot-dog-rl` by
default. Set `DOG_WORK` to a different writable scratch location if needed.
Periodic checkpoints, metadata and W&B artifacts remain the record of the
run; copy the selected result back to persistent storage before an allocation
ends.

## Before a long run

Run the short two-stage command first. It validates that the P2S model imports
into CUDA physics and that the GPU environment is correctly configured. The
final mass model and actuator delay/torque measurements should replace the
current randomized proxies before any unsupported hardware transfer.
