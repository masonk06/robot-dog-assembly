"""Watch a trusted saved policy with the exact saved observation statistics."""
import argparse
import json
from pathlib import Path
import time

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from env import DogWalkEnv, WalkConfig


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("checkpoint", type=Path)
    p.add_argument("--source", type=Path, help="Downloaded source artifact directory, if moved")
    p.add_argument("--seconds", type=float, default=60)
    args = p.parse_args()
    manifest = json.loads((args.checkpoint / "environment.json").read_text())
    task = manifest["task"]
    config = WalkConfig(**{**task, "reward_version": task.get("reward_version", 1)})
    source = args.source or Path(json.loads((args.checkpoint / "source.json").read_text())["path"])
    env_class = DogWalkEnv
    if manifest.get('physics_backend', '').startswith('newton'):
        from newton_env import NewtonDogEnv
        env_class = NewtonDogEnv
    robot = env_class(config, model_path=source / "robot_dog_v2.xml")
    env = DummyVecEnv([lambda: robot])
    env = VecNormalize.load(str(args.checkpoint / "normalize.pkl"), env)
    env.training, env.norm_reward = False, False
    model = PPO.load(args.checkpoint / "policy.zip", device="cpu")
    try:
        obs = env.reset()
        robot.render()
        deadline = time.monotonic() + args.seconds
        while robot.viewer.is_running() and time.monotonic() < deadline:
            start = time.monotonic()
            action, _ = model.predict(obs, deterministic=True)
            obs, _, _, _ = env.step(action)
            robot.render()
            time.sleep(max(0, config.control_dt - (time.monotonic() - start)))
    finally:
        env.close()


if __name__ == "__main__":
    main()
