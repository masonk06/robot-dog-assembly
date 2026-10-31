"""Prepare an offline tick trajectory; never opens a serial port or commands motors."""
import argparse
import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def prepare(trajectory, zeros, directions, limits, clamp=False, margin=0):
    with trajectory.open(newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError('Empty trajectory')
    out = []
    previous = -1.0
    for row in rows:
        t = float(row['time_seconds'])
        if not math.isfinite(t) or t <= previous:
            raise ValueError('Trajectory times must be finite and increasing')
        previous = t
        converted = {'time_seconds': t}
        for name, zero in zeros['joints'].items():
            sid = zero['id']
            sign = directions['joints'][name].get('model_to_encoder_sign')
            bounds = limits.get(name)
            if sign not in (-1, 1) or not bounds or bounds.get('id') != sid:
                raise ValueError(f'{name} ID {sid}: missing direction or current-frame limits')
            low, high = bounds['minimum_ticks'] + margin, bounds['maximum_ticks'] - margin
            if not (0 <= low < high <= 4095):
                raise ValueError(f'{name}: invalid non-wrapping limits')
            angle = float(row[name])
            if not math.isfinite(angle):
                raise ValueError(f'{name}: nonfinite angle')
            ticks = round(zero['neutral_ticks'] + sign * angle * 4096 / (2 * math.pi))
            if not low <= ticks <= high:
                if not clamp:
                    raise ValueError(f'{name} ID {sid}: target {ticks} outside {low}..{high}')
                ticks = max(low, min(high, ticks))
            converted[str(sid)] = ticks
        out.append(converted)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('trajectory', type=Path)
    p.add_argument('--limits', type=Path, required=True, help='Reviewed current-frame bounds JSON, keyed by joint name')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--clamp', action='store_true', help='Create an offline preview by clipping targets; not validated for physical replay')
    p.add_argument('--margin', type=int, default=0)
    args = p.parse_args()
    zeros = json.loads((ROOT / 'hardware/calibrations/zero-points-current.json').read_text())
    directions = json.loads((ROOT / 'hardware/calibrations/manual-physical-directions-20261028.json').read_text())
    limits_file = json.loads(args.limits.read_text())
    limits = limits_file.get('joints', limits_file)
    if args.margin < 0:
        p.error('margin must be nonnegative')
    rows = prepare(args.trajectory, zeros, directions, limits, args.clamp, args.margin)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['time_seconds', *map(str, range(1, 13))])
        writer.writeheader()
        writer.writerows(rows)
    print(f'Prepared {len(rows)} rows for offline review only: {args.output}')


if __name__ == '__main__':
    main()
