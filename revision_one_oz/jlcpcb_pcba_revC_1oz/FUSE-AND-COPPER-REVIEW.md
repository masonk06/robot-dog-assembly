# Revision C: 1 oz copper review

The circuit, 20 A prototype main-fuse selection, 1 A adapter/AUX fuses and four
5 A leg fuses are retained. Pi/camera remain separately supplied. The PCB was
rerouted and components repositioned specifically for **35 um / 1 oz copper
on both sides**; this is not a copper-weight change to the old layout.

## Track-resistance screening at 20 C

| Path | Revision B, 70 um | Revision C, 35 um |
| --- | --- | --- |
| Battery positive to F1 | 4.05 mOhm, 52.8 mm | 0.92 mOhm, 11.2 mm |
| F1 output to J3 input | 9.65 mOhm, 130.4 mm | 1.23 mOhm, 15.0 mm |
| Each fuse output to leg connector | about 1.19 mOhm | about 2.22 mOhm |

These values are shortest explicit centerline-path calculations. The shared
revision C paths each have matching 6 mm conductors on both faces. The values
above count a single path and do not take credit for both faces sharing current.
They exclude pad spreading, via barrels, solder, fuses, contacts and cables.
They are not a complete circuit or thermal simulation. At 5 A, 2.22 mOhm of
leg-output track corresponds to about 11 mV drop and 56 mW loss, before the
excluded items; the fuse and harness losses must still be included.

The major gain comes from removing long shared-current detours. New raw/fused
buses have no small via transition in series: both layers attach directly to
through-hole terminals. The switched trunk has sixteen distributed 1 mm drilled
stitches and direct through-hole feeding at J3. Plating and current sharing
still require manufacturing specification/bench validation.

## Ground and geometry

Both faces have filled ground pours with solid pad connections. The independent
audit samples a 6 mm-diameter free copper corridor on B.Cu from the battery
return to all four leg returns (0.5 mm grid; circle sampled every 15 degrees).
This is a geometric screen. It does not model drilled-hole annuli, local
current crowding, sheet-current distribution or temperature. DRC after the final
zone refill verifies connectivity and spacing but does not certify ampacity.

Main supply traces are 6 mm on each face; branch feed/output escapes are 2.6 mm
for 1.5 mm at the SMD lands, followed by broad copper. Leg outputs are mainly
5 mm, with short 4 mm approaches to connector pins. The actual 1 oz prototype
must be checked for loaded temperature rise and voltage drop.

## Protection assumptions that do not change

User expects less than 5 A per leg during walking and assumes at least 5 A
capacity for the 150 mm 22 AWG 5264-3P cable/connectors. These are unverified
operating/contact assumptions, not a guarantee of fault limits. Keep the 5 A
slow-blow fuses. Their manufacturer specifies up to 120 s opening at 200% of
rating and cautions against prolonged 100–200% operation. Nominal dissipation
of the 5 A part at rating is 1.5 W. Source:
https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf

Four legs at 5 A already total 20 A before adapter/AUX/relay current. The main
20 A fuse is not a promise of uninterrupted operation at that combined load.
Do not increase it without renewed coordination. The battery's 35C label is
not its prospective short-circuit current. Fuse selectivity and fault withstand
remain open validation items, as with revision B.

After assembly, inspect unpowered, start with a suitable current-limited supply,
measure startup and actual floor-supported walking current, and record voltage
drop and temperatures until stable. Do not deliberately short the LiPo or hold
servos in a damaging stall. Controlled fault testing requires suitable equipment.

Engineering basis for short/wide power connections and plane spreading:
https://www.analog.com/en/resources/technical-articles/layout-considerations-for-highpower-circuits.html
https://www.monolithicpower.com/en/learning/resources/motor-driver-pcb-layout-guidelines-part-1
