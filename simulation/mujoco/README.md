# RoboDog MuJoCo walk preview

This model predates the latest Fusion housing export. Its intended attachment
hierarchy is described below, but its axes/placements have not been verified
against the latest assembly. See [project status](../../docs/STATUS.md).

The commands below run from this directory. From the repository root, prefix
each script with `simulation/mujoco/`. Install root `requirements.txt` first.

This is the current MuJoCo package for RoboDog. It uses the corrected CAD
attachment hierarchy:

- Knee-servo housing, `Knee Pitch V2`, and its glued boot are one rigid lower-leg assembly.
- The hip-pitch bracket is attached to the knee servo's rotating output disc.
- There is no sliding at screw-connected interfaces.

Run:

```powershell
python build_mujoco_v2.py
python check_model.py
python view_dog_walk.py --viewer --lift-mm 10
python simulate_dog_walk.py --viewer --seconds 16 --lift-mm 10
```

`view_dog_walk.py` is a slow four-beat, kinematic canine-walk preview. Its
swing timing is rear-left, then front-left 12% of a cycle later; both land
before rear-right and front-right repeat the same pattern. A small hip-roll
body sway shifts weight toward the planted side before each pair lifts. This
two-feet-up overlap is a visual/dynamics experiment, not a hardware gait yet.
It is used to validate the CAD connections, inverse-kinematics foot paths, and
gait sequencing before any new hardware commands.

This is not yet a dynamic walking validator: the base is fixed during the
preview. `simulate_dog_walk.py` is the next step: it releases the base and
advances gravity, foot contact, actuator torque limits, and the same gait. It
reports body height, tilt, and net forward progress.  It is deliberately
conservative: a stable body alone is not a transfer pass; the script also
requires at least 10 mm forward progress before calling the gait provisionally
transfer-ready.

The current 10 mm-lift gait stays upright but covers only a few millimetres in
two cycles, so it is **not** ready to command on the real dog. Contact/friction,
stance trajectory, measured joint offsets, cable limits, self-collision, and
hard stops still need validation before an untethered hardware test.
