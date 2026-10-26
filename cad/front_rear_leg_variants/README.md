# Front and rear leg installation references — RoboDog V2

## Conclusion

There are **no separate front and rear printable leg parts**. `FRAME V2` uses the same five supplied printed meshes for every leg:

| Printed part | Front pair | Rear pair | Total |
| --- | ---: | ---: | ---: |
| Hip Roll V3 | 2 | 2 | 4 |
| Hip Pitch L | 2 | 2 | 4 |
| Hip Pitch R | 2 | 2 | 4 |
| Knee Pitch v2 | 2 | 2 | 4 |
| TPU 95 boot | 2 | 2 | 4 |

The `Front_...` and `Rear_...` STEP/STL files are **installation-orientation reference assemblies**, not new printable variants. They use the unmodified source meshes and are normalized at the hip-roll servo output axis. They include printed geometry only; the spaces between parts are occupied by the STS3215 servos. Do not print these compound STL files as individual parts.

## Install orientation

Coordinate convention for the saved assembly: front is **−X**; left is **−Y**. Install the front pair at the two −X frame stations and the rear pair at the two +X frame stations. Use the corresponding reference assembly for the particular end of the chassis.

The rear installation is **not** produced by simply rotating the entire front printed-leg group 180°. The rear hip-roll printed part is rotated 180° about global Z, while the hip-pitch pair, knee, and boot use the rear placement arrangement. This is why the two reference assemblies are provided. No source STL has been mirrored, scaled, or otherwise edited.

The references were generated from `RoboDog_placements.json`, verified against `FRAME V2.stl`, and preserve the original print-source hashes listed in `orientation_reference_manifest.json`.

## Knee hardware

Each knee uses 8 M3 disc screws (four per disc side) plus 6 M2 × 6 mm side screws (three per side). See `../Knee_Fastener_Spec.md` for the fastener count.
