# Luca project status

## What works now

- MuJoCo P2S preview geometry is available for the current 230 mm chassis.
- PPO checkpoints and their observation normalization data are preserved.
- Supported servo replay tracks commanded positions closely; unsupported ground
  walking is not validated.
- The ESP32-S3 receives MPU6500-compatible IMU data at I2C address `0x68`.
- The Raspberry Pi ROS 2 Jazzy bridge publishes raw IMU telemetry on
  `/imu/data_raw` without servo commands.

## Current development boundary

The onboard battery, Pi, power distribution and final enclosure are not all
installed in their final configuration. Do not tune a final walking policy to
the temporary centre of mass. Current ground tests are diagnostic and
supported only.

## Next priorities

1. Verify the raw IMU acceleration scale and establish body axes/zero pose.
2. Finish joint direction, travel-limit and neutral-pose records for the new
   chassis.
3. Measure actuator latency/speed/load during supported motions.
4. Train and evaluate a slow quasi-static crawl across randomized mass,
   friction and actuator parameters.
5. Validate the final CAD mass distribution once the onboard hardware is
   installed.

## Evidence

The representative supported-replay comparison and media are in
[docs/sim-to-real](sim-to-real/README.md). The results are not a claim that
Luca has completed independent ground walking.
