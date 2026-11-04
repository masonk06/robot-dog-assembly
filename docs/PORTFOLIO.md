# Luca portfolio summary

Use the versions below for public-facing material. They are intentionally
specific about what has been demonstrated in simulation and supported hardware,
and do not claim autonomous unsupported walking.

## One-line GitHub description

**Luca is a custom 3D-printed, 12-actuator quadruped for sim-to-real
locomotion research, combining CAD, embedded telemetry, MuJoCo/Newton physics,
and PPO reinforcement learning.**

Suggested GitHub topics: `robotics`, `quadruped`, `reinforcement-learning`,
`ppo`, `mujoco`, `newton-physics`, `esp32`, `embedded-systems`, `simulation`,
`sim-to-real`, `cad`, `kicad`.

See the [interactive GitHub-rendered policy diagram](POLICY_ARCHITECTURE.md)
for the 60 observations, actor/critic MLPs, and 12 action outputs.

## LinkedIn project entry

**Luca — Sim-to-Real Quadruped Robotics Project**  
*Independent Robotics / Reinforcement Learning Project*

Designed and built a custom 3D-printed quadruped with 12 STS3215 bus servos,
then developed the software and experimental workflow needed to transfer
simulation results toward hardware. Built and trained Luca's own policy/value
neural networks with Proximal Policy Optimization (PPO) in MuJoCo/Newton,
including a CUDA-resident rollout and learning pipeline; the preserved
simulated benchmark moved 16.02 cm in 20 s with six steps per leg and no falls
or slide resets in three recorded trials. Implemented ESP32 servo control, joint-ID mapping, calibrated
zero/direction/limit records, live telemetry, IMU bring-up, and supported
sim-to-real replay. Identified temporary rear-biased mass distribution as a
contact issue using front-ballast experiments and controlled COM simulations,
then created a quasi-static robust-crawl curriculum with COM, friction, and
actuator-response variation.

**Current boundary:** walking behavior is validated in simulation and joint
motion has been tested in supported hardware replay; autonomous unsupported
ground walking is still under development.

## Resume bullets

- Designed and iterated a 3D-printed quadruped platform with **12 STS3215
  serial servos**, including V6/V7 chassis packaging, Raspberry Pi/camera
  provisions, and KiCad power-distribution design reviews.
- Built and trained custom policy/value neural networks for locomotion using a
  MuJoCo/Newton CUDA PPO workflow, a **60-value observation contract**, a
  12-action residual controller, saved normalization/checkpoints, and experiment
  tracking on an OSU H100 GPU.
- Produced a preserved simulation benchmark of **16.02 cm forward travel in
  20 s**, six steps per leg, and no falls/sliding resets across three recorded
  trials; documented limitations rather than presenting it as hardware walking.
- Implemented ESP32-based bus-servo telemetry/control, per-joint ID mapping,
  zero/direction/limit calibration, IMU bring-up, and safe supported replay
  logging with typical joint target errors of roughly **4–8 encoder ticks**.
- Diagnosed front-foot unloading through physical ballast experiments,
  four-corner mass measurements, and matched COM/contact simulation sweeps;
  created a robust quasi-static crawl plan for the final onboard configuration.

## Skills to list

Python, C++/Arduino, ESP32, embedded systems, serial communication, MuJoCo,
Newton, NVIDIA Warp, PyTorch, PPO, reinforcement learning, simulation,
sim-to-real, CAD, Fusion 360, KiCad, PCB design review, Git/GitHub, Linux/HPC,
CUDA, technical experimentation, data logging, and system identification.

## Interview-ready 30-second explanation

“I am building Luca, a 12-servo printed quadruped as an end-to-end sim-to-real
robotics project. I created the CAD and embedded control path, trained my own
policy and value neural networks with PPO in MuJoCo/Newton on GPU infrastructure,
and developed calibration and telemetry tools to compare simulation with hardware.
When ground tests showed front-foot contact problems, I measured a rear-biased
mass distribution and used COM sweeps instead of just tuning the policy. The
next phase is to model the final battery and compute hardware, identify the
real actuator dynamics, and validate a slow quasi-static crawl.”

## Evidence links

- [Repository overview](../README.md)
- [Simulation-to-real recording context](sim-to-real/README.md)
- [COM/contact dynamics study](../runs/com-dynamics-study/README.md)
- [Quasi-static robust-crawl plan](../simulation/rl/QUASISTATIC_ROBUST_CRAWL.md)
- [Current project status](STATUS.md)
