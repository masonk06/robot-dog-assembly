"""Check configured GPU reward/command changes against identical physical rollouts."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import torch
from cuda_task import CudaTask
from cuda_runner import CudaRunner
from env import WalkConfig,slip_penalty

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--source',type=Path,required=True)
a=p.parse_args()
torch.set_num_threads(2)
cfg=WalkConfig(**json.loads((a.source/'environment.json').read_text())['task'])
cfg=replace(cfg,reset_noise=0)
old_cfg=replace(cfg,target_speed=.01,tracking_reward_weight=1.25,slip_penalty_weight=2.)
old=CudaTask(2,old_cfg,a.source/'robot_dog_v2.xml',seed=7)
old_runner=CudaRunner(old)
new=CudaTask(2,cfg,a.source/'robot_dog_v2.xml',seed=7)
new_runner=CudaRunner(new)
slip_seen=False
for frame in range(40):
    action=torch.full((2,12),.1 if frame>10 else 0.,device='cuda')
    oo,orr,ot,ou,om,_=old_runner.step(action)
    no,nr,nt,nu,nm,_=new_runner.step(action)
    torch.testing.assert_close(old.q,new.q,atol=1e-6,rtol=0)
    torch.testing.assert_close(oo[:,:9],no[:,:9],atol=1e-6,rtol=0)
    torch.testing.assert_close(oo[:,10:],no[:,10:],atol=1e-6,rtol=0)
    torch.testing.assert_close(no[:,9],torch.full((2,),cfg.target_speed,device='cuda'))
    torch.testing.assert_close(ot,nt);torch.testing.assert_close(ou,nu)
    torch.testing.assert_close(nm['reward/foot_slip'],om['reward/foot_slip']*(cfg.slip_penalty_weight/2.))
    for i,cost in enumerate(nm['slip_cost'].cpu().tolist()):
        expected=slip_penalty(cost,weight=cfg.slip_penalty_weight)
        torch.testing.assert_close(nm['reward/foot_slip'][i],torch.tensor(expected,device='cuda'),atol=2e-6,rtol=1e-5)
        slip_seen |= cost>0
    changed=('reward/tracking','reward/progress','reward/foot_slip')
    for key in om:
        if key.startswith('reward/') and key not in changed:
            torch.testing.assert_close(om[key],nm[key],atol=1e-6,rtol=1e-5)
    expected_delta=sum(nm[k]-om[k] for k in changed)
    torch.testing.assert_close(nr-orr,expected_delta,atol=2e-6,rtol=1e-4)
assert slip_seen
# Check that the new configured coefficients did not introduce hot-loop host reads.
originals={name:getattr(torch.Tensor,name) for name in ('cpu','numpy','item','tolist','__bool__','__float__','__int__')}
def forbidden(*args,**kwargs):raise AssertionError('GPU task copied a tensor to the host')
try:
    for name in originals:setattr(torch.Tensor,name,forbidden)
    new_runner.step(torch.zeros((2,12),device='cuda'))
finally:
    for name,value in originals.items():setattr(torch.Tensor,name,value)
print(json.dumps({'status':'configured_command_and_rewards_verified_on_gpu','frames':40,
    'target_speed':cfg.target_speed,'slip_weight':cfg.slip_penalty_weight,
    'tracking_weight':cfg.tracking_reward_weight,'note':'Validates this change, not broad CPU/GPU trajectory equivalence.'},indent=2))
