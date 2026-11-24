# P2S camera chassis adapter

`camera_chassis_adapter.scad` is a deliberately separate, reversible adapter
between the active P2S chassis and a Raspberry Pi Camera Module 3 board. The
"IMX708" marking identifies the sensor used by that camera family. It is
needed because the chassis and camera mounting patterns differ:

| Interface | Pattern | Adapter hole |
| --- | --- | --- |
| Chassis mast | 2 holes, 34 mm lateral pitch, Z = 32 mm | 3.4 mm M3 clearance |
| Raspberry Pi Camera Module 3 (IMX708) | 4 holes, 21 mm lateral by 12.5 mm vertical pitch, centred at Z = 28.25 mm | 2.4 mm M2 clearance |

The dimensions are transcribed from the established P2S CAD geometry (not a
physical measurement). They apply to the standard Camera Module 3 board,
including Wide and NoIR optical variants, not to the larger High Quality
Camera. The existing camera and chassis remain unchanged.

`camera_chassis_adapter_imx708_open_top.step` is the editable solid exchange
file matching `camera_chassis_adapter_imx708_open_top.stl`. Import the STEP
into Onshape (not the STL) when changing the part there. `build_step.py`
recreates that STEP from the same dimensions as the SCAD source.

The centre of the adapter is intentionally open: its 16 × 22 mm window clears
the rear FFC connector and its cable, allowing the camera PCB to bear on the
adapter's outer rails instead of on that connector.

The rail ends above the upper camera holes are trimmed to a 1.3 mm rim. This
is intentionally close clearance: keep at least four walls and do not
overtighten the M2 screws.

## Print and fit

1. Render `camera_chassis_adapter.scad` in OpenSCAD and export an STL. Print
   the supplied orientation flat, at 100% scale, in PETG or another suitably
   tough material. Use at least 4 walls and 4 top/bottom layers. The plate is
   3.2 mm thick; do not scale it to compensate for a poor hole fit.
   The preview must show **six holes** and a large central open window: two
   larger M3 chassis holes near the ends and four smaller M2 camera holes in a
   rectangle. If it does not, press `F5` to reload the saved source before
   exporting.
2. With the robot powered down, first hold the adapter against the chassis and
   confirm that both M3 holes align without forcing either part. Then verify
   all four M2 camera-board holes. Ream only the printed
   adapter, a small amount at a time, if printer shrinkage prevents a fit.
3. Install the adapter with two M3 fasteners appropriate to the available
   chassis engagement. Install the camera insert with four M2 fasteners. Use
   washers where the head bears on printed plastic, keep the camera cable
   strain-relieved, and do not overtighten the plastic.
4. Before powered operation, check that the mount, cable, and camera clear all
   leg motion and the enclosure. This is a packaging part, not evidence that
   autonomous walking is safe.

The SCAD source is the editable source of truth so the measured pattern can be
updated after a physical test-fit. Record any measured deviation before
changing the nominal dimensions.
