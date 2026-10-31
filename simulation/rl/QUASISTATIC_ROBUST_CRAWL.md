# Quasi-static robust-crawl development track

This is a separate training track for Luca while its battery, Raspberry Pi,
power distribution, and final chassis are not installed. It preserves every
existing model, policy, calibration, and hardware limit.

## Crawl preset

`train_cuda.py --quasistatic-crawl` keeps the existing 60 observations and 12
actions, but changes the training task to a 5 second cycle, 5 mm/s command,
10 mm stride, 12 mm lift, 16% swing duration, and slower residual/target
filters. A swing fraction below one quarter schedules one swing leg and three
stance legs. The reference has a small weight-shift cue; PPO can correct it.

## Robustness curriculum

Run only in simulation. The companion curriculum script creates a source copy
for every slot, then progressively varies mass-constant base COM, foot/floor
friction, and conservative controller response proxies. This is scenario-based
domain randomization across consecutive PPO rollouts; it does not claim every
GPU world has a different physical robot. Each source copy records the exact
scenario beside its checkpoint.

The controller response proxies are not STS3215 measurements. Replace their
range with supported step-response measurements before approving any policy for
ground testing. Servo load percentage is not treated as foot force.

## Hardware boundary

Use the present prototype only for supported diagnostics, IMU/joint logging,
and actuator-response measurements. Do not change torque/current limits, add
foot sensors, or run unsupported dynamic walking. After the final onboard
components are installed, measure their mass and locations, update the model,
and evaluate saved candidates across that final model. Design the battery mount
to slide fore/aft and target a centered COM.
