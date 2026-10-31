# Luca COM and contact-dynamics study — 2026-10-30

This is a **simulation-only** comparison using the frozen overnight PPO policy,
saved observation normalizer, and identical reset seeds `10000..10002` for every
case. The original XML, checkpoint, and real-servo configuration were not
modified.

## Model inspection

- XML total mass: **1.923 kg**. The builder comment says 1.903 kg, which does
  not match the inertial entries.
- Static body-frame COM: **x = +4.17 mm** (rearward, because robot forward is
  negative local X), y = 0, z = +9.75 mm relative to the base origin.
- The 1.282 kg base inertial lump has no separate battery body or battery
  location. Therefore battery relocation cannot be represented faithfully yet.
- Hip locations are approximately x = +/-108.6 mm and y = +/-77.5 mm. Foot
  collision uses 3 mm spherical proxies; printed boot meshes are visual-only.
- Position actuators are kp=12, kv=.15, force-limited to +/-1 Nm. This is still
  a provisional actuator/contact model.

## Controlled policy results

| Case | Mass kg | Body COM x mm | Speed m/s | Front force N | Rear force N | Max pitch deg | Slip reset |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 1.923 | +4.17 | 0.0180 | 9.33 | 9.88 | 1.73 | 0/3 |
| COM forward 30 mm, fixed mass | 1.923 | -15.83 | 0.0173 | 11.05 | 8.06 | 2.07 | 0/3 |
| COM rear 30 mm, fixed mass | 1.923 | +24.17 | 0.0123 | 7.23 | 12.10 | 4.05 | 3/3 |
| 100 g forward payload example | 2.023 | +2.48 | 0.0176 | 9.91 | 10.18 | 1.69 | 0/3 |

The 100 g payload is an illustrative declared cube at x=-30 mm, z=+40 mm; it
is **not** claimed to be the actual temporary mass used on Luca.

## Interpretation

The rear-biased case reduced front normal force by about 22% and produced a
slide reset in every trial after about 1.63 s. That qualitatively supports the
observed front-foot unloading/bounce. A forward COM shift increased front
normal force about 18%, but also increased slip and pitch slightly. It did not
produce a new robust gait by itself.

## Recommendation

1. Correct the simulation model first: measure battery/electronics mass and
   installed location, then split the base mass into a frame/electronics/battery
   model with measured inertias.
2. Do not physically relocate the battery solely from this sweep. The observed
   front-weight improvement is evidence worth testing after measurement, but
   the current model cannot represent the installed battery.
3. Use a controlled hardware step-response/logging test to identify actuator
   delay, rate, and torque behavior. The current slow replay telemetry provides
   tracking error but does not identify a unique torque or time-constant model.
4. If the corrected COM model still cannot match supported ground behavior,
   train a slow quasi-static crawl with deliberate weight transfer and domain
   randomization around the measured COM, friction, actuator delay, and torque.
