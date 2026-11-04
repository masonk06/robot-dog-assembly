# Luca power distribution — fabrication candidate

Status: HOLD — DO NOT ORDER. The electrical review dated 2026-11-03 found
incompatible proposed fuse footprints, a servo-adapter current limitation, and
substantial schematic/PCB topology disagreement. The earlier ZIP is obsolete
and is retained with a .DO_NOT_ORDER suffix. See ELECTRICAL_REVIEW.md.

## Order settings

- Bare PCB, 2 copper layers, FR-4, 1.6 mm board thickness.
- 2 oz finished outer copper on BOTH sides; select this explicitly when ordering.
- Nominal outline: 68.5 x 60.0 mm.
- Solder mask both sides; silkscreen as exported. No stencil required (all THT).
- Upload only the fabrication ZIP. It contains seven Gerber layers and separate
  plated/non-plated Excellon drill files, all using the same absolute origin.
- Review JLCPCB's rendered preview and order settings before payment.

## Changes and checks

- Added a continuous 3.0 mm B.Cu return from J2 pad 2 to the main ground network.
- Verified all power-connector ground pads connect without sub-1 mm traces;
  the previous 0.5 mm C2 connection is no longer the only J2 return.
- Hid unassigned mounting-hole REF** placeholders to remove edge-clipped silk.
- Preserved component placement, board outline, and original source files.
- No copper zones are present; no zone fill is required.
- DRC.txt records the final rule-check result. Custom fabrication rules include
  0.2 mm clearance, 0.5 mm minimum track width, 0.3 mm minimum hole size,
  0.254 mm minimum plated annular ring, and 0.5 mm copper-to-edge clearance.
- J1 pad 1 = /VBAT_RAW, pad 2 = GND.
- J3 pad 1 = /VBAT_FUSED, pad 2 = /SERVO_V+; no board-level copper bypass.

## Hardware release items still required

1. Confirm exact XT60 part against the selected AMASS footprint, physical
   polarity, pin dimensions, and mating orientation.
2. Specify F1, F2, F5, F7 fuse parts, current ratings, DC voltage ratings, and DC
   interrupt ratings appropriate to the battery's available fault current.
3. Confirm servo models/count and measured/estimated continuous and stall/peak
   currents; verify 3 mm main and 1 mm auxiliary paths against these loads.
4. Confirm terminal-block actual part numbers and electrical current ratings.
5. Confirm buck module inputs/outputs, connector pinouts, wiring, and Raspberry
   Pi USB-C power arrangement. Verify Waveshare adapter current under operation.
6. Physically check fuse replacement access, terminal screwdriver/wire clearance,
   XT60 mating space, and enclosure/standoff fit. A footprint DRC cannot prove this.
7. Verify capacitor voltage ratings against actual rail maximum voltage.

The original schematic on disk contains components beyond this PCB's footprint
set, and the open schematic previously had unsaved edits. Schematic-to-PCB parity
has therefore NOT been certified by this package. Resolve the authoritative
schematic before a production release.

This package is for bare-board fabrication, not a turnkey PCBA assembly order.
