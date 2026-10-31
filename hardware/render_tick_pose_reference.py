"""Render start and final poses from a hardware-tick static plan for comparison."""
import argparse
import csv
import json
import math
from pathlib import Path

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
JOINTS = (
    "front_left_hip_roll", "front_left_hip_pitch", "front_left_knee_pitch",
    "front_right_hip_roll", "front_right_hip_pitch", "front_right_knee_pitch",
    "rear_left_hip_roll", "rear_left_hip_pitch", "rear_left_knee_pitch",
    "rear_right_hip_roll", "rear_right_hip_pitch", "rear_right_knee_pitch",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", type=Path, default=ROOT / "simulation/mujoco/robot_dog_v2.xml")
    parser.add_argument("--side", action="store_true", help="Use a left-side camera rather than the default three-quarter view")
    args = parser.parse_args()
    with args.plan.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Plan is empty")
    zeros = json.loads((ROOT / "hardware/calibrations/zero-points-current.json").read_text())["joints"]
    directions = json.loads((ROOT / "hardware/calibrations/manual-physical-directions-20261028.json").read_text())["joints"]
    model, data = mujoco.MjModel.from_xml_path(str(args.model)), None
    data = mujoco.MjData(model)
    scale = 4096.0 / (2 * math.pi)
    address = {name: model.jnt_qposadr[mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)] for name in JOINTS}
    renderer = mujoco.Renderer(model, width=640, height=480)
    camera = mujoco.MjvCamera(); camera.lookat[:] = [0, 0, .085]; camera.distance = .42
    camera.azimuth = 90 if args.side else 135; camera.elevation = -5 if args.side else -12

    frames = []
    for row in (rows[0], rows[-1]):
        data.qpos[:] = model.qpos0
        for name in JOINTS:
            servo_id, neutral, sign = zeros[name]["id"], zeros[name]["neutral_ticks"], directions[name]["model_to_encoder_sign"]
            data.qpos[address[name]] = (int(row[str(servo_id)]) - neutral) / (sign * scale)
        mujoco.mj_forward(model, data); renderer.update_scene(data, camera=camera)
        frames.append(Image.fromarray(renderer.render()).convert("RGB"))
    renderer.close()
    canvas = Image.new("RGB", (1280, 530), "white")
    canvas.paste(frames[0], (0, 50)); canvas.paste(frames[1], (640, 50))
    draw = ImageDraw.Draw(canvas)
    try: font = ImageFont.truetype("arial.ttf", 24)
    except OSError: font = ImageFont.load_default()
    draw.text((18, 15), "Simulation replay start pose", fill="black", font=font)
    draw.text((658, 15), "Simulation-equivalent 2 mm front-foot extension", fill="black", font=font)
    args.output.parent.mkdir(parents=True, exist_ok=True); canvas.save(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
