"""Build a conservative MuJoCo model from the saved RoboDog V2 placements.

Visual meshes remain the original supplied STLs.  Each knee-servo housing,
Knee Pitch V2 part, and its glued boot form one rigid lower-foot assembly. The
hip-pitch bracket is mounted to the rotating knee-servo output circle, which
forms the knee hinge. Collision uses simple foot spheres; printed meshes are
visual-only until a deliberate collision mesh review is done.
"""
from pathlib import Path
import json
import shutil
import xml.etree.ElementTree as ET
import numpy as np
import mujoco

ROOT = Path(__file__).resolve().parents[2] / "cad"
OUT = Path(__file__).resolve().parent
ASSETS = OUT / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)
PLACEMENTS = json.loads((ROOT / "RoboDog_placements.json").read_text())
PART = {p["name"]: p for p in PLACEMENTS["parts"]}

def text(a): return " ".join(f"{float(x):.10g}" for x in a)
def add(parent, tag, **attrs): return ET.SubElement(parent, tag, {k: str(v) for k, v in attrs.items()})
def matrix(name): return np.array(PART[name]["transform"], dtype=float)
def quat(R):
    q = np.zeros(4); mujoco.mju_mat2Quat(q, R.reshape(-1)); return q

# Supplied source meshes.  STS3215 STL is reused from the earlier validated
# package because the original supplied servo is STEP, not STL.
source_dir = ROOT / "revision_sources"
old_assets = ROOT / "source"
needed = {
    "FRAME V2.stl": source_dir / "FRAME V2.stl",
    "Part Studio 1 - Hip Roll V3.stl": source_dir / "Part Studio 1 - Hip Roll V3.stl",
    "Part Studio 1 - Hip Pitch L.stl": source_dir / "Part Studio 1 - Hip Pitch L.stl",
    "Part Studio 1 - Hip Pitch R.stl": source_dir / "Part Studio 1 - Hip Pitch R.stl",
    "Part Studio 1 - Knee Pitch v2.stl": source_dir / "Part Studio 1 - Knee Pitch v2.stl",
    "boots.stl": source_dir / "boots.stl",
    "STS3215.stl": old_assets / "STS3215.stl",
}
for name, src in needed.items():
    if not src.exists(): raise FileNotFoundError(src)
    shutil.copy2(src, ASSETS / name)

root = ET.Element("mujoco", model="RoboDog V2 - conservative RL model")
add(root, "compiler", angle="radian", meshdir="assets", inertiafromgeom="false")
add(root, "option", timestep=".002", integrator="implicitfast", gravity="0 0 -9.80665")
add(root, "default"); asset = add(root, "asset")
mesh_id = {}
for n in needed:
    mesh_id[n] = "mesh_" + str(len(mesh_id))
    add(asset, "mesh", name=mesh_id[n], file=n, scale=".001 .001 .001")

world = add(root, "worldbody")
add(world, "light", pos="0 0 1", dir="0 0 -1")
add(world, "geom", name="floor", type="plane", size="2 2 .05", rgba=".25 .3 .35 1", friction=".8 .01 .001", contype="1", conaffinity="2")
base = add(world, "body", name="base", pos="0 0 .12")
add(base, "freejoint")
# User's mass budget totals 1.903 kg. Boots have no measured mass, so their
# geometry is shown but no unmeasured inertial mass is invented here.
add(base, "inertial", mass="1.282", pos="0 0 .025", diaginertia=".00415 .00496 .00774")
add(base, "geom", name="body_contact_proxy", type="box", pos=".015 0 .025", size=".085 .09 .025", rgba="0 0 0 0", group="3", contype="2", conaffinity="1")

def visual(body, name, origin):
    p = PART[name]; T = matrix(name)
    source = p.get("mesh_source") or p["source"]
    if source == "STS3215.step": source = "STS3215.stl"
    add(body, "geom", name=name, type="mesh", mesh=mesh_id[source],
        pos=text(T[:3, 3] / 1000 - origin), quat=text(quat(T[:3, :3])),
        rgba=".16 .18 .22 1" if "servo" in name else ".62 .66 .72 1",
        contype="0", conaffinity="0", group="1")

