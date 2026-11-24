# Luca project guide

Luca is a 12-DOF, 3D-printed quadruped. This repository combines the active
P2S CAD/model, MuJoCo/Newton simulation, PPO training, ESP32-S3 firmware, and
the Raspberry Pi ROS 2 bridge.

## Start with the current source of truth

- Read [`README.md`](README.md) and [`docs/STATUS.md`](docs/STATUS.md) before
  changing project behavior.
- Treat [`hardware/GETTING_DOG_RUNNING.md`](hardware/GETTING_DOG_RUNNING.md)
  as the authority for physical-robot work.
- The active model is `simulation/mujoco/p2s/robot_dog_p2s.xml`.
- The active training workflow is documented in
  `simulation/p2s_crawl/README.md`.
- The current calibration candidates are records, not universal truths:
  `hardware/calibrations/zero-points-current.json` and
  `hardware/calibrations/manual-physical-directions-20261028.json`.

## Safety boundary — non-negotiable

1. Do not command servos, alter torque/current/temperature limits, or enable
   unsupported walking unless the user explicitly asks for that physical test.
2. Prefer telemetry-only and torque-off checks while calibrating. A live mirror
   must agree with the physical robot for all 12 joints before converting model
   angles to hardware targets.
3. Never replace measured zero positions with a generic `2048` tick center.
   Never infer an encoder wraparound endpoint as a safe motion range.
4. Keep the real and simulated robot distinct in documentation: a successful
   simulation is not approval for a free-standing hardware gait.
5. Preserve an accessible physical cutoff, supported test setup, conservative
   limits, and hardware feedback checks in all physical-test instructions.

## Current hardware facts

- 12 × STS3215 bus servos with 12 V servo power through a Waveshare Bus Servo
  Adapter set to **A**.
- ESP32-S3 is the servo/IMU controller. The firmware is in
  `hardware/esp32_gait_receiver/`.
- Servo UART uses GPIO17 TX and GPIO16 RX; host USB serial is normally 115200
  baud. Do not silently change pins or bus wiring.
- MPU6500/MPU6050-compatible IMU uses SDA GPIO8 and SCL GPIO9 and currently
  reports at I2C address `0x68`.
- Raspberry Pi 5 runs the ROS 2 bridge in `ros2/luca_imu_bridge/`. The bridge
  is telemetry-only and publishes `/imu/data_raw`; orientation remains
  unavailable until calibration/mapping is implemented.
- Current model-order IDs: FL `4,5,6`; FR `1,2,3`; RL `7,8,9`; RR `11,10,12`
  for hip-roll, hip-pitch, knee-pitch respectively. Confirm against the
  calibration records before depending on them.

## Engineering approach

- The current chassis mass distribution is provisional: final battery, Pi,
  power distribution, and enclosure are not yet installed. Do not tune a
  policy tightly around today’s temporary COM.
- Favor slow quasi-static crawl, deliberate weight transfer, three-leg stance,
  realistic actuator latency/speed/torque limits, and domain randomization of
  COM, mass, and friction.
- Preserve the existing policies and reference simulations. New experiments
  should use a new output directory and leave old evidence reproducible.
- The PPO policy has a fixed 60-observation contract. Do not change its input
  dimensions without retraining or a deliberate compatible adaptation.
- Foot-force sensors are deferred. Use IMU, servo feedback, and gait phase for
  diagnostic contact estimates; do not label servo load percentage as foot
  force.

## Repository conventions

- Keep only active P2S CAD, implementation, calibration evidence, selected
  policies, and representative sim-to-real media in the main project story.
- Do not delete or overwrite user work, especially local PCB work under
  `revision_one_oz/` or `revision_onboard_bucks/`, without explicit approval.
- Do not commit run caches, virtual environments, W&B working directories, or
  large temporary artifacts. Selected checkpoints and curated media are the
  exception.
- Update documentation whenever changing hardware pins, IDs, model geometry,
  policy observations/actions, calibration interpretation, or user-facing run
  instructions.
- Use clear names and timestamped output folders for recordings, test logs,
  and experiments.

## Verification expectations

- For Python changes, run the narrowest relevant test or at least compile the
  touched module. Do not claim MuJoCo/Newton/CUDA runtime validation when the
  dependency or GPU is unavailable locally.
- For model or training changes, validate model import and a short pilot before
  recommending a long H100 job.
- For ROS changes, validate telemetry parsing without transmitting serial
  commands, then document the exact Pi verification steps.
- For firmware changes, compile before handoff and state whether upload/live
  hardware validation was actually performed.

## Collaboration style

Explain the reason behind a change in plain language. Luca is also a learning
project, so distinguish clearly between an observation, a hypothesis, a
simulation result, and a confirmed hardware result.
