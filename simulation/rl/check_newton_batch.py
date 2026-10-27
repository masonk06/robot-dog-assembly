"""Validate batch parity, world isolation, resets and aggregate throughput."""
import argparse
from dataclasses import replace
import json
import time
import numpy as np
from env import WalkConfig
from newton_env import NewtonDogEnv
from newton_batch import NewtonBatchVecEnv

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',required=True)
p.add_argument('--envs',type=int,default=4)
p.add_argument('--frames',type=int,default=30)
a = p.parse_args()
from pathlib import Path
cfg = WalkConfig(reset_noise=0)
path = Path(a.source)/'robot_dog_v2.xml'
batch = NewtonBatchVecEnv(a.envs,cfg,path)
single = NewtonDogEnv(cfg,model_path=path)
batch.reset(); single.reset(seed=42)
errors=[]
try:
    for frame in range(10):
        obs,rewards,dones,infos = batch.step(np.zeros((a.envs,12)))
        so,sr,sd,st,si = single.step(np.zeros(12))
        errors.append(float(np.max(np.abs(batch.tasks[0].data.qpos-single.data.qpos))))
        np.testing.assert_allclose(batch.tasks[0].gpu_forces,single.gpu_forces,atol=.1,rtol=.05)
        np.testing.assert_allclose(rewards[0],sr,atol=.1,rtol=.05)
    assert max(errors)<.001, 'Batch differs from single-world physics'
    # Only world zero trips its fall guard. Others keep their episode state.
    batch.tasks[0].config = replace(cfg,min_height=.2)
    _,_,dones,infos = batch.step(np.zeros((a.envs,12)))
    assert dones[0] and not dones[1:].any()
    assert 'terminal_observation' in infos[0]
    assert batch.tasks[0].data.time==0 and batch.tasks[1].data.time>.2
    batch.tasks[0].config = cfg
    # Use distinct actions to check that worlds are not accidentally sharing control.
    actions=np.zeros((a.envs,12)); actions[1]=.5
    batch.step(actions)
    assert not np.allclose(batch.tasks[0].targets,batch.tasks[1].targets)
    batch.reset()
    start=time.perf_counter()
    for _ in range(a.frames): batch.step(np.zeros((a.envs,12)))
    elapsed=time.perf_counter()-start
    print(json.dumps({'status':'batch_parity_and_isolated_reset_passed',
          'envs':a.envs,'max_single_batch_qpos_difference':max(errors),
          'benchmark_frames':a.frames,'seconds':elapsed,
          'aggregate_env_steps_per_second':a.envs*a.frames/elapsed,
          'physics':'one shared CUDA solver','observations_rewards':'CPU per-world'},indent=2))
finally:
    batch.close();single.close()
