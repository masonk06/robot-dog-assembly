# RoboDog V6 — Pi 5 and modular battery-power frame

This revision continues V5's four roofed hip-roll pockets, thick screw flanges,
and low gussets. It replaces the Jetson tray with a Raspberry Pi 5 deck and
adds a removable lower power-distribution sled. The existing Waveshare tray
and the user's 75 x 34 x 25 mm battery layout are retained.

## Open and print

- `RoboDog_V6_Complete.step`: assembled printable parts for Fusion.
- `RoboDog_V6_Equipment_Layout.step`: adds named electronics and power
  envelope solids. Do not print the reference blocks.
- `Frame_V6.stl`: replacement frame with integrated servo roofs and braces.
- `Pi5_Electronics_Deck.stl`: removable Pi 5 deck, including four Pi pillars.
- `Power_Distribution_Sled.stl`: removable universal lower power mount.
- `Waveshare_Sled.stl`: board tray copied into this folder for a complete set.
- `Regulator_Spacer.stl`: print four if using the proposed 4 mm regulator rise.
- Each part also has a corresponding editable STEP file.
- `validation.json`: all generated dimension and interference checks.

The frame is 177 x 179.8 mm in XY, with a 56.5 mm roof height. Only 0.1 mm per
side was removed from V5's outer Y edge; the original mounting flange faces
end at |Y|=89.8485 and remain inside that boundary. There is effectively no
room for an external brim in Y. Each accessory is also under 180 x 180 mm,
but print the frame and accessories on separate plates or arrange separately.
All STLs use mm and assembled coordinates: lay each accessory flat in the
slicer before printing. Inspect the servo roofs for bridge/support requirements.
Keep scale at 100%; do not shrink the model to make room for a brim, because
that would change servo-hole spacing and electronics fits.

## What fits where

| Part | Location | Mount/allowance |
| --- | --- | --- |
| Pi 5 8GB, bare board and cooler | Upper deck, above battery | 85 x 56 mm board; 58 x 49 mm hole pitch; four 2.7 mm clearance bores; board bottom Z=46 |
| Battery | Low and centered | User's 75 x 34 x 25 mm pack in existing 79 x 38 mm cradle, with two 15 mm straps and 0.8 mm pad allowance |
| Waveshare Adapter (A) | Lower +Y side, next to battery | Four bosses on 37 x 28 mm pitch, plus two separate tray-to-frame screws |
| Fused servo power distribution | Lower -Y removable sled | Generic 60 x 20 x 18 mm reservation; strap slots and mounting grid |
| Pi battery regulator | Upper deck, +Y side | Generic 50 x 28 x 20 mm reservation on four 4 mm spacers; adjustable parallel slots |
| Switch or switch adapter | Upper service corner | Generic 16 x 16 x 20 mm reservation; adjustable slots, no assumed panel cutout |
| Future balance sensor (IMU) | Raised lower-deck pad beside battery | Generic 25 x 18 x 10 mm reservation with adjacent tie slots; exact sensor not selected |

The Pi sits on four printed 6 mm pillars above the 3 mm deck. Use appropriate
M2.5 through-screws/nuts, or revise the mount to purchased threaded standoffs.
The open deck centre permits airflow and access under the board. The Pi's
stock eBay enclosure is not installed in this layout: its dimensions and cooler
compatibility are unknown. The 28 mm reference height above the board bottom
is a conservative package volume, not the exact cooler or component surfaces.

The regulator, fuse/distribution board, and switch are not selected products.
Their blocks show reserved space only. Purchase/confirm hardware that fits
these envelopes *including terminals*, or adjust the trays before printing.
Use insulating spacers under exposed boards. Do not infer electrical suitability
from a CAD envelope or from a module's advertised current alone.

The IMU pad is rigidly joined to the chassis, with a 1 mm rise above the floor.
Use thin insulating mounting tape and secure wiring without straining the
sensor. The reserved size is not a claim that every IMU breakout fits.

## Connector and wiring access

- No top cover over the Pi cooler, GPIO, or electronics deck.
- Pi USB/Ethernet edge faces +X; leave space between it and the end wall for
  plugs and bends. USB-C/HDMI edge faces -Y toward the open central side.
- Waveshare keeps its outward-facing side access and removable tray.
- Existing floor cable slots and servo-panel service windows are retained.
- Regulator output and Pi power cable stay on the upper deck; motor wiring
  runs on the lower deck, with space reserved for a fuse/distribution module.
- Place the accessible motor-power disconnect/switch at the service corner
  using an adapter appropriate to the selected switch. A high-current switch
  is not automatically suitable merely because its body fits.

The official wall PSU, microSD reader, battery charger, and setup cables are
off-robot equipment and have no internal mounts. The microSD lives in the Pi.

## Assembly hardware

- Four M3 tray screws for the Pi deck, two for the power sled, and two for
  the Waveshare sled. Frame pilots are 2.6 mm; choose compatible plastic
  fastening hardware and engagement length for the blind holes.
- Four M2.5 Pi fasteners with nuts for the printed through-hole pillars.
- Four suitable M2 board screws for the Waveshare's 2.2 mm printed pilots.
- Two 15 mm battery straps, a thin soft battery pad, and cable ties.
- Appropriate insulated regulator spacers/fasteners and a switch adapter,
  depending on the selected power parts. Four printable spacer copies are
  provided; the model does not assume a particular regulator screw pattern.

Select fastener lengths against the physical printed parts and board
undersides; avoid screws contacting components or the battery.

## Electrical integration still required

Use a Pi 5 compatible regulated supply from the 3S LiPo, with a verified USB-C
connection/power arrangement. A nominal 5 V/5 A buck alone does not establish
correct Pi 5 power negotiation, transient response, or cable-drop behaviour.
The LiPo voltage must never go directly to the Pi's 5 V power input.

The Waveshare Adapter (A) is a signal/control adapter with a stated 5 A current
limit. The physical lower power mount is reserved so the twelve motors can
receive power through suitably rated wiring/distribution rather than forcing
their combined load through that adapter. Final fuses, wire sizes, switches,
common-ground topology, and voltage protection depend on measured current and
the selected parts. This CAD revision does not specify a completed wiring circuit.

## Sources and checks

Pi board and mounting geometry: [official Pi 5 mechanical drawing](https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf).
Waveshare geometry is retained from V3; current rating: [vendor FAQ](https://docs.waveshare.com/Bus_Servo_Adapter_A/FAQ).

Generation checks valid connected printable solids, individual plate-size
bounds, pairwise print-part intersections, electronics/reserved-volume
intersections, and all 12 saved servo cases. Existing V5 checks cover its
unchanged servo roofs, output discs, and printed hip-roll brackets. These are
static checks using saved placements, not full calibrated motion sweeps.
No structural fatigue, heat, cable-bend, or physical printed-fit test has been
performed. Original frame files and hardware calibration are preserved.

## Rebuild

Use Python 3.14 with the installed OCP, numpy, and matplotlib packages:

```powershell
py -3.14 cad/frame_v6/build_frame_v6.py
```
