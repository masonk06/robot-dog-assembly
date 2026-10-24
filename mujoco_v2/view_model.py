"""Open the RoboDog V2 model in MuJoCo's interactive viewer."""
from pathlib import Path
import mujoco
import mujoco.viewer

model = mujoco.MjModel.from_xml_path(str(Path(__file__).with_name("robot_dog_v2.xml")))
data = mujoco.MjData(model)
# Start the base above ground; the user can reset and inspect the neutral pose.
data.qpos[2] = 0.12
mujoco.mj_forward(model, data)
with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
