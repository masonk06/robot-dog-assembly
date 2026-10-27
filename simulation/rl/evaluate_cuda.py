"""Evaluate saved weights with CUDA observations/rewards and frozen normalization."""
import argparse
import json
import math
from pathlib import Path
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv,VecNormalize
from cuda_task import CudaTask
from cuda_runner import CudaRunner
from train_cuda import CudaNormalize
from env import WalkConfig,DogWalkEnv,LEGS


def evaluate(checkpoint,source,episodes=3,seed=10000):
    manifest=json.loads((checkpoint/'environment.json').read_text())
    cfg=WalkConfig(**manifest['task'])
    task=CudaTask(episodes,cfg,source/'robot_dog_v2.xml',seed=seed)
    runner=CudaRunner(task)
    normalizer=VecNormalize.load(str(checkpoint/'normalize.pkl'),DummyVecEnv([
        lambda:DogWalkEnv(cfg,model_path=source/'robot_dog_v2.xml')]))
    norm=CudaNormalize(normalizer,episodes)
    policy=PPO.load(checkpoint/'policy.zip',device='cuda').policy
    policy.set_training_mode(False)
    obs=norm.observation(task.obs())
    finished=torch.zeros(episodes,dtype=torch.bool,device='cuda')
    sums={name:torch.zeros(episodes,device='cuda') for name in ('four_leg_cycles','foot_lifts','slip_cost')}
    result={name:torch.zeros(episodes,device='cuda') for name in
        ('forward_distance_m','forward_speed_m_s','fallen','sliding','seconds','peak_force_n','peak_landing_m_s')}
    step_counts=torch.zeros((episodes,4),device='cuda')
    observations=torch.zeros(episodes,device='cuda')
    with torch.no_grad():
        for _ in range(math.ceil(cfg.episode_seconds/cfg.control_dt)+1):
            action=policy._predict(obs,deterministic=True)
            raw,_,term,timeout,metrics,reset=runner.step(action)
            alive=~finished
            new=(term|timeout)&alive
            observations+=alive
            for name in sums: sums[name]+=metrics[name]*alive
            result['forward_speed_m_s']+=metrics['forward_speed_m_s']*alive
            for name in ('peak_force_n','peak_landing_m_s'):
                result[name]=torch.maximum(result[name],metrics[name]*alive)
            for name in ('forward_distance_m','fallen','sliding','seconds'):
                result[name]=torch.where(new,metrics[name].float(),result[name])
            step_counts=torch.where(new[:,None],metrics['steps'],step_counts)
            finished|=new
            obs=norm.observation(torch.where((term|timeout)[:,None],reset,raw))
    if not bool(finished.all().cpu()): raise RuntimeError('Evaluation failed to terminate all episodes')
    result['forward_speed_m_s']/=observations
    sums['slip_cost']/=observations
    report={f'eval/{name}':float(value.float().mean().cpu()) for name,value in {**result,**sums}.items()}
    for old,new in (('fallen','fall_fraction'),('sliding','slide_reset_fraction'),
                    ('seconds','episode_seconds'),('slip_cost','foot_slip_m2_s2'),
                    ('peak_force_n','peak_foot_force_n'),('peak_landing_m_s','peak_landing_speed_m_s')):
        report[f'eval/{new}']=report.pop(f'eval/{old}')
    report.update({f'eval/steps/{leg}':float(step_counts[:,i].mean().cpu()) for i,leg in enumerate(LEGS)})
    report['implementation']='CUDA-resident task, frozen policy and normalization'
    report['episodes']=episodes
    normalizer.close()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkpoint',type=Path)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--episodes',type=int,default=3)
    p.add_argument('--output',type=Path,default=Path('cuda-evaluation.json'))
    args=p.parse_args()
    torch.set_num_threads(2)
    torch.distributions.Distribution.set_default_validate_args(False)
    report=evaluate(args.checkpoint,args.source,args.episodes)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
