"""Offline small-motion preview from trusted policy weights. No hardware I/O."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import torch
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv,VecNormalize
from joint_mapping import KNEE_MODEL_TO_SERVO_SIGN

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'simulation'/'rl'))
from env import DogWalkEnv,WalkConfig


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint',type=Path,required=True)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,default=ROOT/'runs'/'sim2real-preview')
    p.add_argument('--calibration',type=Path,help='New checked rear-left manual capture, preserving legacy files')
    p.add_argument('--max-degrees',type=float,choices=(3.,5.),default=3.)
    p.add_argument('--slowdown',type=float,choices=(2.,3.),default=2.)
    p.add_argument('--full-amplitude',action='store_true',help='Retain simulated rear-left amplitudes; automatically slow to the test speed limit')
    p.add_argument('--speed-ticks-per-second',type=int,choices=(60,120),default=60)
    args=p.parse_args()
    torch.set_num_threads(2)
    cfg=WalkConfig(**json.loads((args.checkpoint/'environment.json').read_text())['task'])
    robot=DogWalkEnv(cfg,model_path=args.source/'robot_dog_v2.xml')
    vec=DummyVecEnv([lambda:robot])
    norm=VecNormalize.load(str(args.checkpoint/'normalize.pkl'),vec)
    norm.training=False;norm.norm_reward=False
    policy=PPO.load(args.checkpoint/'policy.zip',device='cpu')
    obs=norm.reset()
    targets=[]
    try:
        for frame in range(round(2*cfg.gait_cycle_seconds/cfg.control_dt)):
            action,_=policy.predict(obs,deterministic=True)
            obs,_,done,_=norm.step(action)
            if done[0]:raise RuntimeError('Source simulation terminated before preview cycle completed')
            if frame>=round(cfg.gait_cycle_seconds/cfg.control_dt):targets.append(robot.targets.copy())
        indexes=[robot.names.index('rear_left_hip_pitch'),robot.names.index('rear_left_knee_pitch')]
        original=np.rad2deg(np.array(targets)[:,indexes])
        # One common scale preserves the paired shape; maximum excursion 3 deg.
        scale=1. if args.full_amplitude else min(1.,args.max_degrees/float(np.abs(original).max()))
        shape=original*scale
        # Smooth lead-in/out from the physical neutral, then slow one cycle 2x.
        lead=np.linspace(0,1,41)[:,None];lead=lead*lead*(3-2*lead)
        degrees=np.concatenate((lead*shape[0],shape,(1-lead)*shape[-1]))
        dt=args.slowdown*cfg.control_dt
        neutral=json.loads((ROOT/'hardware'/'physical_neutral_pose.json').read_text())['positions']
        records=json.loads((ROOT/'hardware'/'manual_range_of_motion.json').read_text())['records']
        if args.calibration:
            capture=json.loads(args.calibration.read_text())
            if capture.get('status') not in ('checked_manual_capture','user_reviewed_capture'):
                raise ValueError('Calibration session is incomplete or unchecked')
            for name,key,sid in [('rear_left_hip_pitch','rear-left-hip-pitch',8),('rear_left_knee_pitch','rear-left-knee',9)]:
                entry=capture['joints'][name]
                if entry['id']!=sid:raise ValueError('Calibration ID mismatch')
                neutral[str(sid)]=entry['neutral_ticks']
                records[key]={'minimum':{'ticks':entry['minimum_ticks']},'maximum':{'ticks':entry['maximum_ticks']}}
        ids=[8,9];signs=[1,KNEE_MODEL_TO_SERVO_SIGN['rear_left']]
        ticks=np.array([int(neutral[str(s)]) for s in ids])+np.rint(degrees*np.array(signs)*4096/360).astype(int)
        if args.full_amplitude:
            dt=max(dt,float(np.abs(np.diff(ticks,axis=0)).max())/args.speed_ticks_per_second*1.2)
            original_times=np.arange(len(degrees))*dt
            times=np.linspace(0,original_times[-1],int(np.ceil(original_times[-1]/.05))+1)
            degrees=np.column_stack([np.interp(times,original_times,degrees[:,i]) for i in (0,1)])
            dt=float(times[1]-times[0])
            ticks=np.array([int(neutral[str(s)]) for s in ids])+np.rint(degrees*np.array(signs)*4096/360).astype(int)
        checks=[]
        for column,(sid,key) in enumerate(zip(ids,['rear-left-hip-pitch','rear-left-knee'])):
            old=records[key];low=old['minimum']['ticks']+25;high=old['maximum']['ticks']-25
            checks.append({'id':sid,'neutral_ticks':neutral[str(sid)],
                'planned_ticks':[int(ticks[:,column].min()),int(ticks[:,column].max())],
                'recorded_safe_ticks_with_margin':[low,high],
                'inside_recorded_limits':bool(np.all((ticks[:,column]>=low)&(ticks[:,column]<=high)))})
        args.output.mkdir(parents=True,exist_ok=True)
        np.savetxt(args.output/'rear-left-small-preview.csv',
            np.column_stack((np.arange(len(ticks))*dt,degrees,ticks)),delimiter=',',
            header='time_s,hip_model_deg,knee_model_deg,hip_id8_ticks,knee_id9_ticks',comments='')
        report={'mode':'OFFLINE PREVIEW ONLY — no serial port opened',
            'policy_sha256':hashlib.sha256((args.checkpoint/'policy.zip').read_bytes()).hexdigest(),
            'source_checkpoint':str(args.checkpoint.resolve()),'task':asdict(cfg),
            'leg':'rear_left','controlled_ids':ids,'hip_roll':'not commanded',
            'calibration_file':str(args.calibration.resolve()) if args.calibration else 'legacy manual ranges',
            'maximum_model_excursion_degrees':float(np.abs(degrees).max()),'amplitude_scale':scale,
            'full_amplitude_supported_rear_left':args.full_amplitude,
            'profile_speed_ticks_per_second':args.speed_ticks_per_second,
            'profile_acceleration':20 if args.speed_ticks_per_second==120 else 10,
            'duration_seconds':dt*(len(ticks)-1),'checks':checks,
            'within_recorded_limits':all(x['inside_recorded_limits'] for x in checks),
            'ready_for_powered_replay':False,
            'remaining_preflight':'Live starting pose, mode/torque, temperature, support and operator start still required; bounds alone do not authorize motion.',
            'note':'Scaled/slowed sample of simulated policy targets; not closed-loop policy deployment. Bounds must agree with current calibration.'}
        (args.output/'report.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:norm.close()


if __name__=='__main__':main()
