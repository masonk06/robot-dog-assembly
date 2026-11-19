"""Loop an offline P2S IK diagnostic CSV in a fixed-base MuJoCo viewer."""
from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import mujoco


ROOT = Path(__file__).resolve().parents[2]
MODEL_DEFAULT = ROOT / "simulation" / "mujoco" / "p2s" / "robot_dog_p2s.xml"


def load_rows(path: Path) -> list[dict[str, float]]:
    with path.open(newline="", encoding="utf-8") as stream:
        raw = list(csv.DictReader(stream))
    if len(raw) < 2:
        raise ValueError("Trajectory needs at least two samples")
    rows = [{key: float(value) for key, value in row.items()} for row in raw]
    if any(b["time_seconds"] <= a["time_seconds"] for a, b in zip(rows, rows[1:])):
        raise ValueError("Trajectory times must be strictly increasing")
    return rows


def apply(model: mujoco.MjModel, data: mujoco.MjData, row: dict[str, float]) -> None:
    data.qpos[:] = 0
    # Fixed base: an IK visualization is not a contact-dynamics claim.
    data.qpos[:7] = (0, 0, 0.12, 1, 0, 0, 0)
    for name, value in row.items():
        if name == "time_seconds":
            continue
        joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        if joint < 0:
            raise ValueError(f"Trajectory joint is absent from model: {name}")
        data.qpos[model.jnt_qposadr[joint]] = value
    mujoco.mj_forward(model, data)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trajectory", type=Path)
    parser.add_argument("--model", type=Path, default=MODEL_DEFAULT)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    if args.speed <= 0:
        parser.error("speed must be positive")
    rows = load_rows(args.trajectory)
    model = mujoco.MjModel.from_xml_path(str(args.model.resolve()))
    data = mujoco.MjData(model)
    duration = rows[-1]["time_seconds"]
    import mujoco.viewer
    with mujoco.viewer.launch_passive(model, data) as viewer:
        started = time.perf_counter()
        while viewer.is_running():
            t = ((time.perf_counter() - started) * args.speed) % duration
            index = next((i for i, row in enumerate(rows) if row["time_seconds"] >= t), len(rows) - 1)
            apply(model, data, rows[index])
            viewer.sync()
            time.sleep(0.01)


if __name__ == "__main__":
    main()
