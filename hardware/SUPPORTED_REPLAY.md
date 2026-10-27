# First supported open-loop transfer

Run locally:

    .venv\Scripts\python.exe hardware\supported_replay_view.py

The portable default is the preserved 3-degree plan under
hardware/replay_plans/rear-left-3deg. The 5-degree and confirmed full 46.2-second
plans are preserved alongside it. To select the confirmed full plan explicitly:

    python hardware/supported_replay_view.py --plan hardware/replay_plans/rear-left-full-46s

The runs/ paths below describe the historical generated test locations. They
are not needed to use the checked-in portable plans.

No port is opened until Connect / preflight. No torque or goal write is sent
until the operator checks the supported setup and presses START. This window
has powered-test labels and is separate from the read-only calibration viewer.
Use only one program on the direct servo-bus USB port at a time.

Input is the reviewed 9.24-second rear-left preview under
runs/sim2real-reviewed-preview: IDs 8 (hip pitch) and 9 (knee), maximum 3 degrees,
corrected sign and neutral 1677/1572. Hip roll and the other ten servos are not
commanded. This is a scaled/slowed sample of simulated policy targets, not a
real-time feedback policy. No IMU or invented body observations are used.

After the user reported smooth 3-degree motion, the next reviewed preview is
runs/sim2real-reviewed-5deg: maximum 5 degrees, 13.86 seconds, same IDs/neutral,
same 60-tick/s profile and live guards. Launch with --plan pointing to that
folder. The window title and Start button display the selected amplitude/time.
Its target ranges are hip 1658..1728 and knee 1561..1629 ticks. Other legs and
hip roll remain uncommanded. Both previews are retained independently.

After the user requested the full rear-left motion, a separate full-amplitude
plan was prepared under runs/sim2real-rear-left-full, retaining amplitude scale
1.0 from the 9516896-step checkpoint's sampled cycle. Hip range is approximately
-11.7..32.2 degrees; knee -35.8..6.84 degrees. It is slowed to 92.4 seconds and
resampled to approximately 20 Hz to retain the existing 60-tick/s limit. Raw
targets 1544..2044 (ID 8) and 1494..1979 (ID 9) pass the reviewed bounds.
Only the rear-left pitch joints are commanded; it is still a supported
open-loop trajectory test, not full-body feedback walking. START is required.

The subsequent user-requested faster plan is runs/sim2real-rear-left-full-faster:
the same amplitude/path and raw target ranges, 46.2 seconds, 120 ticks/s RAM
speed and acceleration 20. Approximately 20 Hz targets are retained. Windows
requests 1 ms timer resolution only during replay and restores it afterward.
REV 2 in the title identifies the acknowledged-release controller. The status
sidecar records controller revision, speed and release verification, making
old-window runs distinguishable. A smoother physical result still needs review.

Preflight requires fresh encoder readings, position mode, torque off,
and start within 12 ticks of neutral. The user requested removal of the software
temperature abort on 2026-10-26; temperature remains displayed/logged, and no
servo internal protection registers are changed. RAM goals are
preloaded to measured positions before enabling torque. The test profile is
60 ticks/s with acceleration 10. The validated no-wrap intervals are enforced;
data must begin/end at neutral and agree with the +/- mapping. No EEPROM
calibration or limit registers are changed.

During replay, stop on operator request, failed telemetry, excessive lateness,
encoder wrap/jump, measured limit violation or tracking error above
35 ticks. STOP releases the two selected servos; abort does not command a return
motion. On completion the final neutral is checked, selected torque is released
and read back, and original RAM profile settings are restored best-effort.
Lost communication cannot guarantee software release; use the physical cutoff.
Close through the window's close control so the worker can finish cleanup.

The left view shows command targets and the right encoder pose for the two
joints. Other joints/body are placeholders. Actual per-sample target/encoder
data is saved under runs/sim2real-hardware. Review the CSV and physical motion
before expanding amplitude, adding other legs, or testing ground contact.
