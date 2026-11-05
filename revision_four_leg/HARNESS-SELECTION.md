# Selected harness design — 2026-11-04

Latest user operating details and telemetry limitations are recorded in
`OPERATING-CONTEXT.md`: walking only, 150 mm 22 AWG servo leads, AUX for
NodeMCU ESP32S/MPU6050, and a completely independent Pi/camera power source.
The retained Pi branch is unused in this assembly; omit F7 and the external
Pi buck, and leave J10/J11 unconnected. This is an assembly designation, not
a deletion of the existing circuit or a newly released manufacturing BOM.

These are design selections for the existing four-leg revision, not a claim of
completed thermal, fault-interruption, or robot testing. Do not order the earlier
prototype ZIP as the updated design: its J3 connector is now superseded.

## Wire and length limits

Use flexible stranded **pure copper**, with insulation rated at least 105 C,
proper strain relief, and protected routing. Do not use copper-clad aluminium.
Lengths below are design maximums, not measurements of the robot.

| Circuit | Selected gauge | Maximum conductor length |
| --- | --- | --- |
| Battery to J1 | 12 AWG | 250 mm each for positive and ground |
| J3 external series contact loop | 12 AWG | 250 mm outgoing plus 250 mm returning |
| Each PCB leg output to local distribution | 16 AWG | 400 mm each for positive and ground |
| Relay coil and panel switch | 22 AWG | 500 mm each conductor; separately fused at source |

At 20 C, using nominal copper resistance of 5.21 mOhm/m (12 AWG) and
13.17 mOhm/m (16 AWG), the battery cable pair drops approximately 0.052 V at
20 A; the switch-loop cable adds another 0.052 V. Each leg cable pair drops
approximately 0.085 V at 8.1 A, or 0.028 V at 2.7 A. These calculations exclude
contacts, fuses, PCB copper, splices, and the original servo leads. Hot copper
has higher resistance. Wire gauge alone does not establish system ampacity.

The user's selected harness is a 16 AWG feeder injecting power at the start of
each three-servo daisy chain, retaining its 150 mm 22 AWG links and a 5 A leg
fuse. Expected walking load is below 5 A per leg, as a user-supplied design
assumption; this is not a measured fault-current ceiling. The first connector
carries the aggregate leg current and remains a ratings/temperature check.
Retain DATA continuity and servo IDs. Keep the four fused positive rails separate, including from adapter
V+. Use the dedicated ground returns; avoid additional thin inter-leg ground
links carrying parallel motor-return current. Check DATA backfeed with one leg
unpowered before commissioning.

## Switch and PCB interface

Selected external power relay: **Panasonic CB1a-R-12V / ACB33221**, SPST normally
open, resistor-suppressed 12 V coil. Manufacturer specifies 40 A at 14 V DC for
resistive switching and a 10–16 V usable coil range. Use a matching automotive
socket with genuine contacts and 12 AWG contact leads, rated for the intended
current; no unidentified thin prewired socket. Capacitive inrush, vibration,
hot-coil operation, and battery sag must be checked in the actual assembly.
This relay is not a battery undervoltage cutoff or certified emergency stop.

Panel toggle selection: **C&K 7101SYZQE**, SPDT; use common and one throw as
ON/OFF for the coil only. Insulate the unused terminal. Protect the coil/control
feed with a **1 A inline fuse immediately at its fused-positive source**.
Select the inline holder and fuse with a verified DC breaking capacity adequate
for the battery fault source; that holder/fuse part is not finalized here.

Relay normally-open power contacts bridge J3 pins 1 and 2 only when energized.
J3 pin 1 supplies the control branch through its separate 1 A fuse; the coil
returns to common ground. Follow the actual relay terminal diagram/markings;
do not infer coil or contact terminal positions from socket wire colours.
Both J3 terminals are POSITIVE; neither is a ground terminal.
The Pi branch remains upstream of J3 as in the existing circuit.

J3 replacement: **Phoenix Contact 1868076, MKDS 5/2-7,62**. Manufacturer nominal
32 A, cULus use-group B 30 A; flexible conductors up to 4 mm2. Strip 8 mm,
tighten to 0.5–0.6 Nm, support the terminal body while tightening. Use a correctly
crimped compatible ferrule for fine strands; do not tin strands under the screw.
Installed height 21.5 mm and 5.1 mm pin protrusion require chassis clearance.
Local footprint uses 7.62 mm pitch, 1.3 mm holes, 15.24 x 12.5 mm body, and the
manufacturer's 4.6 mm rear-to-pin-row offset. Verify the purchased part at 1:1.

## Protection and release gates

**20 A mini-blade main fuse is a coordination target, not an approved BOM value.**
The existing Keystone 3568 holder is rated 30 A. Do not substitute a 5 A main
fuse or increase its rating to accommodate all-servo stalls. Common copper,
connector and fuse time/current performance need coordination at this target.

Retain Bel 0680H5000-05 5 A slow-blow leg selections as provisional only.
An 8.1 A leg stall is 162% of fuse rating. Independent overload shutdown and
startup measurements are needed; the fuse is not established as stall
protection. Adapter, auxiliary and Pi branch ratings also remain provisional
until their loads and downstream conductors are verified. A DC voltage rating
alone is not a breaking-capacity verification.

Outstanding: shared-copper thermal/pulse limits and neckdowns; measured startup
and stall shutdown behavior; branch-wire/servo-contact ratings; battery fault
current versus fuse interruption; physical XT60 mating part/polarity; Pi buck
selection and USB-C implementation; actual harness fit and powered load tests.
Do not deliberately short the LiPo to measure fault current.

## Manufacturer references

- Phoenix: https://www.phoenixcontact.com/en-us/products/printed-circuit-board-terminal-mkds-5-2-762-1868076
- Phoenix dimensioned drawing, saved locally: manufacturer_references/Phoenix_1868076_plan.jpg
- Panasonic: https://industry.panasonic.com/global/en/products/control/relay/vehicle/number/acb33221
- C&K selection guide: https://www.littelfuse.com/assetdocs/ck-switch-product-guide?assetguid=e92eb96b-8f0d-4054-b6d0-2251598e197a
- Keystone: https://www.keyelco.com/product.cfm/product_id/306
