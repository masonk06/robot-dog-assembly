# P2S HPC IK + PPO walk

This is the active simulation starting point for training the current P2S
chassis. It does not reuse an old gait as a hardware command. It continues
from the conservative checkpoint with a 3-second IK walking reference and PPO
residual actions: 12 mm/s command speed, 25 mm stride, and the existing
60-observation policy interface.

The curriculum holds total modeled mass constant while evaluating five
temporary-prototype scenarios. Its nominal COM is 8 mm forward (negative body
X), with bounded variants from 15 mm forward to 4 mm rearward and friction
between 0.70 and 0.90. This encodes a slight expected front bias without
overfitting to Luca's current incomplete battery/Pi/PDB layout, while
preserving the 60-observation policy contract.

## On an allocated H100 session

Clone or pull the repository, activate the existing CUDA environment, and run:

```bash
cd ~/robot-dog-assembly
chmod +x simulation/p2s_crawl/hpc_run_quasistatic.sh
bash simulation/p2s_crawl/hpc_run_quasistatic.sh
```

For a 12-hour OSU GPU allocation, defaults are six 6,600-second training
stages (11 hours of training) plus room for the CUDA import gate, checkpoints,
and five 60-second evaluations per stage. It uses 128 parallel worlds and W&B
online logging. Override only before launch, for example:

```bash
P2S_CRAWL_SLOTS=2 P2S_CRAWL_SLOT_SECONDS=900 WANDB_MODE=offline \
  bash simulation/p2s_crawl/hpc_run_quasistatic.sh
```

The script writes caches and run data under `/raid/$USER/robot-dog-rl` by
default on dgxh-1. This is node-local RAID storage, so it is appropriate for
the active 12-hour job but not persistent across nodes or node maintenance.
Set `DOG_WORK` to a different writable location if needed. Copy selected
checkpoints and curated outputs to backed-up storage before the allocation
ends.

## Before a long run

Run the short two-stage command first. It validates that the P2S model imports
into CUDA physics and that the GPU environment is correctly configured. The
final mass model and actuator delay/torque measurements should be added before
any unsupported hardware transfer. A simulation result is not approval for a
free-standing physical gait.
