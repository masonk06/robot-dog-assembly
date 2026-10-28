# Verify all 12 model-zero points through the ESP32

Run from the project directory:

```powershell
.venv\Scripts\python.exe hardware\esp32_zero_view.py
```

The window starts disconnected and never sends serial commands, motor goals,
torque changes or EEPROM writes. It passively reads the combined sketch's
115200-baud servo CSV. Close Arduino Serial Monitor or another app that owns
the ESP32 port before clicking Connect. The direct Waveshare USB calibration
viewer is a different protocol and is not the window to use for this route.

The current compatible read-only sketch is
`imu_servo_readout/imu_servo_readout.ino`, NodeMCU-32S, UART RX16/TX17 to the
Waveshare in mode A. Uploading is not automatic. If there are only IMU lines,
legacy text or NO DATA, verify which sketch is installed rather than treating
missing positions or torque state as zeros. Do not force a joint to move
while torque is ON or unknown; this program cannot turn it off.

1. Support the body with feet clear and verify torque reports OFF before
   gently positioning a joint. Keep the power cutoff accessible.
2. Compare the physical joint to the simulation reference image. All 12
   model angles are zero in that image; the CAD mounting bends remain.
   The user confirmed the same leg arrangement on October 28, 2026, which
   does not itself confirm each encoder zero or positive direction.
3. Start with front-left hip roll, expected ID4 after the user's front-leg
   label correction on October 28. If physical IDs were moved,
   select the verified physical ID; do not infer it only from the old label.
4. Place that joint at its model-zero pose and hold it still. Allow about
   four seconds for three samples. This is a stationary manual measurement,
   not a walking-rate feedback channel. The maximum accepted latest-sample
   age is two seconds because each ID is polled about every 1.2 seconds.
5. Check the operator confirmation and click Capture selected zero. The tool
   requires three distinct stable samples within eight ticks, torque OFF,
   position mode, clear status, no-wrap ticks, and fresh sample history.
6. It advances in policy order: FL 4/5/6, FR 1/2/3, RL 7/8/9, RR 11/10/12.
   Repeat the physical pose/ID confirmation for each joint. The whole robot
   need not be moved by software; nothing here commands motion.
7. Click Save all 12 zero points after all twelve have been captured with
   unique IDs. Each intermediate capture is also written to the same new
   timestamped `hardware/calibrations/zeros-*.json` session file.

The historical zero column is reference data, not a commanded target. This
workflow does not overwrite `physical_neutral_pose.json`, the display mapping,
servo limits, firmware, or the older calibration files. Saved zero-only
sessions explicitly remain `ready_for_motion=false`; signs, travel limits,
coupled-pose clearance and the command/feedback transport still require
separate verification. The existing powered replay rejects these zero-only
records as a full neutral-and-limits calibration.
