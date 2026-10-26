"""Non-interactive import and neutral-state validation."""
from pathlib import Path
import mujoco

model = mujoco.MjModel.from_xml_path(str(Path(__file__).with_name("robot_dog_v2.xml")))
data = mujoco.MjData(model)
data.qpos[2] = .12
mujoco.mj_forward(model, data)
assert model.nu == 12
assert model.njnt == 13  # free joint plus twelve driven hinges
assert all(model.actuator_forcerange[i, 1] <= 1.0 for i in range(model.nu))
print(f"Loaded {model.nu} actuators; mass={model.body_mass.sum():.3f} kg; warning count={data.warning.number.sum()}")
