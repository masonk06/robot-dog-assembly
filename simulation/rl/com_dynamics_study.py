"""Controlled COM / payload study for the frozen overnight PPO policy.

Creates separate MuJoCo XML variants; it never edits the saved source model,
checkpoint, or real-hardware configuration.
"""
import argparse
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import mujoco
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


ROOT = Path(__file__).resolve().parents[2]
LEGS = ("front_left", "front_right", "rear_left", "rear_right")


def comma(values):
    return " ".join(f"{value:.9g}" for value in values)


def make_variant(source_xml, output, com_offset_x=0., payload=None):
    tree = ET.parse(source_xml); root = tree.getroot()
    compiler = root.find("compiler")
    compiler.set("meshdir", str(source_xml.parent.joinpath("assets").resolve()).replace("\\", "/"))
    base = root.find("./worldbody/body[@name='base']")
    inertial = base.find("inertial")
    pos = [float(v) for v in inertial.get("pos").split()]
    pos[0] += com_offset_x
    inertial.set("pos", comma(pos))
    if payload:
        body = ET.SubElement(base, "body", name=payload["name"], pos=comma(payload["pos"]))
        # Solid 20 mm cube approximation, declared separately from the robot.
        side = payload["cube_side_m"]
        diagonal = payload["mass_kg"] * side * side / 6
        ET.SubElement(body, "inertial", mass=f"{payload['mass_kg']:.9g}", pos="0 0 0",
                      diaginertia=comma((diagonal, diagonal, diagonal)))
    ET.indent(tree, space="  ")
    output.parent.mkdir(parents=True, exist_ok=True)
    tree.write(output, encoding="utf-8", xml_declaration=False)


def model_summary(model_path):
    model = mujoco.MjModel.from_xml_path(str(model_path)); data = mujoco.MjData(model); mujoco.mj_forward(model, data)
    mass = float(model.body_mass.sum())
    com = (model.body_mass[:, None] * data.xipos).sum(0) / mass
    base = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base")
    body_com = data.xmat[base].reshape(3, 3).T @ (com - data.xpos[base])
    bodies = [{"name": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i),
               "mass_kg": float(model.body_mass[i]), "world_com_m": data.xipos[i].tolist()}
              for i in range(model.nbody) if model.body_mass[i] > 0]
    return {"total_mass_kg": mass, "world_com_m": com.tolist(), "body_frame_com_m": body_com.tolist(), "bodies": bodies}


def run_episode(robot, normalizer, policy, seed, seconds):
    raw, _ = robot.reset(seed=seed)
    obs = normalizer.normalize_obs(raw[None])
    contacts = [[] for _ in LEGS]
    stance = [[] for _ in LEGS]
    front_force, rear_force, slip, pitch, tracking, actions = [], [], [], [], [], []
    done = False; info = {}
    for _ in range(math.ceil(seconds / robot.config.control_dt) + 2):
        action, _ = policy.predict(obs, deterministic=True)
        action = np.asarray(action)[0]
        raw, _, terminated, truncated, info = robot.step(action)
        obs = normalizer.normalize_obs(raw[None])
        forces, velocities = robot._feet()
        current = forces > .2
        for i in range(4):
            contacts[i].append(bool(current[i]))
        front_force.append(float(forces[:2].sum())); rear_force.append(float(forces[2:].sum()))
        slip.append(float(np.mean(np.linalg.norm(velocities[current, :2], axis=1))) if current.any() else 0.)
        gravity, _, _ = robot._state()
        pitch.append(float(np.degrees(np.arctan2(gravity[0], -gravity[2]))))
        tracking.append(float(np.mean(np.abs(robot.data.qpos[robot.qadr] - robot.data.ctrl))))
        actions.append(float(np.mean(np.abs(action))))
        if terminated or truncated:
            done = True; break
    dt = robot.config.control_dt
    for i in range(4):
        duration = 0.
        for in_contact in contacts[i] + [False]:
            if in_contact: duration += dt
            elif duration:
                stance[i].append(duration); duration = 0.
    stance_mean = [float(np.mean(values)) if values else 0. for values in stance]
    return {
        "seed": seed, "completed": done, "seconds": float(info.get("seconds", len(actions) * dt)),
        "forward_displacement_m": float(info.get("forward_distance", 0.)),
        "forward_speed_m_s": float(info.get("forward_distance", 0.)) / max(float(info.get("seconds", len(actions) * dt)), 1e-9),
        "fallen": bool(info.get("fallen", False)), "sliding": bool(info.get("sliding", False)),
        "front_stance_duration_s": float(np.mean(stance_mean[:2])), "rear_stance_duration_s": float(np.mean(stance_mean[2:])),
        "front_normal_force_n": float(np.mean(front_force)), "rear_normal_force_n": float(np.mean(rear_force)),
        "front_peak_force_n": float(max(front_force, default=0.)), "rear_peak_force_n": float(max(rear_force, default=0.)),
        "mean_contact_slip_m_s": float(np.mean(slip)), "max_abs_pitch_deg": float(max(map(abs, pitch), default=0.)),
        "mean_pitch_deg": float(np.mean(pitch)), "joint_tracking_error_rad": float(np.mean(tracking)),
        "policy_action_magnitude": float(np.mean(actions)),
    }


