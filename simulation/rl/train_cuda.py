"""CUDA-resident rollout, normalization, GAE and PPO continuation.

Only periodic logging/checkpointing transfers tensors to CPU. Preserve originals.
"""
import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import shutil
import signal
import time
import numpy as np
import torch
import warp as wp
import wandb
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from env import DogWalkEnv, WalkConfig
from cuda_task import CudaTask
from cuda_runner import CudaRunner


class Moments:
    def __init__(self,mean,var,count):
        self.mean=torch.as_tensor(np.array(mean),device='cuda',dtype=torch.float64)
        self.var=torch.as_tensor(np.array(var),device='cuda',dtype=torch.float64)
        self.count=torch.as_tensor(float(count),device='cuda',dtype=torch.float64)

    @torch.no_grad()
    def update(self,x):
        x=x.double()
        mean,var=x.mean(0),x.var(0,unbiased=False)
        n=x.shape[0]
        delta=mean-self.mean
        total=self.count+n
        self.mean+=delta*n/total
        self.var=(self.var*self.count+var*n+delta.square()*self.count*n/total)/total
        self.count=total


class CudaNormalize:
    def __init__(self,saved,n):
        self.obs=Moments(saved.obs_rms.mean,saved.obs_rms.var,saved.obs_rms.count)
        self.ret=Moments(saved.ret_rms.mean,saved.ret_rms.var,saved.ret_rms.count)
        self.returns=torch.zeros(n,device='cuda',dtype=torch.float64)
        self.gamma,self.epsilon,self.clip_obs,self.clip_reward=saved.gamma,saved.epsilon,saved.clip_obs,saved.clip_reward

    def observation(self,x,update=False):
        if update: self.obs.update(x)
        return ((x.double()-self.obs.mean)/torch.sqrt(self.obs.var+self.epsilon)).clamp(-self.clip_obs,self.clip_obs).float()

    def reward(self,x,done):
        self.returns=self.returns*self.gamma+x.double()
        self.ret.update(self.returns)
        result=(x.double()/torch.sqrt(self.ret.var+self.epsilon)).clamp(-self.clip_reward,self.clip_reward).float()
        self.returns.masked_fill_(done,0)
        return result

    def save(self,saved,path):
        # Intentional host copies only at checkpoint boundaries.
        for rms,m in ((saved.obs_rms,self.obs),(saved.ret_rms,self.ret)):
            rms.mean=m.mean.cpu().numpy();rms.var=m.var.cpu().numpy();rms.count=float(m.count.cpu())
        saved.save(str(path))


