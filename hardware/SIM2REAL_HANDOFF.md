# Simulation to hardware handoff

Prepared October 28, 2026. Scope: the replacement NodeMCU ESP-32S and the new
frame. This document and its [validation record](SIM2REAL_HANDOFF_VALIDATION.json)
were prepared offline. No serial port was opened, no firmware was uploaded,
no motor was commanded, and no training was started.

**Progress update, October 28 at 12:50 PM:** the operator captured all 12
model-zero points through ESP32 CSV on COM7. The saved records passed checks
for unique expected IDs, three stable distinct samples, torque OFF, position
mode, clear status and matching model hash. The current zero-only record is
[`calibrations/zero-points-current.json`](calibrations/zero-points-current.json),
from `zeros-20261028-124732-40500f.json`. These are now operator-confirmed zero
points, unlike the earlier uncalibrated raw readings listed later. Directions,
current-frame travel limits and powered motion remain unverified. Historical
neutral/mapping files and the old replay CSVs were not changed.

| Leg | New roll zero | New hip-pitch zero | New knee zero |
|---|---:|---:|---:|
| Front left (IDs 4/5/6; corrected October 28) | 2130 | 1788 | 1861 |
| Front right (IDs 1/2/3; corrected October 28) | 2105 | 1830 | 1836 |
| Rear left (IDs 7/8/9) | 2065 | 1707 | 1708 |
| Rear right (IDs 11/10/12) | 1999 | 1881 | 1759 |

All values are raw encoder ticks at model joint angle zero. A zero-only
record is not a complete neutral-and-limits file for powered replay.
The user corrected front-left/front-right assembly labels after this capture;
zeros were preserved by physical servo ID and relabeled in the current record.
Original timestamped capture files retain their historical labels. ID2's zero
1830 is distinct from ID8 rear-left hip pitch's zero 1707 and ID9 knee's 1708.

The next physical milestone is a supported, two-joint correspondence test.
Full-body feedback walking is not ready. The existing powered replay program
cannot communicate through the current ESP32 readout sketch; this transport
gap must be resolved before connecting that program to COM7.

## Selected checkpoints and what each is for

| Use | Checkpoint and matching source | Status |
|---|---|---|
| Latest simulation candidate for later full-body deployment | `runs/hpc-review-j6ett8qi/checkpoint` and `runs/hpc-review-j6ett8qi/source` | Run **j6ett8qi**, 36,943,712 cumulative steps; simulation validation only |
| Origin of the existing supported rear-left replay plans | `policies/best-distance` and historical source archive `policies/sources/58cjy6ku.zip` | Run **58cjy6ku**, step **9,516,896**; the previously reviewed physical replay used this policy |

Use the existing **3-degree plan** as the template for the first new-frame
supported test after recalibration. Do not label those CSV plans as j6ett8qi:
all three checked-in plans were generated from the 9,516,896-step policy.
They replay recorded targets, not policy inference from the real robot.

