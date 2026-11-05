# Revision C — new JLCPCB files and settings

The old revision B 2 oz order must not be changed to 1 oz without replacing its
files. Re-upload the **entire revision C Gerber, BOM and CPL set** and review
the new component locations. Board outline and mounting holes are unchanged.

Use these settings for the replacement prototype quote:
- FR-4, 2 layers, 1.6 mm, **1 oz finished outer copper on each side**.
- Green solder mask, white silkscreen, lead-free HASL if selecting basic
  low-cost finish options. No controlled impedance is required by this design.
- **Top-side-only component placement**. All 18 populated components are top-side.
  Bottom copper is still a required PCB layer; it does not mean bottom assembly.
- Request Economic PCBA if JLC permits the sourced components and through-hole
  parts in that service; otherwise obtain its Standard quote. Confirm actual
  service eligibility and cost in the quote rather than assuming a saving.
- By JLCPCB Manual Match; exact MPNs only, no substitutions without review.
- Confirm Parts Placement: Yes. Review updated J1/J3/F1/F5 positions against
  the revision C assembly drawing. Photo confirmation is useful for a first build.
- If JLC adds rails/fiducials, confirm their layout clears J1's deliberate
  8.6 mm bottom-edge overhang and the intended depaneling method. Request safe
  rail removal before shipping if desired. Temporary rails do not change the
  final 88.5 x 60 mm board outline.

Suggested Assembly Remark (under 500 characters):

> Rev C 1oz prototype, all populated parts TOP. Exact BOM parts only; no substitutions without approval. DNP F7/J10/J11. F1 holder only; no blade fuse. J1 pad1 GND, pad2 positive; 8.6mm bottom-edge overhang. J12-J15 pad1 GND, pad2 positive. Do not bridge J3. Ensure rails/tabs and depaneling tooling clear J1. Confirm sourcing, connector mechanical revision, panel layout and CPL alignment against Rev C drawings before production.

Attach the revision C top assembly PDF. Keep assembly notes in Assembly Remark,
not Bake Components Remark. Baking depends on actual component requirements.

Parts sourcing/placement approval remains necessary. This is a validation
prototype: direct current, voltage-drop, thermal and protection testing is
required on the assembled unit before regular powered use.
