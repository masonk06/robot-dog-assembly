# Active Luca CAD

This directory intentionally contains only the current printable and editable
design files. Earlier frame studies stay out of the published project so a new
clone starts with the hardware that is relevant now.

## Active parts

- `frame_p2s_camera_insert/` — current P2S chassis, camera insert, Raspberry
  Pi tray, perfboard carrier, and Waveshare adapter mounting options. The
  `RoboDog_P2S_Camera_Onshape.step` assembly is the main editable reference.
- `luca_enclosure/` — printable enclosure and assembly exports.
- `retaining_electronics_trays/` and `velcro_trays/` — current alternatives
  for retaining the perfboard, Pi, and Waveshare adapter.
- `luca_test_stand/` — supported-test stand used for safe calibration/replay.

CAD units are millimetres. The MuJoCo P2S preview currently derives its chassis
mesh from `frame_p2s_camera_insert/Chassis.stl`.
