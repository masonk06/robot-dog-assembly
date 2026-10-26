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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hardware"))
import rear_left_ik_trot as ik  # noqa: E402


MODEL_PATH = Path(__file__).with_name("robot_dog_v2.xml")
# Lateral-pair walk requested for RoboDog: the rear foot leads, then the front
# foot on that same side lifts shortly afterward.  Both return to the ground
# before the pair on the opposite side starts.
LEGS = ("rear_left", "front_left", "rear_right", "front_right")
# The front foot trails its matching rear foot by 12% of the cycle.  With a
# 20% swing, same-side legs overlap in the air for 8% of a cycle, then all four
# feet are down before the other side begins.
SWING_START = {"rear_left": 0.00, "front_left": 0.12, "rear_right": 0.50, "front_right": 0.62}
SWING_FRACTION = 0.20
CYCLE_SECONDS = 10.0
UPDATE_SECONDS = 0.01
STRIDE_M = 0.015
ROLL_SWAY_RAD = 0.04


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


def leg_phase(leg, phase):
    """Leg-local phase, with zero at that foot's lift-off."""
    return (phase - SWING_START[leg]) % 1.0


def hip_roll_target(leg, phase):
    """Shift the body toward the three-foot support triangle during swing.

    A slow canine walk visibly sways toward the planted feet before each paw
    lifts.  With the model's shared hip-roll axis, a negative command lowers
    the right support feet and a positive command lowers the left ones.
    """
    local_phase = leg_phase(leg, phase)
    if local_phase >= SWING_FRACTION:
        return 0.0
    swing_side = -1.0 if leg.endswith("left") else 1.0
    return swing_side * ROLL_SWAY_RAD * math.sin(math.pi * local_phase / SWING_FRACTION)


def set_pose(model, data, phase):
    data.qpos[:] = 0
    # Fixed base: this preview isolates leg kinematics rather than claiming
    # that the provisional contact/mass model can support dynamic walking.
    data.qpos[:7] = (0, 0, 0.12, 1, 0, 0, 0)
    for leg in LEGS:
        x, z = walk_foot_target(leg_phase(leg, phase))
        hip, knee = ik.inverse_kinematics(x, z)
        data.qpos[joint_address(model, f"{leg}_hip_roll")] = hip_roll_target(leg, phase)
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
    print("Lateral-pair walk: rear-left lifts, front-left follows after 12% of the cycle;")
    print("both land before rear-right and front-right repeat the same pattern.")
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
    parser.add_argument("--stride-mm", type=float, default=15.0, help="fore-aft foot stroke in millimetres (default: 15)")
    args = parser.parse_args()
    if not 0 < args.lift_mm <= 20 or not 5 <= args.stride_mm <= 40:
        raise SystemExit("--lift-mm must be 0..20 and --stride-mm must be 5..40")
    ik.SWING_HEIGHT_M = args.lift_mm / 1000
    global STRIDE_M
    STRIDE_M = args.stride_mm / 1000
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    validate(model, data)
    if args.viewer:
        show(model, data)


if __name__ == "__main__":
    main()
