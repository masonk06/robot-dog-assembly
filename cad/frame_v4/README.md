# RoboDog V4 — hip-roll screw-hole reinforcement

This revision addresses the user's reported crack origin: the outside screw
holes at the four hip-roll mounts. It retains the V3 battery cradle, Jetson
tray posts, Waveshare mounting provision, and wire slots.

## Changes

- Extrudes each original inboard mounting face 5 mm farther toward the frame
  centre. The nominal 5 mm flange becomes approximately 10 mm thick.
- Copies the exact face wires, so the original screw-hole pattern and middle
  openings continue through the added material. Servo-side seating faces and
  hole locations are not moved.
- Adds a low 17 x 25.5 mm load-spreading foot and two 4 mm thick triangular
  gussets at each mount. Gussets stay below Z=19 mm, below the lower screw
  centres and the middle opening.
- Clips added material against the saved hip-roll servo case solids, and
  checks for any increase in case interference relative to V3.
- Retains the 170 x 180 mm printable envelope. There is no extra room for a
  brim/skirt beyond the 180 mm dimension; verify the slicer's usable area.

## Files

- `Frame_V4_Reinforced.step`: editable replacement-frame solid for Fusion.
- `Frame_V4_Reinforced.stl`: printable replacement-frame mesh, millimetres.
- `RoboDog_Frame_V4_Assembly.step`: frame plus the existing removable Jetson
  and Waveshare trays from V3.
- `Frame_V4_preview.png`: rendered model of the reinforced frame.
- `validation.json`: solid validity, dimensions, exact flange-face records,
  and static servo/electronics intersection checks.
- `build_frame_v4.py`: reproducible OpenCascade construction.

The original files and live Fusion assembly are not overwritten. The trays
from `cad/frame_v3/` remain compatible; their existing mounting-pattern and
physical-fit limitations still apply.

## Engineering limits

Added flange thickness spreads screw loading through more material; it does
not prove that cracking is eliminated. The original hole-edge distances and
small screw bores remain unchanged. Do not force an oversized screw through
them. Check the actual screw diameter and engagement, head/washer seating,
and fastener preload before assembly. No new screw size is specified by this
revision. Original screw-side seating is retained, so longer fasteners are
not automatically required; check the hardware against the physical part.

Static servo-case and electronics packaging checks do not establish full
joint-sweep clearance, cable routing, printed strength, or structural fatigue
life. Trial-fit one mount and articulate it with torque off before installing
all legs. This revision has not undergone FEA or a load test.

## Regenerate

From the repository root, with the system Python containing OCP:

```powershell
python cad/frame_v4/build_frame_v4.py
```
