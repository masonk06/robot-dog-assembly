# ESP32 manual directions and conservative limits

Start the read-only window:

```powershell
.venv\Scripts\python.exe hardware\esp32_joint_check_view.py
```

This uses the current verified zero file `calibrations/zero-points-current.json`.
The window begins disconnected, receives ESP32 CSV at 115200, and implements
no serial writes, motor goals, torque changes, or EEPROM operations. Keep
the existing UART wiring and adapter mode A. Disconnect the zero-point viewer
and Arduino Serial Monitor before connecting this window to COM7.

The left robot stays at model neutral. The right robot highlights the
selected joint's downstream links and slowly shows the chosen +5 or -5
degree reference movement. Only that on-screen model moves automatically.
Choose a side or front/rear camera if the selected movement is unclear.

## First, all 12 directions

Keep the body supported and relevant joints reporting torque OFF before
gentle manual movement. This tool cannot switch torque off. Do not force a
joint or move into contact/cable tension.

1. Select front-left hip roll (ID4), with mode **Directions**. Put this leg's joints
   near their saved zeros. Check the confirmation box and Capture neutral
   baseline. This requires the selected joint within 12 ticks of its zero,
   the other joints on this leg within 35 ticks, and all joints providing fresh
   readings with torque OFF, position mode and clear status. Other legs need
   not match their neutral pose for this direction-only check. It preserves
   the saved zero; it does not redefine it.
2. Click **Show +5°**. Watch the highlighted simulated movement. Gently move
   the matching real joint a few degrees in the same model-positive direction.
   Hold it still, check the confirmation box, then Capture positive pose.
3. Return through zero. Click **Show −5°**, move gently in that model-negative
   direction, hold still, confirm and Capture negative pose.
4. Both raw encoder changes must be clear and opposite. The tool infers sign
   +1 if model-positive motion increases ticks, or -1 if it decreases ticks.
   Captured direction moves must be roughly 2–15 degrees from the baseline;
   the on-screen five degrees is a direction cue, not proof of exact manual
   angle magnitude. Three stable distinct samples are required for each pose.
5. Return the joint near its zero before selecting the next joint. Repeat
   in policy order FL 4/5/6, FR 1/2/3, RL 7/8/9, RR 11/10/12.

Confirmations reset on changing the reference. If the operator cannot tell
which physical direction matches the model, do not guess the sign. Change
the camera and inspect correspondence first. Failed reads invalidate history;
stream restart/reconnect or a suspected raw wrap/jump requires a new neutral
baseline. A full 0/4095 crossing is not accepted as a direction measurement.

## Then, conservative limits

After directions are reviewed, select **Limits**. For each joint:

1. Return to neutral, confirm the physical ID/pose, and Capture neutral
   baseline. In Limits mode this preserves the verified sign and begins new
   endpoint captures. Switching modes alone does not perform this step.
2. **Show +5°** indicates the positive direction. Choose a comfortable,
   backed-off clear endpoint on that side by hand, without seeking a hard
   stop. Hold still, confirm and Capture positive endpoint.
3. Return through zero, then Show −5°, choose a comfortable clear negative
   endpoint and capture it. Keep other joints near their saved neutrals.
4. Each endpoint must be on the indicated model-angle side, within the
   simulated joint range, and at least 25 ticks beyond neutral. The tool
   retains an additional 25-tick inward margin in the usable raw interval.
   Do not force a larger interval merely to pass a planned trajectory.

These are manually checked intervals **with the other joints near neutral**.
They do not establish collision-free ranges for every combined pose. Existing
frame-contact, cable-clearance and ID2 position-ambiguity history must still
be reconciled before full-body powered testing. Smaller intervals may be
appropriate; offline trajectory checks will reveal whether a proposed replay
fits them. Actual guarded end travel and speed still require powered validation.

## Saved data and next handoff

Each accepted baseline/pose/endpoint saves a new timestamped
`calibrations/joint-checks-*.json` session. Save session is also available.
The file pins the exact zero-source hash, signed direction evidence, endpoint
samples, neighboring positions, and completion flags. It remains
`ready_for_motion=false`. The current calibration/mapping/firmware files are
not overwritten, and the old 60/120-tick supported replay profiles are not
silently enabled.

A complete session has all 12 signs and all 12 endpoint pairs. Partial
records explicitly remain incomplete. After capture, review the file before
promoting a new canonical calibration. In particular, legacy trajectory
generation still uses the historical hip +1 / knee -1 mapping; if measured
signs differ, that code must consume the new verified signs before generating
new commands. The ESP32 command transport also remains separate work.
