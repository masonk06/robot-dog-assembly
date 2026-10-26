# Mechanical design

| Assembly | Meaning |
| --- | --- |
| `RoboDog - Knee Housing Connections.f3d` | Latest export, 2026-10-25: all knee housings grouped with knee-pitch parts and boots; output discs grouped with upper links |
| `Recovered Fusion/RoboDog - FRAME V2 + boots.f3d` | Recovered 2026-10-22 assembly before housing edits |
| `RoboDog.f3d` | Earlier snapshot; does not include the latest edits |
| `RoboDog_geometry_backup.f3d` | Historical geometry backup |

The latest export is a work in progress: the front-left motion test showed the housing following the foot, but the pivot remained near the hip. All knee pivots and motion ranges require review.

## Assets

- `source/`: originally supplied STL meshes.
- `revision_sources/`: revised frame, boot, and split servo geometry.
- `solid_sources/`: converted STEP parts.
- `positioned_parts/` and `robot_dog_layout.*`: earlier conceptual layouts.
- `front_rear_leg_variants/`: installation references, not new printable designs.
- `RoboDog_placements.json`: earlier saved transforms used by the simulator.
- `placements.json`: conceptual assumptions, not measured mechanical truth.
- `robot_dog_meshes_for_hpc.zip`: original HPC transfer snapshot.

Fusion scripts run inside Fusion's Python environment. Conversion tools require OpenCascade Python bindings (`OCP`), separate from simulator dependencies. `RoboDog_original_import_script.py` is archival and retains paths to an older workspace.

JSON reports, logs, and images describe the revisions that generated them; they do not certify the latest assembly.
