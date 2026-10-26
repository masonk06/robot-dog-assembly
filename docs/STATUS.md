# Project status — 2026-10-25

## Mechanical work

The latest export is `cad/RoboDog - Knee Housing Connections.f3d`. All four knee housings were regrouped with the knee-pitch parts and boots; output discs were moved to the upper-link groups. A front-left 20-degree preview confirmed housing/foot motion together, but showed the pivot still near the hip. Other knees have the same regrouping but have not received equivalent motion tests in this session.

Next: correct knee centers to the physical output axes; verify all hip/knee signs, interference, and conservative ranges; then export new placements and regenerate the simulation.

## Simulation and RL

The MuJoCo kinematic preview fixes the base. The dynamics script adds gravity/contact. Existing notes report insufficient forward progress, so the gait remains unvalidated for hardware. No trained robot-dog policy is included.

An Isaac Lab / Newton GPU environment was initialized on OSU HPC, with a reported Cartpole smoke run. This is separate from training this dog; see [HPC notes](HPC.md).

## Backup boundary

This repository preserves accessible Windows project files plus the identified latest Fusion export. It does not include remote HPC home/scratch contents, unsaved Fusion application state, or unrelated local project folders. Export remote scripts, job configurations, selected training logs, and policies to complete that backup. Keep containers and caches out of Git.
