# Luca revision B — validation prototype / PCBA quotation

This is the current replacement for all earlier fabrication packages.
It contains a fresh fabrication ZIP, full assembly BOM, CPL, assembly drawings,
selected external-parts list and CAD verification results. It is ready for
**supplier quotation/engineering review**, not a pre-approved paid order or
a claim of validated powered-use safety.

## Files to use

1. Upload **Luca_RevB_FAB_PROTOTYPE.zip** as the PCB fabrication file. It contains
   seven Gerbers and separate plated/non-plated Excellon files, not the BOM.
2. Select PCB assembly and upload `assembly/BOM_FULL_QUOTE.csv` and
   `assembly/CPL_FULL_QUOTE.csv`.
3. Review `assembly/SOURCING_STATUS.csv`. Empty LCSC codes are intentional:
   the exact MPN requires JLC global sourcing/consignment confirmation. Do not
   accept automatic substitutions or silently omit unmatched parts.
4. Ask JLC to review `assembly/ASSEMBLY_TOP.pdf` and `ASSEMBLY_BOTTOM.pdf` and
   its component-placement preview. The CPL uses physical fabrication-outline
   centroids; `CENTROID_DATUM_REVIEW.csv` and `KiCad_ORIGINS_REFERENCE.csv`
   document the coordinate origins for engineering alignment. Rotation/model
   zero conventions must be confirmed in JLC's own preview before ordering.

## Quote requirements

- FR-4, two layers, 1.6 mm thick, **2 oz finished copper on BOTH sides**.
- Outline 88.5 x 60.0 mm; preserve the four 3.2 mm non-plated mounting holes.
- Request double-sided SMT plus through-hole/manual assembly. Start with
  Standard PCBA; ask JLC to confirm the appropriate service for this mix.
- 18 populated PCB components: 7 SMT and 11 through-hole. F5 is bottom-side.
  No assembly of **F7, J10 or J11**. H1–H4 are mounting holes, not components.
- F1 BOM item is the **Keystone 3568 holder only**. The separate 20 A
  Littelfuse 0297020.WXNV blade insert is listed under external purchases;
  leave it out during shipping/initial unpowered inspection or quote it as a
  separate manual insertion operation. It has no CPL row.
- C1: positive lead into pad 1. All other capacitors/fuses are nonpolar.
- **J1 pad 1 GND; pad 2 battery positive.** PCB-mount AMASS XT60PW-M, rotated
  180 degrees; positive is physically left in the top assembly drawing.
  Supplier C98732 currently links AMASS 2025V0 model XT60PW-M30.G.Y.T.
  Electrical holes are 2.9 mm; reinforcement slots are 0.8 x 1.9 mm with enlarged
  plated lands. Confirm the supplied mechanical revision matches this layout.
- J1 body deliberately overhangs the bottom edge by about 8.6 mm. It has PCB
  reinforcement tabs. Confirm tooling, handling and soldering clearance; do not
  move it to eliminate the intended overhang.
- J12–J15 XT30UPB-M: pad 1 GND, pad 2 positive. Do not substitute wire-type XT30.
- J3 is a positive-to-positive **external series switch loop**, not a power
  output: neither terminal is ground. No bridge or jumper is to be fitted.
- Do not change capacitor voltage ratings, fuse family/rating, connector type,
  footprints or pinouts without updated engineering review.

## What preassembly includes and excludes

JLC can quote the board-mounted parts, subject to exact sourcing and DFM.
It does not install the robot's battery, servo cables, ESP32, IMU, camera,
independent Pi supply or chassis-mounted buck/relay harness through this PCB
placement file. `assembly/EXTERNAL_PURCHASES.csv` lists selected off-board items.
The current AUX buck choice is Pololu D24V10F5 / #2831, fixed 5 V; this remains
external and connects to J7, with its regulated output returning to J5.

## First-power conditions and outstanding validation

The user selected walking only, 150 mm 22 AWG servo cables and one 5 A fused
three-servo chain per leg. Connector capacity is assumed at least 5 A at the
user's request, without a manufacturer current-rating document. A 5 A slow-blow
fuse does not limit instantaneous current to 5 A.

The 20 A main, 1 A adapter/AUX and 5 A leg fuse choices are selected for this
prototype, not established as a complete fault-protection coordination study.
Main current-path/via heating, cable/contact temperature, voltage drop, startup
peaks and bus transients must be measured on the assembled unit before regular
use. The long main-fuse-to-switch copper route remains a particular thermal
review item. Do not interpret a successful factory DFM or assembly as proof of
electrical load capacity.

Inspect polarity and continuity unpowered, then commission with a suitable
current-limited supply. Verify 5 V at J5 before connecting the NodeMCU and verify
the exact MPU6050 breakout supply pinout. Never apply battery voltage to J5.
The Pi/camera use a separate supply; leave F7/J10/J11 unpopulated. Avoid joining
their supply-positive rails through USB or other interconnections.

## Sources and revision lock

`RELEASE-MANIFEST.json` records the exact PCB/schematic and fabrication hashes.
`DRC.txt`, `ERC.txt`, and the topology audit report the current clean CAD checks.
Historical PCB files and old ZIPs must not be mixed into this quote.

- JLC assembly options: https://jlcpcb.com/help/article/pcb-assembly-faqs
- JLC part sourcing: https://jlcpcb.com/help/article/how-to-use-my-own-parts-for-pcb-assembly-order
- CPL requirements: https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
- C2 catalog: https://jlcpcb.com/partdetail/CL21B104KBCNNNC/C1711
- J1 catalog: https://jlcpcb.com/partdetail/XT60PW-M/C98732
- J12–J15 catalog: https://jlcpcb.com/parts/2nd/Industrial_control_electrical/Power_connector__plug_connector_2944
- C1: https://www.nichicon.com/en-us/part/upw1e471mpd/8409/
- Bel fuses: https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf
- AUX regulator: https://www.pololu.com/product/2831/specs
