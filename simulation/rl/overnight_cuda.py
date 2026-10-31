"""Bounded, checkpoint-preserving CUDA curriculum toward 0.02 m/s."""
import argparse
from dataclasses import replace
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


STAGES = [
    dict(target_speed=.0125, reference_stride=.034, gait_cycle_seconds=3.0),
    dict(target_speed=.0150, reference_stride=.038, gait_cycle_seconds=2.9),
    dict(target_speed=.0175, reference_stride=.043, gait_cycle_seconds=2.75),
    dict(target_speed=.0200, reference_stride=.048, gait_cycle_seconds=2.6),
]
MINUTES = [35, 50, 60, 75]  # 220 training minutes; 10 minutes reserved for overhead.
LIMITS = dict(foot_slip_m2_s2=2.0, peak_foot_force_n=1.5,
              peak_landing_speed_m_s=1.5)


def quality(report, baseline, seconds=60):
    """Experimental comparison budgets, not hardware safety limits."""
    reasons = []
    trials = report.get('per_episode', [])
    if not trials or len(trials) != report.get('episodes'):
        reasons.append('missing individual trials')
    for key in ['net_speed_m_s', *LIMITS]:
        value = report.get('eval/' + key)
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            reasons.append('nonfinite or missing ' + key)
    cycle = report.get('gait_cycle_seconds', 3.)
    minimum_steps = max(1, math.floor(seconds / cycle) - 2)
    for trial in trials:
        numeric = [trial.get(k, float('nan')) for k in
                   ('seconds', 'fallen', 'sliding', 'slip_cost', 'peak_force_n',
                    'peak_landing_m_s', 'net_speed_m_s')]
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in numeric):
            reasons.append('invalid individual trial')
            continue
        if trial['seconds'] < seconds - .1 or trial['fallen'] or trial['sliding']:
            reasons.append('fall, severe sliding, or early ending')
        counts = trial.get('steps', {})
        if len(counts) != 4 or any(not math.isfinite(v) or v < minimum_steps for v in counts.values()):
            reasons.append('insufficient steps from every leg')
        for field, key in [('slip_cost', 'foot_slip_m2_s2'),
                           ('peak_force_n', 'peak_foot_force_n'),
                           ('peak_landing_m_s', 'peak_landing_speed_m_s')]:
            if trial[field] > baseline['eval/' + key] * LIMITS[key]:
                reasons.append(key + ' exceeds comparison budget')
        if trial['net_speed_m_s'] < baseline['eval/net_speed_m_s'] * .95:
            reasons.append('slower than 95% of original baseline')
    return sorted(set(reasons))


def eligible_to_advance(report, command):
    # Require every trial to reach 80% of this stage's command before increasing it.
    return all(t['net_speed_m_s'] >= .8 * command for t in report['per_episode'])


def goal_reached(report, reasons):
    return not reasons and all(t['net_speed_m_s'] >= .02 for t in report['per_episode'])


def copy_pair(checkpoint, source, destination):
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(checkpoint, destination / 'checkpoint')
    shutil.copytree(source, destination / 'source')
    (destination / 'checkpoint' / 'source.json').write_text(json.dumps(
        {'path': str((destination / 'source').resolve())}, indent=2))


