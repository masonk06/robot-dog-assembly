"""Build a static, reversible front-leg extension pose check (no gait cycle)."""
import argparse
import csv
import json
import math
from pathlib import Path

import mujoco
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
JOINT_NAMES = (
    "front_left_hip_roll", "front_left_hip_pitch", "front_left_knee_pitch",
    "front_right_hip_roll", "front_right_hip_pitch", "front_right_knee_pitch",
    "rear_left_hip_roll", "rear_left_hip_pitch", "rear_left_knee_pitch",
    "rear_right_hip_roll", "rear_right_hip_pitch", "rear_right_knee_pitch",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Existing replay CSV; its first row is the known start pose")
    parser.add_argument("output", type=Path)
    parser.add_argument("--depth-mm", type=float, default=2.0)
    parser.add_argument("--move-seconds", type=float, default=1.5)
    parser.add_argument("--hold-seconds", type=float, default=4.0)
    parser.add_argument("--model", type=Path, default=ROOT / "simulation/mujoco/robot_dog_v2.xml")
    parser.add_argument("--limits", type=Path, default=ROOT / "hardware/calibrations/current-frame-limits-20261029.json")
    args = parser.parse_args()
    if not 0 < args.depth_mm <= 2 or args.move_seconds <= 0 or args.hold_seconds <= 0:
        parser.error("depth-mm must be in (0, 2] and durations must be positive")

    with args.input.open(newline="", encoding="utf-8") as handle:
        source = next(csv.DictReader(handle), None)
    if source is None:
        raise ValueError("Input replay is empty")
    zeros = json.loads((ROOT / "hardware/calibrations/zero-points-current.json").read_text())["joints"]
    directions = json.loads((ROOT / "hardware/calibrations/manual-physical-directions-20261028.json").read_text())["joints"]
    limits = json.loads(args.limits.read_text())["joints"]
    by_name = {name: (zeros[name]["id"], zeros[name]["neutral_ticks"], directions[name]["model_to_encoder_sign"])
               for name in JOINT_NAMES}
    by_id = {item["id"]: (item["minimum_ticks"] + 10, item["maximum_ticks"] - 10)
             for item in limits.values()}
    model, data = mujoco.MjModel.from_xml_path(str(args.model)), None
    data = mujoco.MjData(model)
    scale = 4096.0 / (2 * math.pi)
    qpos = {name: model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in JOINT_NAMES}
    dof = {name: model.jnt_dofadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in JOINT_NAMES}
    for name in JOINT_NAMES:
        sid, zero, sign = by_name[name]
        data.qpos[qpos[name]] = (int(source[str(sid)]) - zero) / (sign * scale)
    mujoco.mj_forward(model, data)
    target = {str(sid): int(source[str(sid)]) for sid in range(1, 13)}
    deltas = {}
    for leg in ("front_left", "front_right"):
        hip, knee = f"{leg}_hip_pitch", f"{leg}_knee_pitch"
        site = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, f"{leg}_foot")
        jac = np.zeros((3, model.nv)); mujoco.mj_jacSite(model, data, jac, None, site)
        adjustment = np.linalg.solve(jac[np.ix_((0, 2), (dof[hip], dof[knee]))], [0.0, -args.depth_mm / 1000])
        for name, radians in zip((hip, knee), adjustment):
            sid, _, sign = by_name[name]
            target[str(sid)] += round(sign * radians * scale)
            low, high = by_id[sid]
            if not low <= target[str(sid)] <= high:
                raise ValueError(f"{name} target outside reviewed bounds")
            deltas[name] = target[str(sid)] - int(source[str(sid)])

    fields = ["time_seconds", *map(str, range(1, 13))]
    rows = []
    total = args.move_seconds + args.hold_seconds
    for step in range(round(total / .02) + 1):
        time_s = step * .02
        fraction = min(1.0, time_s / args.move_seconds)
        fraction = fraction * fraction * (3 - 2 * fraction)
        row = {"time_seconds": f"{time_s:.2f}"}
        for sid in range(1, 13):
            start, finish = int(source[str(sid)]), target[str(sid)]
            row[str(sid)] = round(start + (finish - start) * fraction)
        rows.append(row)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    args.output.with_suffix(".json").write_text(json.dumps({
        "source": str(args.input), "front_foot_downward_offset_mm": args.depth_mm,
        "move_seconds": args.move_seconds, "hold_seconds": args.hold_seconds,
        "encoder_deltas_at_final_pose": deltas,
        "note": "Static pose comparison only; no saved zero values or servo EEPROM registers were changed.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} static-pose frames to {args.output}; final deltas: {deltas}")


if __name__ == "__main__":
    main()