class MaskedAdam:
    """Adam with GPU-only KL skip decisions, including moments and step counters."""
    def __init__(self,optimizer):
        if not isinstance(optimizer,torch.optim.Adam): raise TypeError('Expected Adam optimizer')
        self.optimizer=optimizer
        for group in optimizer.param_groups:
            if group.get('weight_decay',0)!=0: raise ValueError('Weight decay is unsupported')
            for p in group['params']:
                state=optimizer.state[p]
                if not state:
                    state.update(step=torch.tensor(0.,device='cuda'),exp_avg=torch.zeros_like(p),exp_avg_sq=torch.zeros_like(p))
                state['step']=state['step'].to('cuda')

    @torch.no_grad()
    def step(self,enabled):
        for group in self.optimizer.param_groups:
            b1,b2=group['betas']
            for p in group['params']:
                if p.grad is None: continue
                state=self.optimizer.state[p]
                state['step'].add_(enabled.float())
                state['exp_avg'].copy_(torch.where(enabled,b1*state['exp_avg']+(1-b1)*p.grad,state['exp_avg']))
                state['exp_avg_sq'].copy_(torch.where(enabled,b2*state['exp_avg_sq']+(1-b2)*p.grad.square(),state['exp_avg_sq']))
                step=state['step'].clamp_min(1)
                direction=(state['exp_avg']/(1-b1**step))/(torch.sqrt(state['exp_avg_sq']/(1-b2**step))+group['eps'])
                p.add_(torch.where(enabled,-group['lr']*direction,torch.zeros_like(p)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--resume',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--envs',type=int,default=64)
    p.add_argument('--steps',type=int,default=65536)
    p.add_argument('--rollout',type=int,default=128)
    p.add_argument('--minibatch',type=int,default=256)
    p.add_argument('--epochs',type=int,default=5)
    p.add_argument('--eval-episodes',type=int,default=3,help='0 only for pipeline smoke tests')
    p.add_argument('--eval-seconds',type=float,default=None,help='Evaluation duration; training episode length stays unchanged')
    p.add_argument('--save-every',type=int,default=32768)
    p.add_argument('--max-seconds',type=float,default=None,help='Stop at a rollout boundary and save a time-limit checkpoint')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--tracking-weight',type=float,default=None)
    p.add_argument('--slip-weight',type=float,default=None)
    p.add_argument('--target-speed',type=float,default=None,help='Commanded forward speed in meters per second')
    p.add_argument('--cycle-seconds',type=float,default=None,help='Explicit reference-cadence experiment; saved in the task manifest')
    p.add_argument('--stride-m',type=float,default=None,help='Reference foot sweep in meters; saved in the task manifest')
    p.add_argument('--quasistatic-crawl',action='store_true',help='Use the separate slow three-leg-stance crawl preset; preserves the input/output dimensions')
    p.add_argument('--crawl-response-scale',type=float,default=1.0,help='Simulation-only quasi-static response proxy; replace range with measured servo data')
    p.add_argument('--mode',choices=['online','offline','disabled'],default='online')
    p.add_argument('--output',type=Path,default=Path('runs/cuda'))
    args=p.parse_args()
    if min(args.envs,args.steps,args.rollout,args.minibatch,args.epochs,args.save_every)<1:
        p.error('Counts must be positive')
    if args.eval_episodes<0: p.error('eval-episodes must be nonnegative')
    if args.eval_seconds is not None and (not math.isfinite(args.eval_seconds) or args.eval_seconds<=0):
        p.error('eval-seconds must be finite and positive')
    if args.max_seconds is not None and (not math.isfinite(args.max_seconds) or args.max_seconds<=0):
        p.error('max-seconds must be finite and positive')
    if args.tracking_weight is not None and (not math.isfinite(args.tracking_weight) or args.tracking_weight<=0):
        p.error('tracking-weight must be finite and positive')
    if args.slip_weight is not None and (not math.isfinite(args.slip_weight) or args.slip_weight<=0):
        p.error('slip-weight must be finite and positive')
    if args.target_speed is not None and (not math.isfinite(args.target_speed) or args.target_speed<=0):
        p.error('target-speed must be finite and positive')
    if args.cycle_seconds is not None and (not math.isfinite(args.cycle_seconds) or args.cycle_seconds<=0):
        p.error('cycle-seconds must be finite and positive')
    if args.stride_m is not None and (not math.isfinite(args.stride_m) or args.stride_m<=0):
        p.error('stride-m must be finite and positive')
    if not math.isfinite(args.crawl_response_scale) or args.crawl_response_scale<=0:
        p.error('crawl-response-scale must be finite and positive')
    if not torch.cuda.is_available(): raise RuntimeError('Install CUDA-enabled PyTorch first')
    torch.set_num_threads(2)
    torch.distributions.Distribution.set_default_validate_args(False)
    torch.manual_seed(args.seed)
    manifest=json.loads((args.resume/'environment.json').read_text())
    cfg=WalkConfig(**manifest['task'])
    if args.tracking_weight is not None:
        cfg=replace(cfg,tracking_reward_weight=args.tracking_weight)
    if args.slip_weight is not None:
        cfg=replace(cfg,slip_penalty_weight=args.slip_weight)
    if args.target_speed is not None:
        cfg=replace(cfg,target_speed=args.target_speed)
    if args.cycle_seconds is not None:
        cfg=replace(cfg,gait_cycle_seconds=args.cycle_seconds)
    if args.stride_m is not None:
        cfg=replace(cfg,reference_stride=args.stride_m)
    if args.quasistatic_crawl:
        # Conservative reference and command-filter settings.  This is a new
        # training task, not a modification of the saved walking policy.
        cfg=replace(cfg, target_speed=.005, gait_cycle_seconds=5.0,
                    reference_stride=.010, reference_lift=.012,
                    reference_rear_lift_multiplier=1.0,
                    reference_weight_shift=.008, reference_sway=.035,
                    swing_fraction=.16, action_scale=.025,
                    residual_time_constant=.18*args.crawl_response_scale,
                    max_target_rate=.45/args.crawl_response_scale,
                    slip_penalty_weight=max(cfg.slip_penalty_weight,3.0))
    env=CudaTask(args.envs,cfg,args.source/'robot_dog_v2.xml',seed=args.seed)
    runner=CudaRunner(env)
    template=VecNormalize.load(str(args.resume/'normalize.pkl'),DummyVecEnv([
        lambda:DogWalkEnv(cfg,model_path=args.source/'robot_dog_v2.xml')]))
    norm=CudaNormalize(template,args.envs)
    model=PPO.load(args.resume/'policy.zip',device='cuda')
    policy=model.policy
    adam=MaskedAdam(policy.optimizer)
    run=wandb.init(project='robot-dog-rl',entity='marsdenm-oregon-state-university',mode=args.mode,
        config={**vars(args),'task':vars(cfg),'backend':'newton-cuda-resident',
                'physics_device':str(env.model.device),'ppo_device':str(model.device),
                'normalization':'CUDA float64 moments; rollout float32',
                'note':'Full GPU port; parity and training quality are separate validation gates'})
    folder=args.output/f'{time.strftime("%Y%m%d-%H%M%S")}-{run.id}'
    source=folder/'source';source.mkdir(parents=True)
    shutil.copytree(args.source,source,dirs_exist_ok=True)
    (source/'environment.json').write_text(json.dumps({**manifest,'task':vars(cfg)},indent=2))
    for name in ('cuda_task.py','cuda_runner.py','train_cuda.py','evaluate_cuda.py','env.py','newton_env.py','newton_batch.py','play.py'):
        shutil.copy2(Path(__file__).with_name(name),source/name)
    source_artifact=wandb.Artifact(f'robodog-source-{run.id}',type='dataset')
    source_artifact.add_dir(str(source));run.log_artifact(source_artifact,aliases=['source'])
    completed=0;next_save=args.save_every;initial=model.num_timesteps
    obs=norm.observation(env.obs(),update=True)
    start=time.perf_counter()
    n,t=args.envs,args.rollout
    rollout_obs=torch.empty((t,n,60),device='cuda')
    rollout_actions=torch.empty((t,n,12),device='cuda')
    rewards=torch.empty((t,n),device='cuda');values=rewards.clone();logs=rewards.clone()
    dones=torch.empty((t,n),device='cuda',dtype=torch.bool)
    def save(label):
        path=folder/label;path.mkdir(parents=True,exist_ok=True)
        model.num_timesteps=initial+completed
        model.save(path/'policy.zip')
        norm.save(template,path/'normalize.pkl')
        metadata={**manifest,'task':vars(cfg),'physics_backend':'newton-batch',
                  'training_implementation':'newton-cuda-resident',
                  'adaptation':'ppo_continuation','new_training_steps':completed,
                  'evaluation_episodes':args.eval_episodes,'evaluation_seconds_override':args.eval_seconds,
                  'additional_steps':completed,'normalization':'saved GPU running moments'}
        (path/'environment.json').write_text(json.dumps(metadata,indent=2))
        (path/'source.json').write_text(json.dumps({'path':str(source.resolve()),
            'wandb_source_artifact':f'{run.entity}/{run.project}/robodog-source-{run.id}:source'},indent=2))
        if args.eval_episodes:
            from evaluate_cuda import evaluate
            with torch.random.fork_rng(devices=[0]):
                report=evaluate(path,source,args.eval_episodes,seconds=args.eval_seconds)
            (path/'evaluation.json').write_text(json.dumps(report,indent=2))
            run.log({'global_step':model.num_timesteps,**{key:value for key,value in report.items() if key!='per_episode'}})
        artifact=wandb.Artifact(f'robodog-policy-{run.id}',type='model',metadata={'timesteps':model.num_timesteps})
        artifact.add_dir(str(path));run.log_artifact(artifact,aliases=['latest',label])
        print(f'Saved {path}',flush=True)
    time_limited=False
    stop_requested=False
    def request_stop(signum,frame):
        nonlocal stop_requested
        stop_requested=True
    signal.signal(signal.SIGTERM,request_stop)
    signal.signal(signal.SIGINT,request_stop)
    try:
        while completed<args.steps:
            if stop_requested:break
            if args.max_seconds is not None and time.perf_counter()-start>=args.max_seconds:
                time_limited=True
                break
            policy.set_training_mode(False)
            for i in range(t):
                with torch.no_grad():
                    action,value,log_prob=policy(obs)
                    raw,reward,term,timeout,metrics,reset_obs=runner.step(action)
                    done=term|timeout
                    returned_obs=torch.where(done[:,None],reset_obs,raw)
                    norm.obs.update(returned_obs)
                    next_obs=norm.observation(raw)
                    normalized_reward=norm.reward(reward,done)
                    # Time limits bootstrap from the terminal observation, falls do not.
                    terminal_value=policy.predict_values(next_obs).flatten()
                    normalized_reward+=model.gamma*terminal_value*(timeout&~term)
                    rollout_obs[i].copy_(obs);rollout_actions[i].copy_(action)
                    values[i].copy_(value.flatten());logs[i].copy_(log_prob)
                    rewards[i].copy_(normalized_reward);dones[i].copy_(done)
                    obs=norm.observation(returned_obs)
                completed+=n
            with torch.no_grad():
                last_value=policy.predict_values(obs).flatten()
                advantage=torch.zeros_like(rewards);gae=torch.zeros(n,device='cuda')
                for i in reversed(range(t)):
                    following=last_value if i==t-1 else values[i+1]
                    alive=(~dones[i]).float()
                    delta=rewards[i]+model.gamma*following*alive-values[i]
                    gae=delta+model.gamma*model.gae_lambda*alive*gae
                    advantage[i]=gae
                returns=advantage+values
            policy.set_training_mode(True)
            model._n_updates+=args.epochs
            flat_obs=rollout_obs.flatten(0,1);flat_actions=rollout_actions.flatten(0,1)
            flat_adv=advantage.flatten();flat_returns=returns.flatten();flat_log=logs.flatten()
            enabled=torch.tensor(True,device='cuda')
            updates=torch.zeros((),device='cuda')
            for _ in range(args.epochs):
                permutation=torch.randperm(t*n,device='cuda')
                for begin in range(0,t*n,args.minibatch):
                    idx=permutation[begin:begin+args.minibatch]
                    value,log_prob,entropy=policy.evaluate_actions(flat_obs[idx],flat_actions[idx])
                    ratio=torch.exp(log_prob-flat_log[idx])
                    adv=flat_adv[idx]
                    if adv.numel()>1:
                        adv=(adv-adv.mean())/(adv.std(unbiased=True)+1e-8)
                    kl=((ratio-1)-(log_prob-flat_log[idx])).mean().detach()
                    enabled=enabled & (kl<=1.5*(model.target_kl or .015)) & torch.isfinite(kl)
                    pg=-torch.minimum(adv*ratio,adv*ratio.clamp(.8,1.2)).mean()
                    vf=(flat_returns[idx]-value.flatten()).square().mean()
                    ent=-entropy.mean()
                    loss=pg+model.vf_coef*vf+model.ent_coef*ent
                    policy.optimizer.zero_grad(set_to_none=True)
                    loss.backward()
                    grad_norm=torch.nn.utils.clip_grad_norm_(policy.parameters(),model.max_grad_norm)
                    enabled=enabled & torch.isfinite(loss.detach()) & torch.isfinite(grad_norm)
                    adam.step(enabled)
                    updates+=enabled
            # Only this summary/checkpoint boundary synchronizes device scalars.
            torch.cuda.synchronize()
            summary={'global_step':initial+completed,'time/fps':completed/(time.perf_counter()-start),
                'train/kl_last':float(kl.cpu()),'train/applied_minibatches':float(updates.cpu()),
                'train/reward_mean':float(reward.mean().cpu()),
                'train/forward_speed':float(metrics['forward_speed_m_s'].mean().cpu()),
                'train/contact_capacity_used':float(wp.to_torch(env.d.nacon).max().cpu())/env.capacity}
            if bool(env.overflow.cpu()):
                raise RuntimeError('GPU contact capacity was exhausted; do not trust this rollout')
            run.log(summary);print(json.dumps(summary),flush=True)
            if completed>=next_save:
                save(f'step-{initial+completed}');next_save=completed+args.save_every
        save('interrupted' if stop_requested else 'time-limit' if time_limited else 'final')
    except KeyboardInterrupt:
        save('interrupted')
    finally:
        template.close();run.finish()
    print(f'Run saved to {folder}',flush=True)


if __name__=='__main__': main()
