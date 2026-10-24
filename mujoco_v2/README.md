# RoboDog MuJoCo walk preview

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
```

`view_dog_walk.py` is a slow four-beat, kinematic dog-walk preview. Its swing
order is front-right, rear-left, front-left, rear-right. It is used to validate
the CAD connections, inverse-kinematics foot paths, and gait sequencing before
any new hardware commands.

This is not yet a dynamic walking validator: the base is fixed during the
preview, and the contact/friction, inertia, cable behavior, self-collision, and
measured hard stops still need validation before force-based walking simulation
or untethered hardware use.