visual(base, "frame", np.zeros(3))
actuators = add(root, "actuator")
legs = ["front_left", "front_right", "rear_left", "rear_right"]
for leg in legs:
    # Joint origins and axes come directly from the placed servo shaft axes.
    R = np.array(PART[f"{leg}_servo_hip_roll"]["axis_point"], dtype=float) / 1000
    H = np.array(PART[f"{leg}_servo_hip_pitch"]["axis_point"], dtype=float) / 1000
    K = np.array(PART[f"{leg}_servo_knee_pitch"]["axis_point"], dtype=float) / 1000
    if leg.startswith("front_"):
        # The front placements' recorded axis point is 30 mm inward from the
        # knee-servo output disc.  Shift only the front hinge origin so its
        # lower assembly rotates at the same disc-local origin as the rear.
        K += np.array([.03, 0, 0])
    roll = add(base, "body", name=f"{leg}_roll_link", pos=text(R))
    add(roll, "joint", name=f"{leg}_hip_roll", type="hinge", axis="1 0 0", range="-.5 .5", damping=".025", armature=".00002")
    add(roll, "inertial", mass=".066", pos=text(H - R), diaginertia=".0000176 .0000176 .0000176")
    visual(base, f"{leg}_servo_hip_roll", np.zeros(3))
    visual(roll, f"{leg}_hip_roll", R)
    visual(roll, f"{leg}_servo_hip_pitch", R)

    upper = add(roll, "body", name=f"{leg}_upper_link", pos=text(H - R))
    add(upper, "joint", name=f"{leg}_hip_pitch", type="hinge", axis="0 -1 0", range="-1.2 1.2", damping=".025", armature=".00002")
    add(upper, "inertial", mass=".073625", pos=text((K-H)*.45), diaginertia=".0000298 .0000298 .00000767")
    for n in ("hip_pitch_L", "hip_pitch_R"):
        visual(upper, f"{leg}_{n}", H)

    lower = add(upper, "body", name=f"{leg}_lower_link", pos=text(K - H))
    add(lower, "joint", name=f"{leg}_knee_pitch", type="hinge", axis="0 -1 0", range="-1.5 1.5", damping=".025", armature=".00002")
    add(lower, "inertial", mass=".015625", pos="-.025 0 -.04", diaginertia=".0000102 .0000102 .00000163")
    visual(lower, f"{leg}_servo_knee_pitch", K)
    visual(lower, f"{leg}_knee_v2", K)
    visual(lower, f"{leg}_boot", K)  # glued to Knee Pitch V2: no relative joint
    # Measured TPU-95 boot mass: 5 g each. This is a fixed child, so the
    # adhesive bond cannot introduce another degree of freedom.
    boot_mass = add(lower, "body", name=f"{leg}_boot_mass", pos="-.0131 0 -.0656")
    add(boot_mass, "inertial", mass=".005", pos="0 0 0", diaginertia=".000001 .000001 .000001")
    # Conservative 3 mm TPU-95 sole proxy. solref/solimp make floor contact
    # compliant; they are a starting approximation, not a measured material model.
    add(lower, "geom", name=f"{leg}_foot_contact_proxy", type="sphere", pos="-.045 0 -.07", size=".003", rgba="0 0 0 0", group="3", contype="2", conaffinity="1", friction="1.0 .01 .001", solref=".02 1", solimp=".9 .95 .001")
    add(lower, "site", name=f"{leg}_foot", pos="-.045 0 -.07", size=".003")
    for joint in ("hip_roll", "hip_pitch", "knee_pitch"):
        name = f"{leg}_{joint}"
        add(actuators, "position", name=name, joint=name, kp="12", kv=".15", forcerange="-1 1", forcelimited="true")

ET.indent(root)
xml_path = OUT / "robot_dog_v2.xml"
ET.ElementTree(root).write(xml_path, encoding="unicode")
model = mujoco.MjModel.from_xml_path(str(xml_path))
data = mujoco.MjData(model); mujoco.mj_forward(model, data)
summary = {
    "model": xml_path.name, "mujoco_version": mujoco.__version__, "actuators": int(model.nu),
    "joints": 12, "total_model_mass_kg": float(model.body_mass.sum()),
    "frame": "FRAME V2.stl", "boots": "TPU 95, glued beneath Knee Pitch V2; knee-servo housing, Knee Pitch V2, and boot form each rigid lower-foot assembly",
    "actuator_limit_Nm": 1.0,
    "joint_limits_rad": {"hip_roll": [-.5,.5], "hip_pitch": [-1.2,1.2], "knee_pitch": [-1.5,1.5]},
    "known_limitations": ["Knee-servo housing, Knee Pitch V2, and its glued boot are rigid lower-foot parts; the hip-pitch bracket is attached to the rotating knee-servo output circle.", "Each TPU-95 boot is a measured 5 g lumped mass at its mesh-center approximation.", "Foot contact uses 3 mm TPU-95 spherical sole proxies with provisional softness and friction.", "Mesh geometry is visual-only; no printed-part self-collision."],
}
(OUT / "import_validation.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
