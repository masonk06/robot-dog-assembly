"""Run a contact-and-gravity screening simulation for the RoboDog walk gait.

Unlike view_dog_walk.py, this advances MuJoCo dynamics with gravity, the free
base, foot-contact proxies, and the position actuators.  It is an engineering
screen, not a hardware-ready controller: a failed run identifies that the
contact, mass, torque, or stabilization model needs refinement before transfer.
"""
import argparse
import math
import sys
import time
from pathlib import Path

import mujoco

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hardware"))
import rear_left_ik_trot as ik  # noqa: E402
import view_dog_walk as gait  # noqa: E402
from view_dog_walk import (  # noqa: E402
    LEGS,
    CYCLE_SECONDS,
    hip_roll_target,
    leg_phase,
    walk_foot_target,
)


MODEL_PATH = Path(__file__).with_name("robot_dog_v2.xml")


def object_id(model, kind, name):
    value = mujoco.mj_name2id(model, kind, name)
    if value < 0:
        raise RuntimeError(f"Missing MuJoCo object: {name}")
    return value


def leg_targets(phase):
    values = {}
    for leg in LEGS:
        x, z = walk_foot_target(leg_phase(leg, phase))
        values[f"{leg}_hip_roll"] = hip_roll_target(leg, phase)
        values[f"{leg}_hip_pitch"], values[f"{leg}_knee_pitch"] = ik.inverse_kinematics(x, z)
    return values


def initialise(model, data, actuator_ids, joint_addresses):
    data.qpos[:] = 0
    data.qpos[:7] = (0, 0, 0.12, 1, 0, 0, 0)
    targets = leg_targets(0.0)
    for joint, value in targets.items():
        data.qpos[joint_addresses[joint]] = value
        data.ctrl[actuator_ids[joint]] = value
    mujoco.mj_forward(model, data)


def run(model, data, duration, viewer=None):
    actuator_ids = {name: object_id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name) for leg in LEGS for name in (f"{leg}_hip_roll", f"{leg}_hip_pitch", f"{leg}_knee_pitch")}
    joint_addresses = {name: model.jnt_qposadr[object_id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in actuator_ids}
    base_id = object_id(model, mujoco.mjtObj.mjOBJ_BODY, "base")
    initialise(model, data, actuator_ids, joint_addresses)
    start_xy = data.xpos[base_id, :2].copy()
    min_height = math.inf
    max_tilt = 0.0
    wall_start = time.perf_counter()
    while data.time < duration:
        phase = (data.time / CYCLE_SECONDS) % 1.0
        for joint, value in leg_targets(phase).items():
            data.ctrl[actuator_ids[joint]] = value
        mujoco.mj_step(model, data)
        base_rotation = data.xmat[base_id].reshape(3, 3)
        tilt = math.acos(max(-1.0, min(1.0, base_rotation[2, 2])))
        min_height = min(min_height, float(data.xpos[base_id][2]))
        max_tilt = max(max_tilt, tilt)
        if viewer is not None:
            viewer.sync()
            elapsed = time.perf_counter() - wall_start
            if data.time > elapsed:
                time.sleep(data.time - elapsed)
        if not math.isfinite(min_height) or min_height < 0.03:
            break
    displacement_xy = data.xpos[base_id, :2] - start_xy
    return data, min_height, math.degrees(max_tilt), displacement_xy


def report(data, min_height, max_tilt, displacement_xy):
    stable = data.time >= 3.0 and min_height >= 0.06 and max_tilt <= 20.0
    # In the CAD coordinate frame the front feet have negative X positions,
    # so negative world-X is forward progress.
    forward_mm = -float(displacement_xy[0]) * 1000
    lateral_mm = float(displacement_xy[1]) * 1000
    transfers = stable and forward_mm >= 10.0
    print(f"Dynamic walk simulated: {data.time:.2f} s")
    print(f"Minimum base height: {min_height * 1000:.1f} mm")
    print(f"Maximum base tilt: {max_tilt:.1f} deg")
    print(f"Net forward progress: {forward_mm:+.1f} mm (lateral {lateral_mm:+.1f} mm)")
    if transfers:
        print("PASS: stable walk with provisional forward progress")
    elif stable:
        print("STABLE BUT NOT TRANSFER-READY: tune the gait for forward traction before hardware use")
    else:
        print("NOT TRANSFER-READY: refine dynamics/controller before hardware use")
    return transfers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=16.0, help="simulation duration (default: 16; two walk cycles)")
    parser.add_argument("--lift-mm", type=float, default=10.0, help="foot lift in millimetres (default: 10)")
    parser.add_argument("--stride-mm", type=float, default=15.0, help="fore-aft foot stroke in millimetres (default: 15)")
    parser.add_argument("--viewer", action="store_true", help="watch the dynamic contact simulation")
    args = parser.parse_args()
    if not 0 < args.seconds <= 20 or not 0 < args.lift_mm <= 20 or not 5 <= args.stride_mm <= 40:
        raise SystemExit("--seconds must be 0..20, --lift-mm must be 0..20, and --stride-mm must be 5..40")
    ik.SWING_HEIGHT_M = args.lift_mm / 1000
    gait.STRIDE_M = args.stride_mm / 1000
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    if args.viewer:
        from mujoco import viewer as mujoco_viewer
        # The passive viewer must receive the *same* MjData that mj_step
        # advances.  Giving it a second data object leaves the visible robot
        # frozen even though the background simulation is running.
        data = mujoco.MjData(model)
        with mujoco_viewer.launch_passive(model, data) as viewer:
            data, min_height, max_tilt, displacement_xy = run(model, data, args.seconds, viewer)
            report(data, min_height, max_tilt, displacement_xy)
    else:
        data = mujoco.MjData(model)
        data, min_height, max_tilt, displacement_xy = run(model, data, args.seconds)
        report(data, min_height, max_tilt, displacement_xy)


if __name__ == "__main__":
    main()
