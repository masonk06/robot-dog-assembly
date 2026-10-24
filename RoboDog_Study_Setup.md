# RoboDog: FRAME V2 and boot assembly

RoboDog.f3d is the native Fusion assembly. All source STLs are preserved in revision_sources; copies were converted into valid faceted BRep solids for analysis. The geometry is not remodeled, scaled, mirrored or smoothed. The supplied STEP servo was split into its original fixed-case and rotating-disc shapes. Each of the four identical leg geometries uses three servos. The frame is grounded and all 12 named revolute joints have their limits disabled.

The user corrected the initial 150 mm statement: there is no required 150 mm body dimension. FRAME V2 is retained at 170 x 180 x 50.10 mm overall, centered at X=15 mm. Front leg groups follow the source frame mount shift of +30 mm relative to the previous chassis. All leg groups are translated +1.2 mm in Z to align the case mounting axes to the frame holes at Z=23.5 and 48.0 mm. The source boot fits around the knee's original foot location and uses the same rigid transform as its knee link. Front remains -X.

## Native simulation drafts

The F3D archive contains Simulation Model 1 with Static Stress and Modal Frequencies study drafts. Neither was solved and no cloud solve was submitted.

Static Stress has a total downward force of 7.3549875 N on the centered frame floor face, representing 0.75 kg under standard gravity. This is a distributed-force stand-in for the payload weight, not a physical payload solid or full modal inertia. It does not add self-weight or the earlier 0.8 kg electronics assumption. Whether that old mass is additional is still unconfirmed. No supports or contact idealizations were guessed. Grounding the frame in the assembly is not an FEA support definition.

Modal Frequencies is a study shell. Payload inertia, supports, contacts and servo holding stiffness remain unset. The CAD stores a 750 g payload parameter and metadata, but a 0.75 kg modal point mass has not been applied because CG height and attachment footprint are unknown.

PETG assumptions are stored on printed components: hip-roll brackets 35% infill, other printed parts 20%. These are metadata, not calibrated mechanical properties. Infill percentage alone cannot determine stiffness, strength or mass. The solid CAD does not represent sparse infill. The studies must receive appropriate material and mass properties before solving. Default/inherited Fusion materials must not be interpreted as printed-PETG data.

All 12 joints are available for motion/range studies. RoboDogMotionCheck.py exercises each at +0.01 rad and returns to neutral; it sends no hardware commands. This is a kinematic test, not a rated range-of-motion sweep or collision guarantee. Actual hard limits remain unset as requested. A native motion-editor demonstration was exercised, but persistence of a motion curve was not verified and is not claimed.

## Fit findings

Visual assembly is consistent, including the four boots. Exact boolean checks against the fixed hip-roll case return about 0.038-0.040 mm3 near-coincident overlap per mount. This small residual has not been certified as clearance. It is retained for review rather than silently modifying the source frame. The boot and knee meshes overlap about 53.99 mm3 in native mating coordinates; confirm whether that is the intended physical press fit before accepting it. No boot or knee geometry was changed.

## Inputs required to finish meaningful studies

- Payload CG height, attachment footprint and whether 0.75 kg replaces the prior electronics estimate.
- Printed PETG material data, wall count, layer height, print orientation and infill pattern; revised frame and boot masses.
- Support/contact assumptions and servo joint holding stiffness for the intended stance.
- Desired per-joint motion ranges and measured physical hard stops.

No stress, safety factor, deflection, natural frequency, balance, or hardware-safe travel result is claimed by these draft setups. See RoboDog_study_setup.json and the geometry/motion verification files for recorded settings.
