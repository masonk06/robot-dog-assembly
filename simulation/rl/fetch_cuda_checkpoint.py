"""Fetch an immutable policy/source artifact pair; preserve existing checkpoints."""
import argparse
import json
from pathlib import Path
import wandb

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--run',default='1f0ethf8')
p.add_argument('--root',type=Path,default=Path('cuda-inputs'))
p.add_argument('--pointer',type=Path,default=Path('cuda-start.json'))
a=p.parse_args()
api=wandb.Api()
prefix='marsdenm-oregon-state-university/robot-dog-rl'
run=api.run(f'{prefix}/{a.run}')
if run.state=='running':
    raise SystemExit(f'Run {a.run} is still marked running. Let the current HPC training finish before launching the CUDA continuation.')
policy=api.artifact(f'{prefix}/robodog-policy-{a.run}:latest')
source=api.artifact(f'{prefix}/robodog-source-{a.run}:source')
folder=a.root/f'{a.run}-{policy.version}'
cp=Path(policy.download(root=str(folder/'checkpoint'))).resolve()
src=Path(source.download(root=str(folder/'source'))).resolve()
record={'run':a.run,'policy_artifact':f'{prefix}/robodog-policy-{a.run}:{policy.version}',
        'source_artifact':f'{prefix}/robodog-source-{a.run}:{source.version}',
        'checkpoint':str(cp),'source':str(src),'timesteps':policy.metadata.get('timesteps')}
a.pointer.write_text(json.dumps(record,indent=2))
print(json.dumps(record,indent=2))
