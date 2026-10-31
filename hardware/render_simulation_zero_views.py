"""Render exact MuJoCo model-zero poses for physical alignment reference."""
import argparse
from pathlib import Path

import mujoco
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]


def render(model, data, azimuth):
    renderer = mujoco.Renderer(model, width=640, height=480)
    camera = mujoco.MjvCamera()
    camera.lookat[:] = [0.0, 0.0, .085]
    camera.distance = .43
    camera.azimuth = azimuth
    camera.elevation = -5
    mujoco.mj_forward(model, data)
    renderer.update_scene(data, camera=camera)
    image = Image.fromarray(renderer.render()).convert("RGB")
    renderer.close()
    return image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--model", type=Path, default=ROOT / "simulation/mujoco/robot_dog_v2.xml")
    args = parser.parse_args()
    model = mujoco.MjModel.from_xml_path(str(args.model))
    data = mujoco.MjData(model)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    try: font = ImageFont.truetype("arial.ttf", 30)
    except OSError: font = ImageFont.load_default()
    for filename, azimuth, label in (
        ("simulation-zero-side-a.png", 90, "Simulation model zero — side A (front is left)"),
        ("simulation-zero-side-b.png", 270, "Simulation model zero — side B (front is right)"),
    ):
        image = render(model, data, azimuth)
        canvas = Image.new("RGB", (640, 530), "white")
        canvas.paste(image, (0, 50))
        ImageDraw.Draw(canvas).text((20, 12), label, fill="black", font=font)
        path = args.output_dir / filename
        canvas.save(path)
        print(path)


if __name__ == "__main__":
    main()
