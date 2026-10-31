"""Simulation-only staged COM/friction robustness curriculum for Luca.

Each stage copies the source and applies a mass-constant COM/friction variant,
then continues PPO with the separate quasi-static crawl task. Inputs are never
edited and no physical hardware is controlled.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


# Negative X is forward in the CAD/body frame.  These deliberately cover a
# plausible incomplete-prototype range without fitting the temporary chassis.
SCENARIOS = ((0.000, .80, 1.00, 'baseline'), (-.015, .70, 1.15, 'forward-low-friction'),
             (+.015, .90, .85, 'rear-high-friction'), (-.015, .90, .85, 'forward-high-friction'),
             (+.015, .70, 1.15, 'rear-low-friction'))


def write_variant(original, output, com_shift_x, friction):
    tree = ET.parse(original)
    root = tree.getroot()
    base = root.find(".//worldbody/body[@name='base']")
    inertial = None if base is None else base.find('inertial')
    floor = root.find(".//geom[@name='floor']")
    if inertial is None or floor is None:
        raise ValueError('Expected base inertial and floor geometry')
    pos = [float(value) for value in inertial.attrib['pos'].split()]
    pos[0] += com_shift_x
    inertial.set('pos', ' '.join(f'{value:.8g}' for value in pos))
    floor.set('friction', f'{friction:.5g} .01 .001')
    for geom in root.findall('.//geom'):
        if geom.attrib.get('name', '').endswith('_foot_contact_proxy'):
            geom.set('friction', f'{friction:.5g} .01 .001')
    tree.write(output, encoding='utf-8', xml_declaration=True)


def run(command, log, timeout):
    print('Running:', ' '.join(map(str, command)), flush=True)
    with log.open('w', encoding='utf-8') as stream:
        process = subprocess.Popen([str(x) for x in command], stdout=stream,
                                   stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.terminate()
            try: code = process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
                raise RuntimeError(f'Timeout; inspect {log}')
    if code:
        raise RuntimeError(f'Training exited {code}; inspect {log}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--slots', type=int, default=5)
    parser.add_argument('--slot-seconds', type=float, default=3600)
    parser.add_argument('--envs', type=int, default=64)
    parser.add_argument('--mode', choices=('online', 'offline', 'disabled'), default='online')
    args = parser.parse_args()
    if args.slots < 1 or args.envs < 1 or args.slot_seconds <= 60:
        parser.error('slots/envs must be positive and slot-seconds must exceed 60')
    root = args.output / time.strftime('%Y%m%d-%H%M%S')
    root.mkdir(parents=True, exist_ok=False)
    checkpoint, source_base = args.checkpoint.resolve(), args.source.resolve()
    records = []
    for slot in range(args.slots):
        shift, friction, response_scale, label = SCENARIOS[slot % len(SCENARIOS)]
        source = root / f'source-slot-{slot + 1:02d}-{label}'
        shutil.copytree(source_base, source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        write_variant(source / 'robot_dog_v2.xml', source / 'robot_dog_v2.xml', shift, friction)
        metadata = {'slot': slot + 1, 'label': label, 'com_x_shift_m': shift,
                    'friction': friction, 'total_mass_change_kg': 0,
                    'actuator_response_proxy_scale': response_scale,
                    'note': 'COM-only variant; response proxy is provisional; simulation-only.'}
        (source / 'robustness-scenario.json').write_text(json.dumps(metadata, indent=2))
        output = root / f'slot-{slot + 1:02d}'
        command = [sys.executable, '-u', source / 'train_cuda.py', '--resume', checkpoint,
                   '--source', source, '--quasistatic-crawl', '--crawl-response-scale', response_scale, '--envs', args.envs,
                   '--steps', 100000000, '--max-seconds', args.slot_seconds,
                   '--save-every', 1000000, '--eval-episodes', 5, '--eval-seconds', 60,
                   '--mode', args.mode, '--output', output]
        run(command, root / f'slot-{slot + 1:02d}.log', args.slot_seconds + 180)
        evaluations = list(output.glob('*/*/evaluation.json'))
        if not evaluations:
            raise RuntimeError(f'No completed evaluation in {output}')
        checkpoint = max(evaluations,
                         key=lambda path: json.loads(path.read_text()).get('eval/net_speed_m_s', float('-inf'))).parent
        report = json.loads((checkpoint / 'evaluation.json').read_text())
        records.append({**metadata, 'checkpoint': str(checkpoint),
                        'speed_m_s': report.get('eval/net_speed_m_s')})
        (root / 'progress.json').write_text(json.dumps(records, indent=2))
    (root / 'summary.json').write_text(json.dumps({
        'status': 'simulation_only', 'best_checkpoint': str(checkpoint), 'scenarios': records,
        'warning': 'Re-evaluate after measuring final battery/Pi/PDB/chassis mass and placement.'}, indent=2))
    print('Results:', root)


if __name__ == '__main__':
    main()
