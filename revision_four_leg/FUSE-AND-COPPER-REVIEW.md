# Four-leg power review — 2026-11-04

## Selected configuration

Retain **5 A per leg**, Bel 0680H5000-05 slow-blow SMD at F8–F11, with the
existing three-servo daisy chain on each leg. The user expects walking current
below 5 A per leg. This is the operating assumption, not a measured fault limit.
No per-servo power split or electronic current limiter has been added.
Pi/camera have an independent source; the existing Pi branch is unused.

## Fuse findings

The manufacturer specifies a maximum 120 s opening time at 200% rating,
and cautions against prolonged operation between 100% and 200% because of
overheating/desoldering. The 5 A version has nominal 0.30 V drop and 1.5 W
dissipation at rated current. Consequently, four branches near 5 A can dissipate
about 6 W in their fuses alone. Startup pulses, ambient temperature, and actual
loading matter. The retained fuse is not a hard 5 A limiter.

Manufacturer interruption ratings cover 500 A at 125 V DC and 5000 A at 72 V DC.
The battery's 35C discharge label is not its prospective short-circuit current;
fault-source and application coordination remain unverified.

Source: https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf

## Shared-current budget

| Scenario | Servo current alone | Implication |
| --- | --- | --- |
| Previously stated 0.9 A per servo | 10.8 A | Reference arithmetic, not a measured gait maximum |
| Four legs simultaneously at 5 A | 20 A | Add adapter, AUX and relay current; exceeds a 20 A total budget |
| Twelve simultaneous 2.7 A stalls | 32.4 A | Fault/transient case, not intended continuous operation |

The proposed 20 A main fuse remains a target pending coordination; it cannot
promise uninterrupted operation with all four legs near 5 A plus electronics.
Do not automatically increase it. Branch/main time-current selectivity is not
established. The supplied sequential servo telemetry does not settle this budget.

## Copper changes and screen

The common positive nets and ground now use 4 mm track sections where the
existing geometry permits, with 3 mm retained at constrained sections. Original
paired-via transitions and small parallel spokes remain; they are not equivalent
to a uniformly 4 mm bus. Individual fused leg-positive tracks remain at least
3 mm. Net assignments, J3 series-loop topology, mounting holes and board outline
are preserved. Final geometry/check results are in DRC.txt and
topology-and-ground-audit.json.

`review_power_paths.py` generates `power-path-screen.json` from the actual PCB.
It estimates resistance along explicit track centerlines at 20 C and 70 um
copper. It excludes fuse resistance, pad spreading, via-barrel resistance,
contacts, solder and harness resistance, and does not solve parallel copper
current sharing. It is a routing screen, not a temperature or ampacity model.
The 1.2 mm minima reported in some paths are layer-transition spokes; multiple
spokes/vias must be evaluated together rather than treating one as the entire bus.

A shorter F1-to-J3 route was screened on both copper layers and with paired-via
transitions. No substantially shorter route fit the current placement and
clearances, so the existing connected route is retained. Its centerline model
reports approximately 9.65 mOhm of track resistance before via/contact losses.
This remains a priority for measured loading/temperature checks and possible
placement revision; the wider sections do not close that release gate.

## Required validation before electrical release

1. Identify the actual servo connector contacts and cable material. Generic
   '5264/JST' compatibility is insufficient for an aggregate-current rating.
2. Capture total battery current and one leg's input current during startup,
   representative floor-supported walking, turns and recovery. Use a calibrated
   shunt/instrument with transient capture, not summed sequential servo reports.
3. Validate fault clearing/current shutdown against the harness and copper.
   Do not deliberately short the LiPo or hold the robot in a damaging stall.
   Fault tests require suitable current-limited equipment and a controlled setup.
4. Check fuse, connector, main-path, via and first servo-lead temperatures after
   operation reaches thermal equilibrium in the intended installation. Record
   ambient, current and temperatures; limits must come from actual parts and
   insulation, not a touch test.
5. Verify actual XT60 mating part/polarity and AUX development-board supply input.

No final fabrication release is asserted by this review. Bench thermal tests
require an assembled prototype; any initial bare-board order must be explicitly
identified as a validation prototype rather than a proven production design.
