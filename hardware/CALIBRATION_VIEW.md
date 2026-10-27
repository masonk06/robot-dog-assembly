# Live calibration comparison

Run locally (not on HPC):

    .venv\Scripts\python.exe hardware\calibration_view.py

The blue robot is a reference pose. Select one joint and adjust its reference
angle or enable the slow 5-degree screen preview. The green robot shows the
encoder-driven pose when connected. No live data is represented by a gray
placeholder and explicit freshness status. Offline demo is orange and labeled
synthetic. The body pose is fixed; this is joint correspondence, not motion
capture of the robot's world position/orientation.

Choose the direct Waveshare USB servo-bus port (historically COM5) and connect
read-only. The existing direct-bus protocol uses 1 Mbps; an ESP32 console is not
a compatible direct servo connection without bridge firmware. Missing servos
produce stale/no-data rows rather than fabricated measurements. Serial opens
only when Connect is clicked. No position, torque, calibration or EEPROM write
instruction is implemented. The serial WRITE call only transmits a READ packet.
Other apps must release the selected port before connecting.

Mapping starts from physical_neutral_pose.json, the saved ID map and the shared
knee signs in joint_mapping.py. All four knees use -1; the front two were
corrected by the user's live comparison on 2026-10-26. Individual signs/zeros can be edited and saved into
display_joint_mapping.json. These edits change the display only; they neither
recenter a servo nor overwrite the original calibration. Existing script notes
do not encode every confirmed model-to-servo roll sign, so check correspondence
visually and adjust the viewer sign if needed. The user has reported joint
calibration complete; this tool does not invalidate that calibration.

Record CSV saves reference and measured angles, their geometric difference,
ticks, temperature, reading age and demo flag under runs/calibration. Because
the viewer never commands targets, these differences are not automatically a
servo tracking/latency measurement. They become such a measurement only if an
independent, synchronized controller supplies matching targets.

Disconnect/closing leaves the hardware's torque state unchanged. Move joints
manually only if their existing torque state and support allow it. This screen
does not deploy the walking policy or control the physical robot.

## Rear-left neutral/limit recapture

Open "Re-record rear-left limits" (or launch with --capture). The panel requires
fresh read-only telemetry, position mode and torque reported off for IDs 8/9.
Capture both at neutral first. For each joint, move it gently by hand to two
backed-off comfortable endpoints and capture A/B, keeping the other joint near
its captured neutral. Save checks that neutral lies between the endpoints with
25-tick margins. Demo data cannot be captured. The viewer does not turn torque
off automatically; if torque is on, do not force the joint by hand.

New records go under hardware/calibrations with timestamped filenames; the old
manual_range_of_motion.json and physical_neutral_pose.json are preserved. These
are manual measurements, not powered-trajectory validation. A new checked file
can be passed to prepare_policy_transfer.py with --calibration for the offline
trajectory-limit check before any powered replay.
