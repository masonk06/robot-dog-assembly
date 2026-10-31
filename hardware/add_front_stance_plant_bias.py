"""Add a small, stance-only downward foot bias using the MuJoCo leg Jacobian.

This is an offline replay transform. It does not change PPO weights and does
not claim to sense real ground contact. The adjustment keeps the simulated
front foot's fore-aft coordinate fixed while asking for a small lower Z target.
"""
import argparse
import csv
import json
import math
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
CYCLE_SECONDS = 3.0
SWING_FRACTION = 0.20
LEGS = {
    "front_left": {"offset": .25, "ids": (4, 5, 6)},
    "front_right": {"offset": .75, "ids": (1, 2, 3)},
}
JOINT_NAMES = (
    "front_left_hip_roll", "front_left_hip_pitch", "front_left_knee_pitch",
    "front_right_hip_roll", "front_right_hip_pitch", "front_right_knee_pitch",
    "rear_left_hip_roll", "rear_left_hip_pitch", "rear_left_knee_pitch",
    "rear_right_hip_roll", "rear_right_hip_pitch", "rear_right_knee_pitch",
)


def smoothstep(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--depth-mm", type=float, default=1.0)
    parser.add_argument("--ramp-seconds", type=float, default=.10)
    parser.add_argument("--startup-ramp-seconds", type=float, default=.50,
                        help="Simulated seconds to introduce the plant bias from the unchanged start pose")
    parser.add_argument("--model", type=Path, default=ROOT / "simulation/mujoco/robot_dog_v2.xml")
    parser.add_argument("--limits", type=Path, default=ROOT / "hardware/calibrations/current-frame-limits-20261029.json")
    parser.add_argument("--max-front-tick-step", type=int, default=18)
    args = parser.parse_args()
    if not 0 < args.depth_mm <= 2:
        parser.error("depth-mm must be in (0, 2] for this first-contact experiment")
    if not 0 < args.ramp_seconds < 1:
        parser.error("ramp-seconds must be in (0, 1)")
    if not 0 < args.startup_ramp_seconds <= 1:
        parser.error("startup-ramp-seconds must be in (0, 1]")
    if not 0 < args.max_front_tick_step <= 20:
        parser.error("max-front-tick-step must be in [1, 20]")

    with args.input.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if fields is None or not rows or any(str(sid) not in fields for sid in range(1, 13)):
        raise ValueError("Expected a non-empty 12-servo replay CSV")

    zeros = json.loads((ROOT / "hardware/calibrations/zero-points-current.json").read_text())["joints"]
    directions = json.loads((ROOT / "hardware/calibrations/manual-physical-directions-20261028.json").read_text())["joints"]
    limits = json.loads(args.limits.read_text())["joints"]
    by_id = {joint["id"]: (joint["minimum_ticks"] + 10, joint["maximum_ticks"] - 10)
             for joint in limits.values()}
    by_name = {name: (zeros[name]["id"], zeros[name]["neutral_ticks"],
                      directions[name]["model_to_encoder_sign"])
               for name in JOINT_NAMES}

    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)
    qpos_index = {name: model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)]
                  for name in JOINT_NAMES}
    dof_index = {name: model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)]
                 for name in JOINT_NAMES}
    scale = 4096.0 / (2.0 * math.pi)
    ramp_fraction = args.ramp_seconds / CYCLE_SECONDS
    changed = {leg: 0 for leg in LEGS}

    for row in rows:
        for name in JOINT_NAMES:
            servo_id, neutral, sign = by_name[name]
            data.qpos[qpos_index[name]] = (int(row[str(servo_id)]) - neutral) / (sign * scale)
        mujoco.mj_forward(model, data)
        phase = (float(row["time_seconds"]) / CYCLE_SECONDS) % 1.0
        for leg, spec in LEGS.items():
            local = (phase - spec["offset"]) % 1.0
            if local < SWING_FRACTION:
                continue
            # Smoothly add the bias after touchdown and remove it before swing.
            entered_stance = (local - SWING_FRACTION) / ramp_fraction
            leaving_stance = (1.0 - local) / ramp_fraction
            startup = smoothstep(float(row["time_seconds"]) / args.startup_ramp_seconds)
            envelope = smoothstep(min(entered_stance, leaving_stance)) * startup
            if envelope <= 0:
                continue
            site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{leg}_foot")
            jacobian = np.zeros((3, model.nv))
            mujoco.mj_jacSite(model, data, jacobian, None, site_id)
            hip, knee = f"{leg}_hip_pitch", f"{leg}_knee_pitch"
            columns = (dof_index[hip], dof_index[knee])
            xz = jacobian[np.ix_((0, 2), columns)]
            try:
                delta = np.linalg.solve(xz, np.array([0.0, -args.depth_mm / 1000.0 * envelope]))
            except np.linalg.LinAlgError as error:
                raise RuntimeError(f"{leg}: singular foot Jacobian") from error
            if np.max(np.abs(delta)) > .10:
                raise RuntimeError(f"{leg}: unexpected {np.max(np.abs(delta)):.3f} rad plant adjustment")
            for name, radians in zip((hip, knee), delta):
                servo_id, _, sign = by_name[name]
                row[str(servo_id)] = str(int(row[str(servo_id)]) + round(sign * radians * scale))
                low, high = by_id[servo_id]
                value = int(row[str(servo_id)])
                if not low <= value <= high:
                    raise ValueError(f"{name} target {value} outside reviewed bounds {low}..{high}")
            changed[leg] += 1

    # Keep release/entry transitions under the receiver's per-frame guard.
    for previous, row in zip(rows, rows[1:]):
        for servo_id in (1, 2, 3, 4, 5, 6):
            old, desired = int(previous[str(servo_id)]), int(row[str(servo_id)])
            row[str(servo_id)] = str(old + max(-args.max_front_tick_step,
                                                min(args.max_front_tick_step, desired - old)))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    args.output.with_suffix(".json").write_text(json.dumps({
        "source": str(args.input), "front_stance_downward_bias_mm": args.depth_mm,
        "ramp_seconds": args.ramp_seconds, "changed_frames": changed,
        "startup_ramp_seconds": args.startup_ramp_seconds,
        "note": "Offline Jacobian-based stance target adjustment. No physical contact sensor is used.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} frames to {args.output}; changed frames: {changed}")


if __name__ == "__main__":
    main()
