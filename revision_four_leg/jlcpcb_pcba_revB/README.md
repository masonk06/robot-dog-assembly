# Luca power distribution — revision B prototype PCBA

Current CAD: `Luca_power_distribution_four_leg.kicad_pro` (KiCad 10).
This modifies the existing design; the board is 88.5 x 60 mm and retains the
original four mounting-hole positions. Original files outside this revision
remain preserved.

## Current release state

Revision B is prepared for a **validation-prototype fabrication/assembly quote**.
It is not approved as a thermally/fault-validated production design. The current
package is `jlcpcb_pcba_revB`; start with its `START-HERE.md`. Earlier prototype
exports and `_history` are superseded and must not be ordered.

Checks: zero DRC violations, zero unrouted connections, zero schematic-parity
issues and zero ERC violations. Independent topology/polarity/return-path checks
are in `topology-and-ground-audit.json`, bound to the PCB hash. These establish
CAD consistency, not a proven current rating.

## Circuit and assembly selections

| Reference | Assembly / function | Pin assignment |
| --- | --- | --- |
| J1 | PCB-mount AMASS XT60PW-M, right angle | **1 GND, 2 battery positive** |
| F1 | Keystone 3568 MINI holder; separate 20 A Littelfuse 0297020.WXNV insert | raw battery to VBAT_FUSED |
| J3 | Phoenix 1868076 high-current series switch loop | 1 VBAT_FUSED; 2 switched SERVO_V+; neither is ground |
| F2 / J2 | 1 A Bel slow-blow; Phoenix 1715721 adapter output | J2: 1 fused battery positive, 2 GND |
| F5 / J7 | 1 A Bel slow-blow; Phoenix 1715747 external AUX buck interface | J7: 1 fused battery input, 2 GND, 3 regulated 5 V return, 4 GND |
| J5 | Phoenix 1715721 regulated AUX output | 1 returned 5 V, 2 GND |
| F8 / J12 | 5 A Bel slow-blow, FL leg, AMASS XT30UPB-M | J12: 1 GND, 2 fused positive |
| F9 / J13 | 5 A Bel slow-blow, FR leg, AMASS XT30UPB-M | J13: 1 GND, 2 fused positive |
| F10 / J14 | 5 A Bel slow-blow, RL leg, AMASS XT30UPB-M | J14: 1 GND, 2 fused positive |
| F11 / J15 | 5 A Bel slow-blow, RR leg, AMASS XT30UPB-M | J15: 1 GND, 2 fused positive |
| C1 | Nichicon UPW1E471MPD, 470 uF, 25 V, D10 x 16 mm, pitch 5 mm | 1 positive, 2 GND |
| C2 | Samsung CL21B104KBCNNNC, 100 nF, 50 V, X7R, 0805 | switched supply decoupling |
| F7, J10, J11 | **DO NOT POPULATE**; preserved Pi circuit | Pi/camera use an independent source |

**J1 numbering changed from the old solder-cup footprint.** The PCB-mount part
uses manufacturer/library pad 1 negative and pad 2 positive. Positive remains
physically left in the top board view. J1 is rotated 180 degrees, with the body
overhanging the bottom edge by about 8.6 mm. Its 2025V0 supplier drawing requires
2.9 mm electrical holes and 0.8 x 1.9 mm reinforcement slots. Local enlarged lands
retain at least the project's annular-ring minimum. Do not substitute a generic
wire-type XT60 into the new footprint.

F5 is bottom-side SMT. The other populated SMT parts are top-side. There are
18 populated PCB components: 7 SMT and 11 through-hole; plus a separate main
blade-fuse insert. JLC must confirm exact sourcing and assembly eligibility.

## Off-board integration

- Battery: user-selected 3S LiPo, 11.1 V nominal / 12.6 V full.
- External AUX buck: Pololu D24V10F5 / #2831, fixed 5 V, typical 1 A capability;
  wire through J7 and verify 5 V at J5 before attaching the NodeMCU ESP32S.
  Connect the MPU6050 using its verified 3.3 V supply/interface requirements;
  identify the actual breakout's regulator/pinout before wiring it.
- External switch: Panasonic CB1a-R-12V relay contacts bridge J3; panel toggle
  controls only its coil. See `HARNESS-SELECTION.md` and external-purchases CSV.
- Selected harness: 12 AWG battery/switch loop, 16 AWG leg feeders, then each
  existing three-servo chain with 150 mm 22 AWG 5264-3P leads. User assumes at
  least 5 A connector capacity; it is **unverified**. Retain 5 A leg fuses.
- Adapter handles serial DATA/common reference and its own supply; it does not
  carry the four legs' main current. Never join its positive rail or different
  leg-positive rails downstream of their separate fuses.
- Pi/camera supply positive must not join this board's supply. Review USB/other
  wired links for unintended power paths. Wireless links avoid that power tie.

## Validation and files

`pcba_parts.json` is the selected quote BOM. The manufacturer part numbers are
explicit; several require JLC global sourcing/consignment confirmation, and no
substitutions are approved. `power-path-screen.json` estimates track-centerline
resistance at 20 C / 70 um copper, excluding vias, contacts, fuse and harness
losses. Shared paths have 4 mm sections where clearance permits; constrained
sections, paired vias and small parallel spokes remain. Individual fused leg
positive traces are at least 3 mm. No uniform bus-current rating is asserted.

Before regular powered use, validate actual current peaks, first-lead/contact
temperature, main-path/via temperature, voltage drop, switch behavior and fault
clearing. The selected 20 A main and 5 A leg fuses are prototype choices; the
leg fuse is not an instantaneous 5 A current limiter. See the dated reviews for
details; this README and the revision B package override older pin/BOM tables.

To rebuild the quote exports, use `build_pcba_quote.py` with KiCad's Python.
Construction/routing scripts are engineering utilities and must not be rerun
blindly against finalized placement. Historical trials are under `_history`.

Manufacturer references, selection sources and fabrication/assembly instructions
are included in the quote package. Copper weight must be ordered explicitly as
**2 oz finished copper on both sides**; Gerbers alone do not specify it.
