"""Short CPU/GPU physics and contact-metric parity gate."""
import argparse
import json
import numpy as np
from env import DogWalkEnv, WalkConfig
from newton_env import NewtonDogEnv

p = argparse.ArgumentParser()
p.add_argument('--source',required=True)
p.add_argument('--frames',type=int,default=30)
a = p.parse_args()
from pathlib import Path
cfg = WalkConfig(reset_noise=0)
cpu = DogWalkEnv(cfg,model_path=Path(a.source)/'robot_dog_v2.xml')
gpu = NewtonDogEnv(cfg,model_path=Path(a.source)/'robot_dog_v2.xml')
cpu.reset(seed=1)
gpu.reset(seed=1)
errors,forces,slips = [],[],[]
try:
    for _ in range(a.frames):
        _,_,cd,ct,ci = cpu.step(np.zeros(12))
        _,_,gd,gt,gi = gpu.step(np.zeros(12))
        errors.append(np.max(np.abs(cpu.data.qpos-gpu.data.qpos)))
        forces.append([ci['peak_foot_force_n'],gi['peak_foot_force_n']])
        slips.append([ci['foot_slip_m2_s2'],gi['foot_slip_m2_s2']])
        assert (cd,ct)==(gd,gt), 'Termination mismatch'
    assert max(errors)<.005, 'State divergence exceeds parity gate'
    np.testing.assert_allclose(np.array(forces)[:,0],np.array(forces)[:,1],atol=.5,rtol=.1)
    result={'frames':a.frames,'max_qpos_difference':float(max(errors)),
            'max_normal_force_difference_n':float(np.max(np.abs(np.diff(forces,axis=1)))),
            'max_slip_cost_difference':float(np.max(np.abs(np.diff(slips,axis=1)))),
            'status':'short_contact_parity_passed'}
    print(json.dumps(result,indent=2))
finally:
    cpu.close()
    gpu.close()
