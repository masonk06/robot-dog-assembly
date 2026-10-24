"""Preview a slow four-beat dog walk with the current RoboDog MuJoCo model.

This is a kinematic gait review: it holds the floating base fixed and drives
the CAD-derived hip/knee angles directly.  It is intended to validate the
attachment hierarchy, foot paths, and walking sequence before a future
ground-contact dynamics model or real-servo transfer.
"""
import argparse
import math
import sys
import time
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).parent.parent))
import rear_left_ik_trot as ik  # noqa: E402


MODEL_PATH = Path(__file__).with_name("robot_dog_v2.xml")
LEGS = ("front_right", "rear_left", "front_left", "rear_right")
# A static walk has one swing leg at a time rather than diagonal pairs.
PHASE_OFFSET = {leg: index / 4 for index, leg in enumerate(LEGS)}
SWING_FRACTION = 0.25
CYCLE_SECONDS = 8.0
UPDATE_SECONDS = 0.01
STRIDE_M = 0.015


def joint_address(model, name):
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if joint_id < 0:
        raise RuntimeError(f"Missing joint: {name}")
    return model.jnt_qposadr[joint_id]


def walk_foot_target(phase):
    """Forward/up swing followed by a slower level stance sweep."""
    x0, z0 = ik.NEUTRAL_FOOT
    if phase < SWING_FRACTION:
        progress = phase / SWING_FRACTION
        return (
            x0 - STRIDE_M * ik.smoothstep(progress),
            z0 + ik.SWING_HEIGHT_M * math.sin(math.pi * progress),
        )
    progress = (phase - SWING_FRACTION) / (1 - SWING_FRACTION)
    return x0 - STRIDE_M + STRIDE_M * ik.smoothstep(progress), z0


def set_pose(model, data, phase):
    data.qpos[:] = 0
    # Fixed base: this preview isolates leg kinematics rather than claiming
    # that the provisional contact/mass model can support dynamic walking.
    data.qpos[:7] = (0, 0, 0.12, 1, 0, 0, 0)
    for leg in LEGS:
        x, z = walk_foot_target((phase + PHASE_OFFSET[leg]) % 1.0)
        hip, knee = ik.inverse_kinematics(x, z)
        data.qpos[joint_address(model, f"{leg}_hip_roll")] = 0
        data.qpos[joint_address(model, f"{leg}_hip_pitch")] = hip
        data.qpos[joint_address(model, f"{leg}_knee_pitch")] = knee
    mujoco.mj_forward(model, data)


def validate(model, data):
    set_pose(model, data, 0.0)
    heights = {}
    for leg in LEGS:
        site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{leg}_foot")
        heights[leg] = float(data.site_xpos[site][2])
    swing_leg = LEGS[0]
    set_pose(model, data, 0.125)
    site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{swing_leg}_foot")
    lift = float(data.site_xpos[site][2] - heights[swing_leg])
    if lift <= 0:
        raise RuntimeError("Walk preview did not lift the first swing foot")
    print(f"Four-beat walk: {', '.join(LEGS)} swing in that order.")
    print(f"First swing foot ({swing_leg}) lift at mid-swing: {lift * 1000:.1f} mm.")


def show(model, data):
    import mujoco.viewer

    with mujoco.viewer.launch_passive(model, data) as viewer:
        start = time.perf_counter()
        while viewer.is_running():
            phase = ((time.perf_counter() - start) / CYCLE_SECONDS) % 1.0
            set_pose(model, data, phase)
            viewer.sync()
            time.sleep(UPDATE_SECONDS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--viewer", action="store_true", help="open the looping MuJoCo gait preview")
    parser.add_argument("--lift-mm", type=float, default=10.0, help="swing lift in millimetres (default: 10)")
    args = parser.parse_args()
    if not 0 < args.lift_mm <= 20:
        raise SystemExit("--lift-mm must be between 0 and 20")
    ik.SWING_HEIGHT_M = args.lift_mm / 1000
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    validate(model, data)
    if args.viewer:
        show(model, data)


if __name__ == "__main__":
    main()
