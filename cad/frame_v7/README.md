# RoboDog V7 — wide-angle camera mount

Camera: official Raspberry Pi Camera Module 3 Wide, standard visible-light
version (not NoIR). 12 MP, autofocus, 120° diagonal field of view.
https://www.raspberrypi.com/products/camera-module-3/
Mechanical reference:
https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf

Use a Raspberry Pi camera cable Standard–Mini, 200 mm: 15-pin camera end,
22-pin Pi 5 end. Check whether it is included with the camera.

V6 reinforced chassis, hip-roll attachments, roofs, lower trays and Pi position
are retained. The Pi deck gains two 3.4 mm holes. A separate camera mast bolts
to its front edge with two M3 screws, washers and nuts (about 10–12 mm screws,
depending on washers/nuts). The front of this CAD is negative X.

Mount the camera with its lens facing forward, PCB rear plane X=-47 mm,
approximately Z=68–92 mm, centred in Y. Use four M2 screws, small washers,
4 mm insulating spacers between PCB rear and mast, and nuts. Select screw
length for the actual PCB, spacer, 3 mm mast, washers and nuts; approximately
12 mm. Slots are 21 mm apart and accommodate the camera's 12.5 mm vertical
hole pitch in either orientation. Tighten gently. The central opening leaves
rear ribbon access. Route ribbon through the existing deck cable slot with a
gentle bend, and secure slack away from servos. No lens hood obstructs the lens.

Frame footprint remains 177 × 179.8 mm. Print at 100%; use no brim extending
beyond a 180 mm bed. Every supplied part is individually below 180 × 180 mm.
STLs retain assembly coordinates: use slicer auto-arrange/drop to bed. Lay the
camera mast on its flat rear face (the +X side) for printing. PETG; use at least
4 perimeters around mount holes. Test fit the camera and ribbon before use.

Print Frame_V7, Pi5_Electronics_Deck, Power_Distribution_Sled, Waveshare_Sled,
Camera_Mast, and four Regulator_Spacers as needed. If V6 is already printed,
only the new deck and camera mast need replacement/printing.

RoboDog_V7_Complete.step contains printable assembly parts; Equipment_Layout
adds bounding envelopes, which are not printable parts. Camera envelope is
conservative, not a detailed vendor model. Static overlap checks do not verify
full joint sweeps, cable bends, lens occlusion, vibration or structural loads.
Power reservations and the bare-board Pi assumptions from V6 still apply.
