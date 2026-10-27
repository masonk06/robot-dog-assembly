"""Train slow walking with PPO; save resumable bundles and W&B artifacts."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import wandb
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize, SubprocVecEnv
from stable_baselines3.common.running_mean_std import RunningMeanStd

from env import DogWalkEnv, WalkConfig, MODEL

ROOT = Path(__file__).resolve().parents[2]
ENV_CLASS = DogWalkEnv
EVAL_EPISODES = 3
EVAL_SECONDS = None


def evaluate(model, normalizer, config, model_path, episodes=3):
    """Separate deterministic evaluation; never updates training statistics."""
    distances, speeds, falls, slides, durations = [], [], [], [], []
    foot_metrics = []
    if EVAL_SECONDS is not None:
        from dataclasses import replace
        config = replace(config, episode_seconds=EVAL_SECONDS)
    episodes = EVAL_EPISODES
    env = ENV_CLASS(config, model_path=model_path)
    try:
        for seed in range(10000, 10000 + episodes):
            obs, _ = env.reset(seed=seed)
            velocities = []
            peak_force, peak_landing, slip, cycles = 0., 0., [], 0
            lifts, pattern_matches, clearance_matches = 0, [], []
            while True:
                action, _ = model.predict(normalizer.normalize_obs(obs[None]), deterministic=True)
                obs, _, terminated, truncated, info = env.step(action[0])
                velocities.append(info["forward_speed"])
                peak_force = max(peak_force, info["peak_foot_force_n"])
                peak_landing = max(peak_landing, info["peak_landing_speed_m_s"])
                slip.append(info["foot_slip_m2_s2"])
                cycles += info["four_leg_cycles"]
                lifts += info["foot_lifts"]
                pattern_matches.append(info["gait_contact_match"])
                clearance_matches.append(info["gait_clearance_match"])
                if terminated or truncated:
                    distances.append(info["forward_distance"])
                    speeds.append(np.mean(velocities))
                    falls.append(float(info["fallen"]))
                    slides.append(float(info["sliding"]))
                    durations.append(env.data.time)
                    foot_metrics.append({"eval/peak_foot_force_n": peak_force,
                        "eval/peak_landing_speed_m_s": peak_landing,
                        "eval/foot_slip_m2_s2": float(np.mean(slip)),
                        "eval/four_leg_cycles": cycles,
                        "eval/foot_lifts": lifts,
                        "eval/gait_contact_match": float(np.mean(pattern_matches)),
                        "eval/gait_clearance_match": float(np.mean(clearance_matches)),
                        **{f"eval/{k}": v for k, v in info.items() if k.startswith("steps/")}})
                    break
    finally:
        env.close()
    return {"eval/forward_distance_m": float(np.mean(distances)),
            "eval/forward_speed_m_s": float(np.mean(speeds)),
            "eval/fall_fraction": float(np.mean(falls)),
            "eval/slide_reset_fraction": float(np.mean(slides)),
            "eval/episode_seconds": float(np.mean(durations)),
            **{k: float(np.mean([m[k] for m in foot_metrics])) for k in foot_metrics[0]}}


class SaveAndLog(BaseCallback):
    def __init__(self, run, folder, interval, config, source):
        super().__init__()
        self.run, self.folder, self.interval = run, folder, interval
        self.config, self.source = config, source
        self.next_save = 0

    def _on_training_start(self):
        self.next_save = self.num_timesteps + self.interval

    def save(self, label):
        checkpoint = self.folder / label
        checkpoint.mkdir(parents=True, exist_ok=True)
        self.model.save(checkpoint / "policy.zip")
        self.training_env.save(checkpoint / "normalize.pkl")
        shutil.copy2(self.source / "environment.json", checkpoint / "environment.json")
        # Exact source/model bundle is saved once per run; its W&B artifact
        # version is recorded in each policy checkpoint.
        (checkpoint / "source.json").write_text(json.dumps({"path": str(self.source),
            "wandb_source_artifact": self.source_artifact}, indent=2))
        metrics = evaluate(self.model, self.training_env, self.config, self.source / "robot_dog_v2.xml")
        self.run.log({"global_step": self.num_timesteps, **metrics})
        (checkpoint / "evaluation.json").write_text(json.dumps(metrics, indent=2))
        artifact = wandb.Artifact(f"robodog-policy-{self.run.id}", type="model",
                                  metadata={"timesteps": self.num_timesteps, **metrics})
        artifact.add_dir(str(checkpoint))
        self.run.log_artifact(artifact, aliases=["latest", label])
        print(f"Saved {checkpoint}; evaluation: {metrics}", flush=True)

    def _on_step(self):
        if self.n_calls % 100 == 0:
            infos = self.locals["infos"]
            metrics = {f"train/{k}": float(np.mean([i[k] for i in infos]))
                       for k in ("forward_speed", "height", "tilt_degrees", "peak_foot_force_n",
                                 "peak_landing_speed_m_s", "foot_slip_m2_s2", "useful_steps", "four_leg_cycles",
                                 "sliding", "stance_drift_m", "foot_lifts", "gait_contact_match", "gait_clearance_match")}
            metrics.update({f"train/{k}": float(np.mean([i[k] for i in infos]))
                            for k in infos[0] if k.startswith("reward/")})
            self.run.log({"global_step": self.num_timesteps, **metrics})
        if self.num_timesteps >= self.next_save:
            self.save(f"step-{self.num_timesteps}")
            self.next_save = self.num_timesteps + self.interval
        return True


def main():
    global ENV_CLASS, EVAL_EPISODES, EVAL_SECONDS
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--steps", type=int, default=200000)
    p.add_argument("--backend", choices=["mujoco", "newton", "newton-batch"], default="mujoco")
    p.add_argument("--eval-episodes", type=int, default=3)
    p.add_argument("--eval-seconds", type=float, default=None)
    p.add_argument("--envs", type=int, default=4)
    p.add_argument("--parallel", action="store_true", help="Use a separate CPU process per environment")
    p.add_argument("--torch-threads", type=int, default=2)
    p.add_argument("--source", type=Path, help="Restored source artifact directory for a moved checkpoint")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--speed", type=float, default=0.01)
    p.add_argument("--save-every", type=int, default=20000)
    p.add_argument("--project", default="robot-dog-rl")
    p.add_argument("--entity", default=None)
    p.add_argument("--mode", choices=["online", "offline", "disabled"], default="online")
    p.add_argument("--resume", type=Path, help="Local checkpoint directory (trusted files only)")
    p.add_argument("--upgrade-rewards", action="store_true", help="Upgrade reward version (requires compatible observations)")
    p.add_argument("--output", type=Path, default=ROOT / "runs" / "slow-walk")
    args = p.parse_args()
    if args.eval_episodes < 1 or (args.eval_seconds is not None and args.eval_seconds <= 0):
        p.error('Evaluation duration/count must be positive')
    EVAL_EPISODES, EVAL_SECONDS = args.eval_episodes, args.eval_seconds
    if args.backend.startswith('newton'):
        if args.parallel or (args.backend == 'newton' and args.envs != 1):
            p.error('Newton validation bridge requires --envs 1 without --parallel; GPU batching is not implemented')
        from newton_env import NewtonDogEnv
        ENV_CLASS = NewtonDogEnv
    if args.steps < 1 or args.envs < 1 or args.save_every < 1 or args.torch_threads < 1:
        p.error("steps, envs and save-every must be positive")
    if args.mode == "online" and not wandb.login(timeout=30):
        raise SystemExit("Authenticate first with: .venv\\Scripts\\wandb.exe login")
    config = WalkConfig(target_speed=args.speed)
    source_model = args.source / "robot_dog_v2.xml" if args.source else MODEL
    if args.resume:
        saved = json.loads((args.resume / "environment.json").read_text())
        config = WalkConfig(**{**saved["task"], "reward_version":
            WalkConfig().reward_version if args.upgrade_rewards else saved["task"].get("reward_version", 1)})
        expected_obs = 60 if config.reward_version >= 5 else 48 if config.reward_version >= 4 else 46
        if saved.get("observation_size", 46) != expected_obs:
            raise SystemExit("The controller observation size changed. Start fresh without --resume or --upgrade-rewards; keep --source for the model.")
        source_meta = json.loads((args.resume / "source.json").read_text())
        source_model = Path(source_meta["path"]) / "robot_dog_v2.xml"
        if args.source:
            source_model = args.source / "robot_dog_v2.xml"
        if not source_model.exists():
            raise SystemExit("Restore the source artifact and update source.json path before resuming")
    torch.set_num_threads(args.torch_threads)
    versions = {pkg: importlib.metadata.version(pkg) for pkg in
                ("mujoco", "numpy", "torch", "stable-baselines3", "gymnasium", "wandb")}
    if args.backend.startswith('newton'):
        versions.update({pkg: importlib.metadata.version(pkg) for pkg in ('newton','warp-lang','mujoco-warp')})
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    run = wandb.init(project=args.project, entity=args.entity, mode=args.mode,
                     config={**vars(args), "task": vars(config), "versions": versions,
                             "source_commit": commit, "algorithm": "PPO", "device": "cpu"},
                     sync_tensorboard=True, save_code=False)
    folder = args.output / f"{time.strftime('%Y%m%d-%H%M%S')}-{run.id}"
    source = folder / "source"
    source.mkdir(parents=True)
    shutil.copy2(source_model, source / "robot_dog_v2.xml")
    shutil.copytree(source_model.parent / "assets", source / "assets")
    for name in ("env.py", "train.py", "play.py", "screen_reference.py", "newton_env.py", "newton_batch.py"):
        shutil.copy2(Path(__file__).with_name(name), source / name)
    (source / "versions.json").write_text(json.dumps(versions, indent=2))
    if args.backend == 'newton-batch':
        from newton_batch import NewtonBatchVecEnv
        from stable_baselines3.common.vec_env import VecMonitor
        raw_env = VecMonitor(NewtonBatchVecEnv(args.envs,config,source / 'robot_dog_v2.xml',seed=args.seed))
    else:
        raw_env = make_vec_env(ENV_CLASS, n_envs=args.envs, seed=args.seed,
                               vec_env_cls=SubprocVecEnv if args.parallel else None,
                               env_kwargs={"config": config, "model_path": source / "robot_dog_v2.xml"})
    env = VecNormalize.load(str(args.resume / "normalize.pkl"), raw_env) if args.resume else VecNormalize(
        raw_env, norm_obs=True, norm_reward=True, clip_obs=10.)
    env.training = True
    if args.resume and args.upgrade_rewards:
        # Keep observation scaling but relearn reward scaling for the new objective.
        env.ret_rms = RunningMeanStd(shape=())
    probe = DogWalkEnv(config, model_path=source / "robot_dog_v2.xml")
    manifest = probe.manifest()
    manifest['physics_backend'] = args.backend
    manifest['evaluation_episodes'] = args.eval_episodes
    manifest['evaluation_seconds_override'] = args.eval_seconds
    (source / "environment.json").write_text(json.dumps(manifest, indent=2))
    probe.close()
    if config.reward_version >= 5:
        from screen_reference import screen
        baseline = screen(config, model_path=source / "robot_dog_v2.xml")
        (source / "reference_baseline.json").write_text(json.dumps(baseline, indent=2))
        run.log({"baseline/seconds": baseline["seconds"],
                 "baseline/forward_distance_m": baseline["distance_m"],
                 "baseline/foot_lifts": baseline["foot_lifts"]})
    artifact = wandb.Artifact(f"robodog-source-{run.id}", type="dataset")
    artifact.add_dir(str(source))
    run.log_artifact(artifact, aliases=["source"])
    callback = SaveAndLog(run, folder, args.save_every, config, source)
    callback.source_artifact = f"{run.entity}/{run.project}/{artifact.name}:source"
    model = PPO.load(args.resume / "policy.zip", env=env, device="cpu") if args.resume else PPO(
        "MlpPolicy", env, device="cpu", n_steps=256, batch_size=64, n_epochs=5,
        learning_rate=1e-4 if config.reward_version >= 7 else 3e-4,
        target_kl=.015 if config.reward_version >= 7 else None,
        gamma=0.99, gae_lambda=0.95, seed=args.seed,
        policy_kwargs={"net_arch": [128, 128],
                       "log_std_init": -2.0 if config.reward_version >= 7 else 0.0}, verbose=1,
        tensorboard_log=str(folder / "tensorboard"))
    model.tensorboard_log = str(folder / "tensorboard")
    if args.resume and (args.upgrade_rewards or args.backend.startswith('newton')):
        if model.ep_info_buffer is not None:
            model.ep_info_buffer.clear()
    try:
        model.learn(total_timesteps=args.steps, callback=callback,
                    reset_num_timesteps=not bool(args.resume))
        callback.save("final")
    except KeyboardInterrupt:
        callback.save("interrupted")
    finally:
        env.close()
        run.finish()
    print(f"Run saved to {folder}")


if __name__ == "__main__":
    main()
