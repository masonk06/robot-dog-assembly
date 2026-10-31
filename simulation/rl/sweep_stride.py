"""Screen reference strides with frozen weights; preserve the best acceptable gait."""
import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
import wandb
from env import DogWalkEnv, WalkConfig


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-mm',type=float,default=60)
    p.add_argument('--mode',choices=['online','offline','disabled'],default='online')
    args=p.parse_args()
    manifest=json.loads((args.checkpoint/'environment.json').read_text())
    cfg=WalkConfig(**manifest['task'])
    baseline_mm=cfg.reference_stride*1000
    if not math.isfinite(args.max_mm) or args.max_mm<=baseline_mm:p.error('max-mm must exceed the starting stride')
    args.output.mkdir(parents=True,exist_ok=True)
    if (args.output/'summary.json').exists():p.error('Use a new output directory; preserve the preceding sweep')
    run=wandb.init(project='robot-dog-rl',entity='marsdenm-oregon-state-university',
        settings=wandb.Settings(base_url='https://api.forge.coreweave.com'),mode=args.mode,
        name='stride-sweep-frozen-weights',job_type='evaluation',tags=['stride-sweep','frozen-weights'],
        config={'starting_stride_mm':baseline_mm,'increment_mm':1,'seconds':60,'screening_worlds':3,
                'screening_seed':10000,'validation_worlds':5,'validation_seed':20000,
                'minimum_speed_gain_fraction':.005,'maximum_slip_ratio':1.25,
                'maximum_force_ratio':1.2,'maximum_landing_ratio':1.2,
                'new_training_steps':0,'task':vars(cfg),
                'policy_sha256':hashlib.sha256((args.checkpoint/'policy.zip').read_bytes()).hexdigest()})
    records=[]

    def evaluate_mm(mm,seed=10000,worlds=3,label=None):
        # The CUDA IK clips its acos input. Check the same geometry with the CPU
        # reference first, which rejects unreachable targets and joint-limit violations.
        probe=DogWalkEnv(replace(cfg,reference_stride=mm/1000),model_path=args.source/'robot_dog_v2.xml')
        try:
            probe.reset(seed=seed)
            for phase in np.linspace(0,1,601):
                probe.data.time=cfg.gait_cycle_seconds*(1+phase)
                probe.reference()
        finally:probe.close()
        label=label or f'stride-{mm:g}mm'
        output=args.output/f'{label}.json'
        command=[sys.executable,'-u',str(Path(__file__).with_name('evaluate_cuda.py')),
                 str(args.checkpoint),'--source',str(args.source),'--stride-m',str(mm/1000),
                 '--seconds','60','--episodes',str(worlds),'--seed',str(seed),'--output',str(output)]
        with (args.output/f'{label}.log').open('w') as stream:
            subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=600)
        return json.loads(output.read_text())

    def quality(report,baseline):
        reasons=[]
        if any(not math.isfinite(v) for k,v in report.items() if k.startswith('eval/') and isinstance(v,(int,float))):
            reasons.append('nonfinite metrics')
        for t in report['per_episode']:
            if t['seconds']<59.9 or t['fallen'] or t['sliding']:reasons.append('fall, slide reset or early ending')
            if min(t['steps'].values())<math.floor(60/cfg.gait_cycle_seconds)-2:reasons.append('unused leg')
        for key,ratio in [('foot_slip_m2_s2',1.25),('peak_foot_force_n',1.2),('peak_landing_speed_m_s',1.2)]:
            if report[f'eval/{key}']>baseline[f'eval/{key}']*ratio:reasons.append(f'{key} exceeds comparison budget')
        return sorted(set(reasons))

    def record(mm,report,reasons,phase='screen'):
        row={'stride_mm':mm,'phase':phase,'net_speed_cm_s':report['eval/net_speed_m_s']*100,
             'slip':report['eval/foot_slip_m2_s2'],'peak_force_n':report['eval/peak_foot_force_n'],
             'peak_landing_m_s':report['eval/peak_landing_speed_m_s'],'rejection_reasons':reasons}
        records.append(row)
        run.log({f'sweep/{k}':v for k,v in row.items() if isinstance(v,(int,float))})
        print(json.dumps(row),flush=True)
        (args.output/'progress.json').write_text(json.dumps(records,indent=2))

    try:
        baseline=evaluate_mm(baseline_mm,label='baseline-screen')
        reasons=quality(baseline,baseline)
        if reasons:raise RuntimeError(f'Starting gait failed: {reasons}')
        record(baseline_mm,baseline,[])
        accepted=[(baseline_mm,baseline)]
        best_mm,best=accepted[-1]
        stop_reason='search bound reached; peak not established'
        mm=math.floor(baseline_mm)+1
        while mm<=args.max_mm:
            try:report=evaluate_mm(mm)
            except (ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
                stop_reason=f'candidate failed at {mm:g} mm: {error}'
                print(stop_reason,flush=True)
                break
            reasons=quality(report,baseline)
            gain=report['eval/net_speed_m_s']/best['eval/net_speed_m_s']-1
            if gain<.005:reasons.append('less than 0.5% additional speed')
            record(mm,report,reasons)
            if reasons:
                stop_reason=f'stopped at {mm:g} mm: '+', '.join(reasons)
                # Check one midpoint before the rejected setting, preserving originals.
                midpoint=(best_mm+mm)/2
                if midpoint-best_mm>=.25:
                    try:
                        half=evaluate_mm(midpoint)
                        half_reasons=quality(half,baseline)
                        if half['eval/net_speed_m_s']/best['eval/net_speed_m_s']-1<.005:
                            half_reasons.append('less than 0.5% additional speed')
                        record(midpoint,half,half_reasons,'refine')
                        if not half_reasons:
                            accepted.append((midpoint,half));best_mm,best=accepted[-1]
                    except (ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired):pass
                break
            accepted.append((mm,report));best_mm,best=accepted[-1]
            mm+=1

        held_baseline=evaluate_mm(baseline_mm,20000,5,'baseline-validation')
        while True:
            held=evaluate_mm(best_mm,20000,5,f'validation-{best_mm:g}mm')
            reasons=quality(held,held_baseline)
            if best_mm!=baseline_mm and held['eval/net_speed_m_s']<held_baseline['eval/net_speed_m_s']*1.005:
                reasons.append('no meaningful held-out speed gain')
            record(best_mm,held,reasons,'validation')
            if not reasons:break
            accepted.pop()
            if not accepted:raise RuntimeError('No candidate passed validation')
            best_mm,best=accepted[-1]

        saved=args.output/'best';source=args.output/'source'
        shutil.copytree(args.checkpoint,saved,dirs_exist_ok=True)
        shutil.copytree(args.source,source,dirs_exist_ok=True)
        metadata={**manifest,'task':vars(replace(cfg,reference_stride=best_mm/1000)),
                  'additional_steps':0,'adaptation':'stride_sweep_frozen_weights',
                  'evaluation_episodes':5,'evaluation_seconds_override':60}
        for folder in (saved,source):
            (folder/'environment.json').write_text(json.dumps(metadata,indent=2))
        (saved/'evaluation.json').write_text(json.dumps(held,indent=2))
        (saved/'source.json').write_text(json.dumps({'path':str(source.resolve()),
            'wandb_source_artifact':f'{run.entity}/{run.project}/robodog-source-{run.id}:source'},indent=2))
        for name in ('evaluate_cuda.py','train_cuda.py','sweep_stride.py'):
            shutil.copy2(Path(__file__).with_name(name),source/name)
        summary={'best_stride_mm':best_mm,'stop_reason':stop_reason,'records':records,
                 'wandb_url':run.url,'new_training_steps':0}
        (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
        run.summary.update({'best_stride_mm':best_mm,'stop_reason':stop_reason,
                            **{k:v for k,v in held.items() if k.startswith('eval/')}})
        for folder,name,kind,aliases in [(saved,'policy','model',['latest','best']),
                (source,'source','dataset',['latest','source']),
                (args.output,'sweep-results','evaluation',['latest'])]:
            artifact=wandb.Artifact(f'robodog-{name}-{run.id}',type=kind)
            artifact.add_dir(str(folder));run.log_artifact(artifact,aliases=aliases)
        print(json.dumps(summary),flush=True)
    finally:run.finish()


if __name__=='__main__':main()
