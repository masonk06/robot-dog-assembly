# RoboDog V5 — servo roofs and side bracing

This separate revision adds a roof and a windowed inner side panel above each
of the four fixed hip-roll servo cases. It builds on V4's thickened screw
flanges and lower gussets. The existing hole pattern, servo seating, battery
cradle, Jetson tray, and Waveshare sled are retained.

## Printable parts

- `Frame_V5_Servo_Canopies.step`: frame solid for Fusion.
- `Frame_V5_Servo_Canopies.stl`: replacement frame for slicing, millimetres.
- `RoboDog_Frame_V5_Assembly.step`: frame and both existing electronics trays.
- `Frame_V5_preview.png` / `Frame_V5_top.png`: rendered frame views.
- `validation.json`: dimensions and geometry checks.

The roof and side frames are integrated into the frame print, not separate
covers. The V3 Jetson and Waveshare trays are unchanged and remain separate
printable parts (`cad/frame_v3/Jetson_Tray.stl`, `Waveshare_Sled.stl`).

## Reinforcement and access

Each 4 mm roof joins a 4 mm inner side frame and a top crosspiece tied into
the reinforced screw flange. This creates an additional load path around the
servo pocket. The roof underside is at Z=52.5 mm; the saved fixed-case bounds
top out at Z=50.4003 mm, giving approximately 2.1 mm static height clearance.
The side frame stops short of the saved case side by approximately 0.6 mm.
These are nominal CAD clearances; printer fit and actual cable plugs vary.

Each inner panel has a 24 x 29 mm rounded service/wire window. The outer side
and outer end remain open for installation, connector access, and removing
print supports. Screw access from the original mounting side is retained.

The roof covers most of each fixed case; the last approximately 3.4 mm of its
outer nose remains exposed. Extending solid walls around the entire case at
both ends would exceed the requested 180 mm envelope. The generated frame is
177 x 180 x 56.5 mm. A brim or skirt must not exceed the slicer's usable area.

## Validation scope

The builder checks one valid connected frame solid, the 180 x 180 mm bed
limit, all 12 servo cases and output discs plus the four printed roll brackets
at their saved static CAD placements, and the existing electronics trays and
packaging envelopes. It fails if it adds more than 0.01 mm3 interference.
Historical baseline assembly overlaps are retained, not declared correct.

Full joint sweeps, the current unsaved Fusion revision, actual plug bodies and
wire bend radii, and structural strength/fatigue still require validation.
The two-pass before/after static check cannot establish those properties.
The design creates an additional structural load path; it is not a guarantee
that the printed screw holes cannot crack. Screw fit and tightening load still
matter, and this design does not change the original screw diameter.

Inspect the roof underside in the slicer. Depending on the print settings,
local supports or bridging may be needed. Remove all support from each pocket
and fit the fixed servo with torque off before installing the moving leg.

## Rebuild

With system Python containing OCP, numpy, and matplotlib:

```powershell
python cad/frame_v5/build_frame_v5.py
```

Previous frame files and the live RoboDog assembly are preserved.