Latest candidate artifacts are in
[`j6ett8qi`](https://forge.coreweave.com/wandb/marsdenm-oregon-state-university/robot-dog-rl/runs/j6ett8qi):
`marsdenm-oregon-state-university/robot-dog-rl/robodog-policy-j6ett8qi:v17`
and `marsdenm-oregon-state-university/robot-dog-rl/robodog-source-j6ett8qi:v0`.
Both immutable versions were confirmed COMMITTED during this handoff.
Its saved five 60-second trials averaged
**0.01141096 m/s (1.1411 cm/s)**, with no falls or severe-slide resets. Those
trials do not validate the new frame, electronics, servo calibration, or ground
walking. The four-hour 2 cm/s package is an experiment, not an accepted result.

Fingerprint the pair before using it:

| File | SHA-256 |
|---|---|
| j6ett8qi `policy.zip` | `3f9c60c6aeb4d31aca4618b72cba4d82360e81574898bb626f4ed68c136b3688` |
| j6ett8qi `normalize.pkl` | `1181b5ea649abb71c9e96dfe31210c881de1fbd147ce0a110b9736be1622b0a6` |
| supported-plan origin `policy.zip` | `5e65ecd3cf056db3bfe6e5e198c69c8fea94bc19d96b63af7a0485b9590d94f9` |
| supported-plan origin `normalize.pkl` | `69fecd589f40668da7a9ff5a23bbf08cd6e9477d1c341dfd047d200fecc92b10` |
| both loaded `robot_dog_v2.xml` files | `655de7d1bd9f1cb8185680aa6c5e2c8e846268323d4fc74e74635f2d1beb3fca` |

The latest files under `runs/` are local downloads and are ignored by Git.
The older `policies/` snapshot and its source archive are checked in. Keep
`policy.zip`, `normalize.pkl`, `environment.json`, model/assets, and the matching
implementation together. Never combine normalization from a different run.
Only load trusted policy/pickle files. The validation JSON records additional
file hashes, joint order, task settings, and plan checksums.

The latest task uses reward version 7, command 0.01 m/s, tracking weight 1.25,
31.5 mm stride, and a 3-second four-leg cycle. The old supported-plan origin
uses a 20 mm stride. Lift is 25 mm at the front and 37.5 mm at the rear; swing
order is rear-left, front-left, rear-right, front-right. There is a one-second
reference ramp. The model still uses its saved FRAME V2 geometry and masses.
A new physical frame or relocated leg does not automatically update that model.

## Hardware and transport boundary

Reported current hardware:

| Item | Setting |
|---|---|
| Controller | NodeMCU ESP-32S / classic ESP32, replacing the overheated ESP32-S3 |
| Host | Windows PC over USB; historically COM7, identify the actual current port |
| Servo bus | Waveshare Bus Servo Adapter (A), UART-control jumpers at A, 1,000,000 baud |
| Host UART | GPIO17 TX to adapter TX; GPIO16 RX to adapter RX; common GND |
| Servo power | Separate 12 V supply for the 12 V STS3215 units |
| IMU readout wiring previously verified here | SDA21, SCL22, 3V3/GND; confirm this remains the actual wiring |

Adapter TX/RX labels above follow the already confirmed adapter-specific
wiring. They are not an instruction to swap wires based on generic UART rules.
Do not connect the 12 V servo supply to the ESP32 or IMU power pins.

There are two different serial protocols:

| Software | What it expects or provides |
|---|---|
| `calibration_view.py`, `supported_replay_view.py`, `calibration_io.py` | PC opens a **direct binary STS servo bus at 1 Mbps** |
| `imu_servo_readout/imu_servo_readout.ino` | PC USB console at **115200**, CSV telemetry; ESP32 polls the servo UART at 1 Mbps |
| Current combined sketch's host commands | `SERVOS`, `IMU`, `BOTH`, `HELP`; these select readout only |

**The CSV sketch is neither a transparent binary bridge nor a motor-command
controller.** Pointing the existing replay viewer at COM7 does not implement
that missing bridge. Its read-only parser does not forward arbitrary host
bytes to the servo bus. The most recent successful sensor-only flash also
does not prove that the combined sketch is currently installed.

For the current ESP32 route, the remaining implementation is a matching PC
transport and ESP32 controller/bridge with explicit arm/start/stop, command
acknowledgements, fresh feedback, bounded target/ID checks, and a local
communication watchdog. Existing direct-bus replay packet semantics and
verified selected-joint release must be preserved. No such firmware change is
made by this handoff. A properly configured direct Waveshare USB connection
is a separate alternative for the existing viewer; confirm that connection
and avoid simultaneous bus masters before treating it as a direct bus.

The recent COM7-busy upload error remains unresolved in this handoff. Close
Serial Monitor and other serial viewers before selecting an owner for the
port. Do not upload a different sketch or change ports automatically.

## Exact joint and encoder contract

This is **policy vector order**, not numeric servo-ID order. Left and right
refer to the robot facing forward. Confirm every physical location on the new
frame: a servo keeps its ID when a leg is moved.

| Vector index | Model joint | Expected ID | Saved display sign | Latest reported ticks, not neutral |
|---:|---|---:|---:|---:|
| 0 | front_left_hip_roll | 4 | +1 provisional | 2083 |
| 1 | front_left_hip_pitch | 5 | +1 provisional | 2066 |
| 2 | front_left_knee_pitch | 6 | -1 | 2072 |
| 3 | front_right_hip_roll | 1 | +1 provisional | 2009 |
| 4 | front_right_hip_pitch | 2 | +1 provisional | 1775 |
| 5 | front_right_knee_pitch | 3 | -1 | 1707 |
| 6 | rear_left_hip_roll | 7 | +1 provisional | 2112 |
| 7 | rear_left_hip_pitch | 8 | +1 historical | 1897 |
| 8 | rear_left_knee_pitch | 9 | -1 historical | 1832 |
| 9 | rear_right_hip_roll | **11** | +1 provisional | 2062 |
| 10 | rear_right_hip_pitch | **10** | +1 provisional | 1874 |
| 11 | rear_right_knee_pitch | 12 | -1 | 1771 |

The latest readings arrived without fresh timestamps; they prove neither the
current pose nor calibration. **Do not save them as neutral.** All four saved
knee signs are -1, including the previously corrected front knees. Other saved
signs are display defaults or historical observations and must be checked
against the current assembly.

For each joint establish a measured raw zero `z`, a verified sign `s` in
{-1,+1}, and a reviewed continuous, non-wrapping raw interval. The simulation
neutral is zero radians for all 12 joints:

The exact kinematic zero pose is rendered in
[`simulation-neutral-reference.png`](../reports/sim2real/simulation-neutral-reference.png),
with the underlying joint/foot coordinates in
[`simulation-neutral-reference.json`](../reports/sim2real/simulation-neutral-reference.json).
Zero joint coordinates preserve the model's CAD mounting transforms; the
legs remain bent. A physical servo's corresponding encoder zero must be
measured at that pose, not assumed to be tick 0 or 2048.

```text
q_model_rad = s * (ticks - z) * 2*pi/4096
goal_ticks  = z + round(s * q_target_rad * 4096/(2*pi))
4096 ticks/revolution; 11.3777778 ticks/degree; 0.087890625 degree/tick
```

Do not apply `% 4096` to an out-of-range command. Reject it. The historical
modulo formula in `joint_safety_config.json` is not this no-wrap contract.
The supported replay explicitly requires raw goals in 0..4095 and inside its
reviewed bounds. The knee interval beginning at 1 tick is a conservative
software boundary, not a measured physical stop.

`physical_neutral_pose.json` and `display_joint_mapping.json` retain old zeros.
The reviewed October 26 rear-left capture uses ID8=1677 and ID9=1572, with
25-tick guarded intervals [722,2846] and [26,2443]. The new reported readings
are **220 and 260 ticks away** from those zeros. Existing replay preflight
would reject them because it requires starting within 12 ticks. Do not
command a return to the historical zeros to make that check pass; verify the
new frame and recapture its actual model-neutral pose first.

Record new-frame calibration in a new timestamped file, retaining the older
files. Verify ID/location, model-zero pose, positive direction, conservative
endpoints, coupled-pose clearance, cable clearance, and that no encoder wrap
is crossed. Display-only zero edits do not update actuator calibration or
the replay CSV. Do not write EEPROM centering/limit registers as a substitute.
Historical ID2 absolute-position ambiguity and frame-contact observations in
`joint_safety_config.json` remain unresolved for the new frame.

## Policy actions and timing

The policy is a residual position controller around the saved IK gait. It
does not produce servo ticks, PWM, torque, or complete joint targets directly.
For the 12 outputs, in the joint order above:

```text
dt = 0.02 s                                  # 50 Hz control
a = clip(policy(normalized_observation), -1, +1)
alpha = 1 - exp(-dt/0.12)                    # approximately 0.153518
filtered += alpha * (a - filtered)
desired = clip(reference(time) + 0.035*filtered, model_joint_limits)
target += clip(desired - target, -1.5*dt, +1.5*dt)
last_action = a                              # clipped output, not filtered residual
```

The residual scale is **0.035 rad**, approximately 2.005 degrees. The target
rate bound is 1.5 rad/s, or 0.03 rad per control sample. These model settings
do not establish a safe hardware first-test speed. The model position
actuators use kp=12, kv=0.15 and a +/-1 N m force limit; those values are not
equivalent to STS3215 register gains or a hardware torque limit.

Physics dt is 0.002 s, ten substeps per policy step. The real PC controller
would infer at 50 Hz; the ESP32 would own local timing/watchdog and bus I/O.
No Pi/Jetson is needed for the proposed PC-inference architecture, but actual
end-to-end latency has not been measured. Do not copy simulation random reset
noise or automatic episode resets onto physical actuators. Phase, last action,
filtered action, and initial target require an explicit aligned arm/reset.

The saved model ranges are roll +/-0.5 rad, hip pitch +/-1.2 rad, knee pitch
+/-1.5 rad, with roll axis [1,0,0] and both pitch axes [0,-1,0] in their joint
frames. Hardware commands must also satisfy current measured raw limits and
coupled-pose constraints. Simulation limits alone do not authorize motion.

## Exact feedback observations for later closed-loop inference

The v7 policy expects **60 float32 values** before normalization:

| Zero-based slice | Quantity | Units/frame |
|---|---|---|
| 0:3 | projected gravity `R_body_to_world.T @ [0,0,-1]` | unit vector, body frame |
| 3:6 | base angular velocity | rad/s, body frame |
| 6:9 | base linear velocity at the base inertial COM | m/s, body frame |
| 9 | commanded forward speed | m/s; 0.01 for both selected checkpoints |
| 10:22 | measured joint position minus model neutral | rad, exact vector order above |
| 22:34 | measured joint velocity | rad/s, same order and signs |
| 34:46 | previous clipped policy output | dimensionless; initialized to zero |
| 46:48 | sin(2*pi*phase), cos(2*pi*phase) | phase = elapsed/cycle modulo 1 |
| 48:60 | current unsmoothed reference joint targets | rad, generated from matching model/task |

Use saved observation mean/variance, epsilon 1e-8 and clip_obs=10:
`clip((obs-mean)/sqrt(var+epsilon), -10, +10)`. Freeze statistics during
deployment (`training=False`); do not re-fit them on the real robot or apply
reward normalization to observations. Use deterministic inference for the
first comparison. Maintain the exact reference/observation/action timing;
the previous action is not reconstructed from measured encoder angles.

Forward reward is along model +X and gravity is along world -Z. Check actual
model axes before assigning physical left/right or IMU axes; do not assume a
coordinate convention just from a CAD part label. At the rendered neutral,
the front-labeled foot sites have X=-0.110224439 m while rear-labeled sites
have X=+0.111729541 m. Consequently the name "forward speed" in the training
logs does not establish the intended physical nose direction; verify that
association before full-body deployment. The model's base inertial
COM is offset [0,0,0.025] m from its body origin. Match the velocity reference
point when building the estimator.

The combined diagnostic's servo feedback is roughly **one sample per ID per
1.2 seconds**, while the policy requires synchronized usable state at 50 Hz.
That diagnostic rate and its CSV interface are for identification, not walking.
Encoder-velocity conversion, latency/jitter, packet loss and coherent 12-joint
state acquisition remain to be implemented and measured. Missing or stale
measurements must not turn into zero observations.

## IMU evidence and missing estimator work

The REAL handoff reports an IMU purchased with installation/model not yet
confirmed there. This workspace has additional, earlier evidence:
[`reports/imu/bringup-20261027.json`](../reports/imu/bringup-20261027.json)
records NodeMCU COM7, SDA21/SCL22, I2C 0x68, WHO_AM_I **0x70**, and the
MPU6500-compatible register profile. A board sold as MPU6050 should not be
treated as an identified MPU6050 merely from its label. Confirm that this is
the same sensor and current installation before using that evidence.

The readout produced about 100 Hz, but mean stationary acceleration magnitude
was about 9.37 m/s2 and gyro biases were nonzero. The saved current-pose zero
in `imu/calibrations/current-zero.json` is a tilt reference and stationary
gyro-bias estimate. It is not verified robot-axis alignment, full acceleration
calibration, fused attitude, or a base-velocity estimator.

Later closed-loop deployment requires a verified sensor-to-body rotation,
gyro-bias treatment, gravity/attitude filtering, timestamp synchronization,
and validated linear-velocity estimation at the base COM. An accelerometer
includes gravity/proper acceleration; do not feed its raw three numbers into
the projected-gravity slot. Level simulated gravity is [0,0,-1]. Arbitrarily
zeroing accelerometer channels or integrating noisy acceleration without a
validated estimator does not supply the saved observation contract. Missing
linear velocity cannot simply be replaced by the command or constant zeros.

Supported open-loop CSV replay does **not** need these IMU observations.
That makes it the appropriate next correspondence test while estimator work
remains incomplete. Ground feedback walking is a later milestone.

## Staged first supported replay on the new frame

1. **Offline review.** Pin the checkpoint/source/calibration files. Compare
   the new frame, link orientation, servo housing attachment, and foot geometry
   with the saved model. All three portable plans passed static checks, but
   that result does not establish current physical clearance.
2. **Read-only bringup.** Resolve the COM7 owner/firmware identity, and confirm
   fresh status for all 12 IDs. With support and torque verified off for a
   joint, identify its physical location and positive direction manually.
   Reconcile possible swapped legs before changing mapping files. Do not force
   a joint whose torque state is unknown.
3. **New calibration.** Capture the model-neutral pose and backed-off continuous
   bounds for the intended rear-left pitch joints in a new reviewed file.
   Check the hip/knee pair through its intended poses, not only independently.
   The existing rear-left capture UI itself needs its expected direct-bus
   transport; it cannot read the CSV sketch unchanged.
4. **Resolve the motion transport.** For the chosen ESP32 route, implement and
   test the matching controller/PC transport, initially read-only and then
   explicit selected-joint start/stop. Verify request/ACK/readback, feedback
   freshness, watchdog release, and that IDs other than the selected pair cannot
   be written. Do not substitute a raw COM7 selection for this work.
5. **Regenerate and inspect a 3-degree plan offline** using the reviewed
   new-frame capture and the known portable-policy origin. This template only
   generates files; `NEW-FRAME-REVIEWED.json` must first exist:

   ```powershell
   .venv\Scripts\python.exe hardware\prepare_policy_transfer.py `
     --checkpoint policies\best-distance --source simulation\mujoco `
     --calibration hardware\calibrations\NEW-FRAME-REVIEWED.json `
     --max-degrees 3 --slowdown 2 --output runs\sim2real-new-frame-3deg
   ```

   Inspect its report, CSV, no-wrap limits, beginning/end neutral, pair shape,
   physical direction and clearance before using it as a motion plan.
6. **Explicit-start supported test, after transport/calibration acceptance.**
   Secure the body, feet clear, hands clear, with an accessible physical power
   cutoff. Only selected IDs 8/9 are in scope after confirming they are the
   intended rear-left joints. The direct-bus viewer can then be opened with
   the generated plan **only on its verified compatible direct connection**:

   ```powershell
   .venv\Scripts\python.exe hardware\supported_replay_view.py --plan runs\sim2real-new-frame-3deg
   ```

   The ESP32 route needs the corresponding transport adaptation first. Opening
   the viewer does not command motion. Connect/preflight must pass, then the
   operator checks the support box and presses START. Do not launch or press
   START automatically as part of this handoff.
7. **Review target versus encoder logs.** Require fresh position mode, torque
   reported off before starting, and within 12 ticks of the newly reviewed
   neutral. The existing controller preloads measured-position goals before
   enabling selected torque. It rejects >35-tick tracking errors, >100-tick
   jumps, measured-limit violations, communication failure and >0.25 s lateness.
   STOP releases selected servos and does not command a blind return. Confirm
   `release_verified=true` in the `.status.json` beside the recorded CSV. If
   release is unconfirmed, use the physical cutoff and inspect before retrying.
8. **Expand only after reviewing that test.** A reviewed 5-degree pair test can
   follow, then larger paired motion and other legs with their own verified
   mappings/limits. The old full-amplitude plan is historical, not the first
   new-frame test. Full-body supported replay and then ground feedback control
   need separate acceptance; a supported replay is not proof of balance.

Historical plan details for comparison, not current motion authorization:

| Plan folder | Duration / sampling | Amplitude | Profile | Raw ID8 / ID9 target range |
|---|---|---|---|---|
| `replay_plans/rear-left-3deg` | 9.24 s / 25 Hz | max 3 degrees, common scale 0.0837784 | 60 ticks/s, acceleration register 10 | 1666..1708 / 1565..1606 |
| `replay_plans/rear-left-5deg` | 13.86 s / 16.67 Hz | max 5 degrees | 60 ticks/s, acceleration register 10 | 1658..1728 / 1561..1629 |
| `replay_plans/rear-left-full-46s` | 46.2 s / 20 Hz | max 35.8087 degrees | 120 ticks/s, acceleration register 20 | 1544..2044 / 1494..1979 |

The current replay software displays/logs temperature but has no software
temperature abort, following the earlier explicit user request. This handoff
does not change that setting or any internal servo protection. It is a known
limitation to review before new powered testing; do not interpret a low
temperature as proof that a status, torque-release, or tracking error is safe
to bypass. Communication loss cannot guarantee software torque release.

## Offline validation completed and its limits

Both checkpoint manifests match the loaded 12-joint order; normalization has
60 finite observation means/variances with the saved scale/clip settings;
model neutrals are zero. Both references pass 601 full-cycle IK/limit samples.
All three preserved plans pass the actual `supported_replay.load_plan()`
checks, including exact origin-policy hash, mapping, bounded targets,
neutral endpoints and their speed-profile constraints. These checks performed
no hardware I/O. See the companion validation JSON for exact hashes.

The latest CUDA policy also has an existing unresolved broad CPU/GPU
observation comparison difference of about 0.085 at 31.5 mm, already present
with the unchanged saved source; its tolerance has not been relaxed. Do not
silently generate a purportedly identical latest-policy hardware trajectory
through a different backend without checking its targets. The old reviewed
CSV is a useful independent correspondence milestone while this remains open.

No full-body new-frame calibration, transport timing, physical current/torque
mapping, IMU mounting/state estimation, or ground stability is certified here.
The immediate implementation handoff is **a compatible ESP32 command/feedback
transport plus a reviewed new-frame rear-left calibration**, followed by the
operator-started small supported replay above.
