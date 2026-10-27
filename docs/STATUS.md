# Project status — 2026-10-26

The dog has a working slow simulated gait and user-confirmed, supported
rear-left motion transfer. Full-body hardware walking is not validated.

## Simulation and learning

Version 7 combines a programmed four-beat reference with filtered learned
corrections limited to about 2 degrees. The 60-value observation contract is
preserved across MuJoCo, Newton and the CUDA training port. Newton/MuJoCo Warp
uses replicated GPU physics; the current CUDA path also runs observations,
rewards, normalization, GAE and PPO updates on GPU. CPU handles orchestration,
logging and checkpoint files.

| Run | Steps | Recorded forward distance / 20 s |
| --- | ---: | ---: |
| i95lccut | 8192 | about 10.2 cm; original approved gait |
| qfwutfdb | 448352 | 11.14 cm; tracking weight 1.25 |
| 58cjy6ku best-distance | 9516896 | 16.02 cm; smooth playback approved |
| 58cjy6ku latest saved | 16570208 | 15.75 cm |

These evaluations had six steps per leg and no falls/sliding resets across
three trials. Long-run improvement plateaued around 7–9 million steps. The
process was stopped after its latest periodic save; later unsaved rollout
data is not a checkpoint. Four useful policies, normalization statistics and
exact source archives are backed up under [policies](../policies/README.md).

## Hardware calibration

Rear-left calibration was confirmed by the user after supported replay on
2026-10-26. See [current calibration](../hardware/calibrations/rear-left-current.json).

| Joint | ID | Neutral | Reviewed ticks | With 25-tick margin |
| --- | ---: | ---: | --- | --- |
| Rear-left hip pitch | 8 | 1677 | 697–2871 | 722–2846 |
| Rear-left knee pitch | 9 | 1572 | 1–2468 | 26–2443 |

The knee lower bound is a user-chosen conservative no-wrap interval, not a
measured physical endstop. Original captures are retained. All four knee
model-to-encoder signs are -1; front IDs 3/6 were corrected by live comparison.
The shared source is [joint_mapping.py](../hardware/joint_mapping.py).

Supported tests progressed from 3 and 5 degrees to full-amplitude rear-left
pitch motion and a faster 46.2-second replay at 120 ticks/s. The faster trial
completed, verified torque release, and received user confirmation. Representative
logs are in [reports/sim2real](../reports/sim2real/README.md). Hip roll and other
legs were not commanded. The controller now serializes release commands,
acknowledgements and readbacks, retaining original errors if cleanup fails.
Temperature is displayed/logged; the software temperature abort was removed
at the user's request. Internal servo protection settings were not changed.

## Remaining work

1. Reconcile current neutral/limits for other legs; historical records conflict.
2. Measure loaded tracking, latency and actuator behavior against simulation.
3. Add body-state sensing/estimation for policy feedback. No IMU currently
   reports to the controller; supported replay is open-loop.
4. Expand supported tests before separately reviewing ground-contact transfer.

## CAD and backup boundary

The knee-housing Fusion snapshot and original geometry are preserved; the
user subsequently confirmed corrected pivots. [Frame V3](../cad/frame_v3/README.md)
is a separate packaging revision, not a replacement simulation joint model.

Git includes code, CAD, calibration history, representative measurements and
selected policy/source backups. Full local runs, caches, environments and
containers stay outside Git. Remote HPC files not exported or stored in W&B
are outside this backup. Historical observations are not rewritten as new tests.
