# Active Luca CAD

This directory intentionally contains only the current printable and editable
design files. Earlier frame studies stay out of the published project so a new
clone starts with the hardware that is relevant now.

## Active parts

- `frame_p2s_camera_insert/` — current P2S chassis, camera insert, Raspberry
  Pi tray, perfboard carrier, and Waveshare adapter mounting options. The
  `RoboDog_P2S_Camera_Onshape.step` assembly is the main editable reference.
- `camera_chassis_adapter/` — reversible, parametric adapter from the P2S
  chassis mast holes to the current camera insert's four-hole pattern. Its
  dimensions still require a physical, power-off test fit before an STL is
  treated as final.
- `luca_enclosure/` — printable enclosure and assembly exports.
- `luca_enclosure_v2/` — serviceable enclosure concept: fixed frame, removable
  lid, battery hatch, cooling and protected I/O zones. It is deliberately a
  measurement-gated design baseline, not a released print pack.
- `retaining_electronics_trays/` and `velcro_trays/` — current alternatives
  for retaining the perfboard, Pi, and Waveshare adapter.
- `luca_test_stand/` — supported-test stand used for safe calibration/replay.

CAD units are millimetres. The MuJoCo P2S preview currently derives its chassis
mesh from `frame_p2s_camera_insert/Chassis.stl`.
