# Luca revision C — 1 oz copper prototype

This is the current cost-reduced PCB derived from revision B. **Use 1 oz finished
copper on each side only with this revision's files.** Do not select 1 oz for
the old revision B layout. Board outline remains 88.5 x 60 mm, with the same
four mounting-hole positions and the same circuit/pin nets.

Open `Luca_power_distribution_four_leg.kicad_pro` in KiCad 10. The fabrication
and assembly quote package is `jlcpcb_pcba_revC_1oz`; read `START-HERE.md` there.

## Changes that make this a different 1 oz layout

- F1 moved near the battery input to (151,110) mm; J3 moved to (161.5,95) mm.
- Raw-battery and fused-battery buses are 6 mm wide on **both copper faces**,
  connected by the through-hole power terminals. The old long detour is gone.
- Switched-servo trunk is also 6 mm on both faces, with sixteen 1 mm drilled
  stitching vias distributed near the leg feeds.
- Leg outputs use mainly 5/4 mm copper, with 1.5 mm long, 2.6 mm wide escapes
  at the SMD fuse lands. Each leg retains its selected 5 A slow-blow fuse.
- Ground pours cover both copper faces with solid pad connections and ground
  stitching vias. A sampled 6 mm-wide B.Cu ground corridor is checked between
  the battery return and each leg; see the audit's model limitations.
- F5 moved to (130,78) mm on top. **All 18 populated parts are top-side**:
  seven SMT and eleven through-hole. Bottom copper is still required.
- J7 and C2 moved slightly for clearance. Unused J10/J11 were moved to the
  left and remain DNP along with F7; no Pi circuitry was removed.
- Native stackup specifies 35 um copper on both sides and 1.6 mm total nominal
  thickness. Copper weight still must be selected explicitly on the order form.

## Assembly and interfaces

The parts and circuit are unchanged from revision B: 20 A MINI main fuse in a
Keystone 3568 holder; 1 A Bel adapter/AUX fuses; four 5 A Bel leg fuses; 470 uF
25 V bulk capacitor; 100 nF 50 V decoupler; external Pololu D24V10F5 5 V AUX buck.
The Pi/camera have a separate supply; F7/J10/J11 are unpopulated.

| Connector | Function / pins |
| --- | --- |
| J1 | XT60PW-M: **1 GND, 2 battery positive**; positive physically left in top view |
| J3 | External switch loop: 1 fused battery, 2 switched supply; neither is GND |
| J2 | Adapter supply: 1 fused battery, 2 GND; do not power legs through adapter |
| J7 | AUX buck: 1 fused battery input, 2 GND, 3 regulated 5 V return, 4 GND |
| J5 | AUX regulated output: 1 returned 5 V, 2 GND |
| J12/J13/J14/J15 | FL/FR/RL/RR power: 1 GND, 2 individually fused positive |

J1 remains right-angle with about 8.6 mm bottom-edge body overhang. Factory
rails, tabs and depaneling tooling must clear it. Its local footprint follows
the supplier's 2025V0 drawing: 2.9 mm holes, 0.8 x 1.9 mm reinforcement slots.

The selected servo harness remains three daisy-chained servos per leg, with
150 mm 22 AWG leads. The user assumes at least 5 A connector capacity; no
manufacturer contact-rating document has been supplied. A 5 A slow-blow fuse
does not impose an instantaneous current limit. DATA/common reference stay
connected to the adapter; do not join separately fused positive rails.

## Verification and limits

`DRC.txt` and `ERC.txt` record final CAD checks. `topology-and-ground-audit.json`
checks unchanged pin nets, fuse isolation, 6 mm duplicated buses, ground pours,
via count, mounting holes and all-top population. `power-path-screen.json`
uses **35 um** copper and reports explicit track-centerline path resistance;
it does not solve plane currents, parallel current sharing or temperatures.

This is a **validation prototype**, not a proven production current rating.
Loaded current, voltage drop, first cable/contact temperature, main copper/via
temperature and fault-clearing behavior still need bench verification. Exact
JLC sourcing/placement/DFM confirmation is required before paying for assembly.
No parts substitutions are authorized.

Build exports with `build_pcba_quote.py revision_one_oz`, run
`verify_one_oz.py` and `review_power_paths.py revision_one_oz` after CAD changes,
then bundle with `finalize_pcba_bundle.py revision_one_oz`. Refill zones before
final DRC/export. Do not blindly rerun construction/routing scripts.
