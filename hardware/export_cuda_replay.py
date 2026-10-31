"""Export simulation-only joint targets from a trusted CUDA checkpoint."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('checkpoint', type=Path)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--seconds', type=float, default=10.0)
args = parser.parse_args()
sys.path.insert(0, str(args.source.resolve()))
from env import WalkConfig, DogWalkEnv
from cuda_task import CudaTask
from cuda_runner import CudaRunner
from train_cuda import CudaNormalize

manifest = json.loads((args.checkpoint / 'environment.json').read_text())
config = WalkConfig(**manifest['task'])
task = CudaTask(1, config, args.source / 'robot_dog_v2.xml', seed=10000)
runner = CudaRunner(task)
normalizer = VecNormalize.load(str(args.checkpoint / 'normalize.pkl'), DummyVecEnv([
    lambda: DogWalkEnv(config, model_path=args.source / 'robot_dog_v2.xml')]))
norm = CudaNormalize(normalizer, 1)
policy = PPO.load(args.checkpoint / 'policy.zip', device='cuda').policy
policy.set_training_mode(False)
obs = norm.observation(task.obs())
names = ['front_left_hip_roll','front_left_hip_pitch','front_left_knee_pitch',
         'front_right_hip_roll','front_right_hip_pitch','front_right_knee_pitch',
         'rear_left_hip_roll','rear_left_hip_pitch','rear_left_knee_pitch',
         'rear_right_hip_roll','rear_right_hip_pitch','rear_right_knee_pitch']
args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open('w', newline='') as file, torch.no_grad():
    writer = csv.writer(file)
    writer.writerow(['time_seconds', *names])
    for i in range(math.ceil(args.seconds / config.control_dt)):
        action = policy._predict(obs, deterministic=True)
        raw, _, term, timeout, _, reset = runner.step(action)
        if bool((term | timeout).any().cpu()):
            raise RuntimeError('Simulation episode ended early; replay incomplete')
        writer.writerow([i * config.control_dt, *task.targets[0].cpu().tolist()])
        obs = norm.observation(raw)
normalizer.close()
print(f'Simulation targets saved to {args.output}; radians, not hardware commands.')