def publish_summary(root, summary, plan, mode):
    import wandb
    run = wandb.init(project='robot-dog-rl', entity='marsdenm-oregon-state-university',
                     settings=wandb.Settings(base_url='https://api.forge.coreweave.com'),
                     mode=mode, name='overnight-2cms-summary', job_type='evaluation',
                     tags=['overnight', 'continuation'], config=plan)
    try:
        run.log({key: value for key, value in summary.items()
                 if isinstance(value, (int, float, bool))})
        artifact = wandb.Artifact('robodog-overnight-' + run.id, type='model', metadata=summary)
        for name in ('plan.json', 'baseline.json', 'selection.json', 'heldout.json', 'summary.json'):
            if (root / name).exists():
                artifact.add_file(str(root / name), name=name)
        artifact.add_dir(str(root / 'best'), name='best')
        run.log_artifact(artifact, aliases=['latest'])
    finally:
        run.finish()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, default=Path('overnight-checkpoint'))
    p.add_argument('--source', type=Path, default=Path('overnight-source'))
    p.add_argument('--output', type=Path, default=Path('runs/overnight-2cms'))
    p.add_argument('--mode', choices=['online', 'offline', 'disabled'], default='online')
    p.add_argument('--smoke', action='store_true', help='Two tiny stages; pipeline only, no walking claim')
    args = p.parse_args()
    script = Path(__file__).resolve().parent
    root = args.output / time.strftime('%Y%m%d-%H%M%S')
    root.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic() + (600 if args.smoke else 230 * 60)
    stop = False
    child = None

    def request_stop(signum, frame):
        nonlocal stop
        stop = True
        if child is not None and child.poll() is None:
            child.terminate()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    def execute(command, log, allowance):
        nonlocal child
        print('Running: ' + ' '.join(map(str, command)), flush=True)
        with log.open('w') as stream:
            child = subprocess.Popen(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT)
            try:
                code = child.wait(timeout=max(1, min(allowance, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                child.terminate()  # Trainer saves at the next rollout boundary.
                try:
                    code = child.wait(timeout=120)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
                    raise RuntimeError('Child exceeded its shutdown allowance; prior checkpoints preserved')
            finally:
                child = None
        if code:
            raise RuntimeError(f'Process exited {code}; see {log}')

    def evaluate(checkpoint, source, label, seed=10000):
        output = root / (label + '.json')
        execute([sys.executable, '-u', script / 'evaluate_cuda.py', checkpoint,
                 '--source', source, '--episodes', 2 if args.smoke else 5,
                 '--seconds', .2 if args.smoke else 60, '--seed', seed,
                 '--output', output], root / (label + '.log'), 300)
        return json.loads(output.read_text())

    copy_pair(args.checkpoint, args.source, root / 'original')
    baseline = evaluate(args.checkpoint, args.source, 'baseline')
    baseline_reasons = [] if args.smoke else quality(baseline, baseline)
    if baseline_reasons:
        raise RuntimeError('Original baseline failed: ' + ', '.join(baseline_reasons))
    best_checkpoint, best_source, best_report = args.checkpoint, args.source, baseline
    records = []
    plan = {'initial_checkpoint': str(args.checkpoint.resolve()), 'stages': STAGES,
            'minutes': MINUTES, 'tracking_weight': 1.375, 'slip_weight': 2.2,
            'comparison_limits_relative_to_original': LIMITS, 'wall_budget_minutes': 230,
            'smoke_only': args.smoke}
    (root / 'plan.json').write_text(json.dumps(plan, indent=2))
    stage_index = 0
    for slot, minutes in enumerate(MINUTES[:2] if args.smoke else MINUTES):
        if stop or deadline - time.monotonic() < 180:
            break
        stage = STAGES[stage_index]
        # GPU IK clamps unreachable points. Reject them with the CPU reference first.
        import numpy as np
        from env import WalkConfig, DogWalkEnv
        cfg = WalkConfig(**json.loads((best_checkpoint / 'environment.json').read_text())['task'])
        cfg = replace(cfg, **stage, tracking_reward_weight=1.375, slip_penalty_weight=2.2)
        probe = DogWalkEnv(cfg, model_path=best_source / 'robot_dog_v2.xml')
        try:
            probe.reset(seed=42)
            for phase in np.linspace(0, 1, 601):
                probe.data.time = cfg.gait_cycle_seconds * (1 + phase)
                probe.reference()
        finally:
            probe.close()
        output = root / f'slot-{slot + 1}-stage-{stage_index + 1}'
        allowance = min(minutes * 60, deadline - time.monotonic() - 180)
        command = [sys.executable, '-u', script / 'train_cuda.py', '--resume', best_checkpoint,
                   '--source', best_source, '--target-speed', cfg.target_speed,
                   '--stride-m', cfg.reference_stride, '--cycle-seconds', cfg.gait_cycle_seconds,
                   '--tracking-weight', 1.375, '--slip-weight', 2.2, '--envs', 4 if args.smoke else 64,
                   '--rollout', 8 if args.smoke else 128, '--minibatch', 32 if args.smoke else 256,
                   '--epochs', 1 if args.smoke else 5, '--steps', 32 if args.smoke else 100000000,
                   '--max-seconds', 2 if args.smoke else allowance,
                   '--save-every', 1000000, '--eval-episodes', 2 if args.smoke else 5,
                   '--eval-seconds', .2 if args.smoke else 60, '--mode', args.mode, '--output', output]
        execute(command, root / f'slot-{slot + 1}.log', allowance + 120)
        candidates = []
        for path in output.glob('*/*/evaluation.json'):
            report = json.loads(path.read_text())
            reasons = [] if args.smoke else quality(report, baseline)
            records.append({'checkpoint': str(path.parent), 'stage': stage_index + 1,
                            'net_speed_m_s': report.get('eval/net_speed_m_s'),
                            'rejection_reasons': reasons})
            if not reasons:
                candidates.append((report['eval/net_speed_m_s'], path.parent, report))
        selected = max(candidates, key=lambda item: item[0]) if candidates else None
        if selected and (args.smoke or selected[0] >= best_report['eval/net_speed_m_s']):
            _, best_checkpoint, best_report = selected
            best_source = best_checkpoint.parent / 'source'
            copy_pair(best_checkpoint, best_source, root / f'accepted-slot-{slot + 1}')
            if args.smoke or eligible_to_advance(best_report, cfg.target_speed):
                stage_index = min(stage_index + 1, len(STAGES) - 1)
        print(f'Slot {slot + 1}: best {best_report["eval/net_speed_m_s"] * 100:.3f} cm/s; '
              f'next stage {stage_index + 1}', flush=True)
        (root / 'selection.json').write_text(json.dumps(records, indent=2))
    copy_pair(best_checkpoint, best_source, root / 'best')
    heldout = None
    if not stop and deadline - time.monotonic() > 60:
        heldout = evaluate(root / 'best' / 'checkpoint', root / 'best' / 'source',
                           'heldout', seed=20000)
    reasons = quality(heldout, baseline) if heldout and not args.smoke else ['held-out validation not completed']
    summary = {'status': 'pipeline_smoke_only' if args.smoke else 'training_complete',
               'stop_requested': stop, 'best_checkpoint': str((root / 'best' / 'checkpoint').resolve()),
               'initial_speed_cm_s': baseline['eval/net_speed_m_s'] * 100,
               'selected_speed_cm_s': best_report['eval/net_speed_m_s'] * 100,
               'heldout_speed_cm_s': heldout['eval/net_speed_m_s'] * 100 if heldout else None,
               'heldout_rejection_reasons': reasons,
               'goal_2cms_met': bool(heldout and not args.smoke and goal_reached(heldout, reasons))}
    (root / 'summary.json').write_text(json.dumps(summary, indent=2))
    try:
        publish_summary(root, summary, plan, args.mode)
    except Exception as error:
        summary['summary_upload_error'] = str(error)
        (root / 'summary.json').write_text(json.dumps(summary, indent=2))
        print('Summary upload failed; preserve local results: ' + str(error), flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    print('Overnight results: ' + str(root.resolve()), flush=True)


if __name__ == '__main__':
    main()
