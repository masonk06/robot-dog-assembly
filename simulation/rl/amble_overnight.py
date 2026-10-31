"""Continue a walking policy through gradual lateral phase changes on HPC."""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time

STAGES = [(.22, .72, 0., .50), (.18, .68, 0., .50),
          (.15, .65, 0., .50), (.12, .62, 0., .50)]
SLOTS = 8
SLOT_SECONDS = 80 * 60


def quality(report):
    trials = report.get('per_episode', [])
    return (len(trials) == 5 and all(
        t['seconds'] >= 59.9 and not t['fallen'] and not t['sliding']
        and all(t['steps'].get(leg, 0) >= 15 for leg in
                ('front_left', 'front_right', 'rear_left', 'rear_right'))
        and math.isfinite(t['net_speed_m_s']) and t['net_speed_m_s'] >= .01
        and math.isfinite(t['slip_cost']) and t['slip_cost'] < .0006
        for t in trials))


def stage_source(original, destination, offsets):
    shutil.copytree(original, destination, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    cpu = destination / 'env.py'
    gpu = destination / 'cuda_task.py'
    s = cpu.read_text()
    old = 'SWING_OFFSETS = np.array([.25, .75, 0., .5])'
    if old not in s: raise ValueError('Unexpected CPU gait source; no change made')
    cpu.write_text(s.replace(old, f'SWING_OFFSETS = np.array({list(offsets)!r})', 1))
    s = gpu.read_text()
    old = 'self.offsets = tensor([.25,.75,0.,.5])'
    if old not in s: raise ValueError('Unexpected CUDA gait source; no change made')
    gpu.write_text(s.replace(old, f'self.offsets = tensor({list(offsets)!r})', 1))


def run(command, log, timeout):
    print('Running:', ' '.join(map(str, command)), flush=True)
    with log.open('w') as stream:
        process = subprocess.Popen(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
        try:
            result = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: result = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait(); raise RuntimeError(f'Timeout: {log}')
    if result: raise RuntimeError(f'Process exited {result}; see {log}')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, default=Path('baseline-checkpoint'))
    p.add_argument('--source', type=Path, default=Path('baseline-source'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--mode', choices=('online', 'offline', 'disabled'), default='online')
    p.add_argument('--smoke', action='store_true')
    args = p.parse_args()
    root = args.output / time.strftime('%Y%m%d-%H%M%S')
    root.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic() + (600 if args.smoke else 11 * 3600 + 20 * 60)
    original_source = args.source.resolve()
    current = args.checkpoint.resolve()
    records = []
    stage = 0
    for slot in range(2 if args.smoke else SLOTS):
        if deadline - time.monotonic() < 300: break
        source = root / f'source-stage-{slot+1}'
        stage_source(original_source, source, STAGES[stage])
        output = root / f'slot-{slot+1}'
        seconds = 2 if args.smoke else min(SLOT_SECONDS, deadline - time.monotonic() - 240)
        cmd = [sys.executable, '-u', source / 'train_cuda.py', '--resume', current,
               '--source', source, '--envs', 4 if args.smoke else 64,
               '--rollout', 8 if args.smoke else 128, '--minibatch', 32 if args.smoke else 256,
               '--epochs', 1 if args.smoke else 5, '--steps', 32 if args.smoke else 100000000,
               '--max-seconds', seconds, '--save-every', 1000000,
               '--eval-episodes', 2 if args.smoke else 5, '--eval-seconds', .2 if args.smoke else 60,
               '--mode', args.mode, '--output', output]
        run(cmd, root / f'slot-{slot+1}.log', seconds + 180)
        candidates = []
        for evaluation in output.glob('*/*/evaluation.json'):
            report = json.loads(evaluation.read_text())
            if args.smoke or quality(report): candidates.append((report['eval/net_speed_m_s'], evaluation.parent, report))
        if candidates:
            speed, current, report = max(candidates, key=lambda item: item[0])
            records.append({'slot': slot+1, 'stage': stage+1, 'offsets': STAGES[stage],
                            'checkpoint': str(current), 'speed_m_s': speed, 'accepted': True})
            stage = min(stage + 1, len(STAGES)-1)
        else:
            records.append({'slot': slot+1, 'stage': stage+1, 'offsets': STAGES[stage], 'accepted': False})
        (root / 'progress.json').write_text(json.dumps(records, indent=2))
        print(json.dumps(records[-1]), flush=True)
    summary = {'status': 'pipeline_smoke_only' if args.smoke else 'training_complete',
               'best_checkpoint': str(current), 'accepted_stages': records,
               'note': 'A changed gait is not validated for real hardware.'}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2))
    import wandb
    try:
        run_w = wandb.init(project='robot-dog-rl', entity='marsdenm-oregon-state-university',
                           mode=args.mode, name='amble-overnight-summary', job_type='evaluation')
        artifact = wandb.Artifact('robodog-amble-' + run_w.id, type='model', metadata=summary)
        artifact.add_file(str(root / 'summary.json'))
        artifact.add_dir(str(current), name='checkpoint')
        selected_source = current.parent / 'source' if current != args.checkpoint.resolve() else original_source
        artifact.add_dir(str(selected_source), name='source')
        run_w.log_artifact(artifact); run_w.finish()
    except Exception as error:
        print('Summary upload failed; preserve local files:', error, flush=True)
    print('Results:', root, flush=True)


if __name__ == '__main__': main()
