# SUPERSEDED — DO NOT ORDER THIS PACKAGE

The current PCB has a larger J3 terminal and updated routing. This historical
package does not represent it. Its ZIP has a `.SUPERSEDED` suffix. See
`../HARNESS-SELECTION.md`. No updated production release has been approved.

The historical package was generated for a bare, unpopulated PCB.
The ZIP contains exactly seven Gerber layers and two Excellon drill files.
It does not contain a BOM or placement file and is not an assembly package.

Order settings:
- FR-4, two copper layers.
- 1.6 mm board thickness.
- 2 oz finished copper on BOTH sides. Select this explicitly in the order form;
  Gerber geometry alone does not specify copper weight.
- Nominal board size 88.5 x 60.0 mm. Check this in JLCPCB's upload preview.
- Front and rear solder mask, front/rear silkscreen as included.
- No stencil required for a bare-board order; fuse soldering method is a separate
  assembly choice. This package provides no assembly or powered-use approval.

The source revision passed 0 DRC violations, 0 unconnected pads and 0 schematic
parity issues immediately before export. Its schematic also passed ERC. All
four leg outputs have independent fused positives and common ground returns.
New XT30 leg connector pad 1 is GND and pad 2 is fused positive.

F8-F11 are provisional 5 A slow-blow parts, not approved for sustained leg stall.
F1's rating and protective coordination are unresolved. Current/thermal, harness,
switch, physical connector/polarity and enclosure fit checks remain open. Review
the parent README before assembly. Do not connect the LiPo as a first power test;
initial electrical validation needs a suitably current-limited bench supply.

Prototype fabrication may expose a need for another PCB revision. Do not order
production quantities or treat a successful factory DFM preview as validation
of electrical safety or power capacity.

Do not use the old manufacturing candidate retained with a DO_NOT_ORDER suffix.
