# OSU HPC / Isaac Lab / Newton

Recorded during development, not freshly reverified:

| Item | Value |
| --- | --- |
| Session host | `dgxh-3` |
| GPU | NVIDIA H100 80 GB HBM3 |
| Python module | `python/3.12` |
| Container | `isaac-lab-3.0.0-kitless.sif` |
| Image | `docker://nvcr.io/nvidia/isaac-lab:3.0.0-kitless` |
| Torch check | `2.11.0+cu130`, CUDA available |

Remote project: `~/robot-dog-rl`, containing `assets/`, `configs/`, `scripts/`, `logs/`. Container and cache files were placed in `/scratch/marsdenm/robot-dog-rl/` after home storage filled. Scratch mapped to node-local `/raid`; it is not a durable backup.

The original mesh ZIP was unpacked in `assets/`. `configs/so101_reference.xml` is an SO101 arm reference, not the dog model. The dog needs verified axes, masses, limits, and actuators.

To complete the remote backup, transfer scripts/configs and selected results to a staging folder for review. Exclude credentials, virtual environments, caches, and containers. Track large results separately with their source commit and storage location.
