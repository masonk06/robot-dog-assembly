# RoboDog V2 MuJoCo package

This is the current `FRAME V2` assembly exported for simulation. It retains the supplied leg meshes and includes the four TPU-95 boot meshes as rigid parts of the corresponding lower legs. The boot-to-knee bond has no joint, so it cannot flex independently.

Run this once after moving the folder:

```powershell
python build_mujoco_v2.py
python check_model.py
python view_model.py
```

The model has a floating body, twelve position actuators, a 1 N·m nominal actuator cap, and conservative provisional joint limits. The mesh parts are visual-only. Four 3 mm spherical TPU-95 contact points approximate the boot soles, with soft contact settings and friction 1.0; printed geometry has no self-collision model yet.

The model has 1.923 kg total mass: the earlier 1.903 kg listed mass budget plus four measured 5 g TPU-95 boots. Each boot mass is placed at an approximate mesh center. This is ready for the first PPO exercise—learning to hold a neutral pose—but not yet a trustworthy hardware controller.
