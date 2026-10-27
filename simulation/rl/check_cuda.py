"""Parity and no-host-transfer gates for the CUDA training port."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import torch
from cuda_task import CudaTask
from cuda_runner import CudaRunner
from env import WalkConfig
from newton_env import NewtonDogEnv
from train_cuda import Moments,MaskedAdam

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=Path,required=True)
p.add_argument('--frames',type=int,default=30)
a=p.parse_args()
torch.set_num_threads(2)
torch.distributions.Distribution.set_default_validate_args(False)
config_path=a.source/'environment.json'
cfg=WalkConfig(**json.loads(config_path.read_text())['task']) if config_path.exists() else WalkConfig()
cfg=replace(cfg,reset_noise=0)
g=CudaTask(2,cfg,a.source/'robot_dog_v2.xml')
runner=CudaRunner(g)
c=NewtonDogEnv(cfg,model_path=a.source/'robot_dog_v2.xml')
c.reset(seed=1)
qerror=[];obserror=[];rerror=[];forceerror=[]
try:
    for frame in range(a.frames):
        action=np.zeros(12,dtype=np.float32)
        if frame>10: action[:]=.1
        co,cr,cd,ct,ci=c.step(action)
        go,gr,gd,gt,gi,_=runner.step(torch.as_tensor(np.tile(action,(2,1)),device='cuda'))
        qerror.append(float((g.q[0]-torch.as_tensor(c.data.qpos,device='cuda')).abs().max().cpu()))
        obserror.append(float(np.max(np.abs(go[0].cpu().numpy()-co))))
        rerror.append(abs(float(gr[0].cpu())-cr))
        forceerror.append(abs(float(gi['peak_force_n'][0].cpu())-ci['peak_foot_force_n']))
        assert bool(gd[0].cpu())==cd and bool(gt[0].cpu())==ct
    assert max(qerror)<.005, qerror
    assert max(obserror)<.05, obserror
    assert max(rerror)<.3, rerror
    assert max(forceerror)<.5, forceerror
    # Partial reset changes only world zero; world one retains task state.
    preserved=g.q[1].clone();oldtime=g.time[1].clone()
    g.reset(torch.tensor([True,False],device='cuda'))
    torch.testing.assert_close(g.q[1],preserved,rtol=0,atol=0)
    torch.testing.assert_close(g.time[1],oldtime,rtol=0,atol=0)
    assert float(g.time[0].cpu())==0
    # The steady-state task call must not copy tensors back to the host.
    originals={name:getattr(torch.Tensor,name) for name in ('cpu','numpy','item','tolist','__bool__','__float__','__int__')}
    def forbidden(*args,**kwargs): raise AssertionError('Host tensor transfer in CUDA task hot path')
    try:
        for name in originals: setattr(torch.Tensor,name,forbidden)
        runner.step(torch.zeros((2,12),device='cuda'))
    finally:
        for name,value in originals.items(): setattr(torch.Tensor,name,value)
    # Adam preserves both parameters and moments when KL masks an update.
    x=torch.tensor([1.,-2.],device='cuda',requires_grad=True)
    y=x.detach().clone().requires_grad_()
    ox=torch.optim.Adam([x],lr=1e-4);oy=torch.optim.Adam([y],lr=1e-4)
    masked=MaskedAdam(ox)
    for enabled in (True,False,True):
        x.grad=torch.tensor([.3,-.4],device='cuda');y.grad=x.grad.clone()
        masked.step(torch.tensor(enabled,device='cuda'))
        if enabled: oy.step()
    torch.testing.assert_close(x,y,atol=1e-7,rtol=1e-6)
    # Running statistics use the same population-variance merge as VecNormalize.
    moments=Moments(np.zeros(3),np.ones(3),1e-4)
    data=torch.arange(12,device='cuda').reshape(4,3).float()
    moments.update(data)
    expected=(data.double().mean(0)*4)/(4.0001)
    torch.testing.assert_close(moments.mean,expected)
    print(json.dumps({'status':'cuda_task_parity_reset_transfer_and_adam_gates_passed',
        'frames':a.frames,'max_qpos_error':max(qerror),'max_observation_error':max(obserror),
        'max_reward_error':max(rerror),'max_force_error_n':max(forceerror)},indent=2))
finally:
    c.close()