def aggregate(trials):
    numeric = [key for key, value in trials[0].items() if isinstance(value, (int, float)) and key != "seed"]
    result = {key: float(np.mean([trial[key] for trial in trials])) for key in numeric}
    result["fall_fraction"] = float(np.mean([trial["fallen"] for trial in trials]))
    result["slide_fraction"] = float(np.mean([trial["sliding"] for trial in trials]))
    return result


def save_plot(cases, output):
    metrics = [("forward_speed_m_s", "Forward speed (m/s)"), ("front_normal_force_n", "Front normal force (N)"),
               ("rear_normal_force_n", "Rear normal force (N)"), ("max_abs_pitch_deg", "Max |pitch| (deg)")]
    image = Image.new("RGB", (1300, 720), "white"); draw = ImageDraw.Draw(image)
    try: font = ImageFont.truetype("arial.ttf", 18); title = ImageFont.truetype("arial.ttf", 24)
    except OSError: font = title = ImageFont.load_default()
    labels = list(cases)
    for panel, (metric, title_text) in enumerate(metrics):
        x0 = 50 + (panel % 2) * 640; y0 = 50 + (panel // 2) * 340; width, height = 560, 230
        values = [cases[name]["aggregate"][metric] for name in labels]; maximum = max(max(values), 1e-6)
        draw.text((x0, y0), title_text, fill="black", font=title)
        draw.line((x0, y0 + height, x0 + width, y0 + height), fill="black", width=2)
        bar = width / max(len(labels), 1)
        for i, (label, value) in enumerate(zip(labels, values)):
            left = x0 + 20 + i * bar; right = left + bar * .55; top = y0 + height - value / maximum * (height - 35)
            draw.rectangle((left, top, right, y0 + height), fill="#3f7fbf")
            draw.text((left, y0 + height + 5), label.replace("_", "\n"), fill="black", font=font)
            draw.text((left, max(y0 + 25, top - 20)), f"{value:.3g}", fill="black", font=font)
    output.parent.mkdir(parents=True, exist_ok=True); image.save(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, default=ROOT / "runs/overnight-3cms-review/best/checkpoint")
    parser.add_argument("--source", type=Path, default=ROOT / "runs/overnight-3cms-review/best/source")
    parser.add_argument("--output", type=Path, default=ROOT / "runs/com-dynamics-study")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--seconds", type=float, default=20.)
    parser.add_argument("--payload-mass-kg", type=float, default=.10,
                        help="Illustrative forward payload only; replace with measured payload mass for an actual-payload study")
    args = parser.parse_args()
    if args.episodes < 1 or args.seconds <= 0 or args.payload_mass_kg <= 0:
        parser.error("episodes, seconds, and payload mass must be positive")
    sys.path.insert(0, str(args.source.resolve()))
    from env import DogWalkEnv, WalkConfig
    manifest = json.loads((args.checkpoint / "environment.json").read_text())
    config = WalkConfig(**manifest["task"])
    variants = {
        "baseline": {"com_offset_x_m": 0.},
        "com_forward_30mm": {"com_offset_x_m": -.03},
        "com_rear_30mm": {"com_offset_x_m": .03},
        "payload_forward_example": {"com_offset_x_m": 0., "payload": {"name": "declared_forward_payload", "mass_kg": args.payload_mass_kg, "pos": (-.03, 0., .04), "cube_side_m": .02}},
    }
    policy = PPO.load(args.checkpoint / "policy.zip", device="cpu")
    policy.policy.set_training_mode(False)
    report = {"study": {"source_model": str(args.source / "robot_dog_v2.xml"), "checkpoint": str(args.checkpoint),
                          "episodes": args.episodes, "seconds": args.seconds, "same_seeds": list(range(10000, 10000 + args.episodes)),
                          "forward_axis": "negative local X", "payload_note": "payload_forward_example is not the user's actual temporary weight unless its mass/location equal the passed values."}, "cases": {}}
    for name, spec in variants.items():
        model_path = args.output / "models" / f"{name}.xml"
        make_variant(args.source / "robot_dog_v2.xml", model_path,
                     com_offset_x=spec["com_offset_x_m"], payload=spec.get("payload"))
        robot = DogWalkEnv(config, model_path=model_path)
        vec = DummyVecEnv([lambda: robot])
        normalizer = VecNormalize.load(str(args.checkpoint / "normalize.pkl"), vec)
        normalizer.training = normalizer.norm_reward = False
        trials = [run_episode(robot, normalizer, policy, seed, args.seconds) for seed in range(10000, 10000 + args.episodes)]
        normalizer.close()
        report["cases"][name] = {"spec": spec, "model": model_summary(model_path), "aggregate": aggregate(trials), "trials": trials}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    fields = ["case", "total_mass_kg", "body_com_x_m", "forward_speed_m_s", "forward_displacement_m", "front_stance_duration_s", "rear_stance_duration_s", "front_normal_force_n", "rear_normal_force_n", "mean_contact_slip_m_s", "max_abs_pitch_deg", "joint_tracking_error_rad", "policy_action_magnitude", "fall_fraction", "slide_fraction"]
    with (args.output / "comparison.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for name, value in report["cases"].items():
            agg, model = value["aggregate"], value["model"]
            writer.writerow({"case": name, "total_mass_kg": model["total_mass_kg"], "body_com_x_m": model["body_frame_com_m"][0], **{key: agg[key] for key in fields if key in agg}})
    save_plot(report["cases"], args.output / "comparison.png")
    print(json.dumps({"output": str(args.output), "cases": {name: value["aggregate"] for name, value in report["cases"].items()}}, indent=2))


if __name__ == "__main__":
    main()
