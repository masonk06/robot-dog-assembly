# Luca revision C — 1 oz validation prototype / PCBA quote

**This replaces the old revision B files for the current cost-reduction request.**
Do not simply change the old upload to 1 oz. Parts moved and copper routing is
different. Replace Gerbers, BOM and CPL together.

## Upload files

1. PCB: `Luca_RevC_1oz_FAB_PROTOTYPE.zip` (seven Gerber layers and two Excellon
   drill files). This ZIP alone is not an assembly order.
2. Assembly BOM: `assembly/BOM_FULL_QUOTE.csv`.
3. Placement: `assembly/CPL_FULL_QUOTE.csv` — **all 18 rows are Top**.
4. Assembly reference: `assembly/ASSEMBLY_TOP.pdf`. Bottom PDF is a reference
   showing unpopulated footprints/holes, not an instruction for bottom placement.

Select **1 oz copper on both faces**, 1.6 mm FR-4 and top-side-only assembly.
Outline is 88.5 x 60 mm. Request Economic PCBA if the sourced/through-hole parts
are eligible; otherwise obtain JLC's Standard quote. Current eligibility and
total price must be confirmed by JLC. Green mask/white silk/lead-free HASL are
the intended basic finish options. Copper weight is not encoded by Gerbers.

## What changed

The circuit and parts are retained, including 5 A per-leg fuses and the external
J3 switch loop. F1 moved near J1; J3 moved near the leg feeds. Shared raw/fused
and servo conductors are 6 mm wide on both copper faces. Ground pours cover both
faces. F5 is now on top, not bottom. Unused Pi footprints remain DNP.

## Parts and polarity review

- Review `assembly/SOURCING_STATUS.csv`. Exact Bel fuses, Keystone holder and
  Phoenix terminals require sourcing/consignment confirmation. Empty C-codes
  are intentional; do not silently omit unmatched parts or accept substitutes.
- F7, J10, J11: **DO NOT POPULATE**. H1-H4 are mounting holes.
- F1: **Keystone 3568 holder only**. The separate selected 20 A MINI blade fuse
  is listed in `EXTERNAL_PURCHASES.csv`, not CPL. Leave it out for shipping and
  unpowered inspection, or quote it separately as a loose insertion item.
- J1: pad 1 GND; pad 2 battery positive. It is AMASS XT60PW-M PCB-mount,
  rotated 180 degrees. Positive is physically left in the top drawing.
  Supplier C98732 drawing is AMASS 2025V0 XT60PW-M30.G.Y.T: 2.9 mm holes,
  0.8 x 1.9 mm reinforcement slots and enlarged annular lands.
- J1 body overhangs the bottom board edge about 8.6 mm. Confirm factory rails,
  tabs, handling fixtures and depaneling tooling clear it. Do not reposition it.
- J12-J15: XT30UPB-M PCB-mount, pad 1 GND, pad 2 fused positive.
- C1: positive lead in pad 1. Fuses and C2 are nonpolar.
- J3: two positive switch-loop ends, **neither ground**. No jumper is fitted.

Review JLC's placement/model preview against `CENTROID_DATUM_REVIEW.csv`, the
native KiCad-origin reference and the assembly drawing before production.
Enable Confirm Parts Placement. Sourcing and factory DFM approval are not yet
performed by this package. No paid order is authorized by these files alone.

## External integration and validation

The external AUX buck is Pololu D24V10F5 / #2831, fixed 5 V, connected through
J7, with output returning to J5. Verify 5 V before connecting the NodeMCU; use
the actual MPU6050 breakout's verified supply/interface pinout. The relay,
toggle, external wiring, ESP32, IMU, servo leads, battery and independent Pi
supply are not PCB-placement items. Do not join independent supply-positive
rails through USB or other wiring. F7/J10/J11 remain absent.

The user retains three daisy-chained servos per leg, 150 mm 22 AWG leads and an
assumed 5 A connector rating. This is not a verified manufacturer rating. The
20 A main/1 A adapter-AUX/5 A leg fuses remain prototype selections with fault
coordination and measured thermal/load validation open. A 5 A slow-blow fuse
does not clamp current at 5 A. Initial power-up must use suitable current-limited
equipment after unpowered polarity/continuity inspection. Do not short the LiPo.

## Revision lock and references

`RELEASE-MANIFEST.json` binds source and exported file hashes. `DRC.txt`,
`ERC.txt` and `topology-and-ground-audit.json` record CAD checks. The resistance
and sampled ground-corridor models do not establish a temperature/current rating.
See `FUSE-AND-COPPER-REVIEW.md`, `README.md` and the source CAD for details.

- JLC assembly options: https://jlcpcb.com/capabilities/pcb-assembly-capabilities
- Parts sourcing: https://jlcpcb.com/help/article/how-to-use-my-own-parts-for-pcb-assembly-order
- CPL requirements: https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
- Fuse data: https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-CP-0680H-series.pdf
