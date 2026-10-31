"""Evaluate saved weights with CUDA observations/rewards and frozen normalization."""
import argparse
from dataclasses import replace
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


def evaluate(checkpoint,source,episodes=3,seed=10000,cycle_seconds=None,stride_m=None,seconds=None,
             target_speed=None,tracking_weight=None,slip_weight=None):
    manifest=json.loads((checkpoint/'environment.json').read_text())
    cfg=WalkConfig(**manifest['task'])
    if cycle_seconds is not None:cfg=replace(cfg,gait_cycle_seconds=cycle_seconds)
    if stride_m is not None:cfg=replace(cfg,reference_stride=stride_m)
    if seconds is not None:cfg=replace(cfg,episode_seconds=seconds)
    if target_speed is not None:cfg=replace(cfg,target_speed=target_speed)
    if tracking_weight is not None:cfg=replace(cfg,tracking_reward_weight=tracking_weight)
    if slip_weight is not None:cfg=replace(cfg,slip_penalty_weight=slip_weight)
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
    report['gait_cycle_seconds']=cfg.gait_cycle_seconds
    report['reference_stride_m']=cfg.reference_stride
    report['commanded_speed_m_s']=cfg.target_speed
    report['tracking_reward_weight']=cfg.tracking_reward_weight
    report['slip_penalty_weight']=cfg.slip_penalty_weight
    report['eval/net_speed_m_s']=float((result['forward_distance_m']/result['seconds'].clamp_min(1e-9)).mean().cpu())
    # Keep individual trials so averages cannot hide an early ending or unused leg.
    trials={name:value.detach().cpu().tolist() for name,value in {**result,**sums}.items()}
    trial_steps=step_counts.cpu().tolist()
    report['per_episode']=[{
        'batch_seed':seed,'world_index':i,
        **{name:value[i] for name,value in trials.items()},
        'net_speed_m_s':trials['forward_distance_m'][i]/max(trials['seconds'][i],1e-9),
        'steps':dict(zip(LEGS,trial_steps[i])),
    } for i in range(episodes)]
    normalizer.close()
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('checkpoint',type=Path)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--episodes',type=int,default=3)
    p.add_argument('--seed',type=int,default=10000)
    p.add_argument('--seconds',type=float,default=None,help='Evaluation duration only; saved training task remains unchanged')
    p.add_argument('--cycle-seconds',type=float,default=None)
    p.add_argument('--stride-m',type=float,default=None)
    p.add_argument('--target-speed',type=float,default=None)
    p.add_argument('--tracking-weight',type=float,default=None)
    p.add_argument('--slip-weight',type=float,default=None)
    p.add_argument('--output',type=Path,default=Path('cuda-evaluation.json'))
    args=p.parse_args()
    for name in ('target_speed','tracking_weight','slip_weight'):
        value=getattr(args,name)
        if value is not None and (not math.isfinite(value) or value<=0):p.error(name+' must be finite and positive')
    if args.episodes<1:p.error('episodes must be positive')
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds<=0):
        p.error('seconds must be finite and positive')
    if args.cycle_seconds is not None and (not math.isfinite(args.cycle_seconds) or args.cycle_seconds<=0):
        p.error('cycle-seconds must be finite and positive')
    if args.stride_m is not None and (not math.isfinite(args.stride_m) or args.stride_m<=0):
        p.error('stride-m must be finite and positive')
    torch.set_num_threads(2)
    torch.distributions.Distribution.set_default_validate_args(False)
    report=evaluate(args.checkpoint,args.source,args.episodes,seed=args.seed,cycle_seconds=args.cycle_seconds,stride_m=args.stride_m,seconds=args.seconds,
                    target_speed=args.target_speed,tracking_weight=args.tracking_weight,slip_weight=args.slip_weight)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
