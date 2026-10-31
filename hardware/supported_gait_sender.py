"""Prototype supported replay sender. Requires explicit --execute to move motors."""
import argparse
import csv
import json
import math
from pathlib import Path
import sys
import time
from contextlib import contextmanager
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.servo_tools'))
import serial
sys.path.insert(0, str(ROOT / 'hardware/imu'))
from body_axis_view import transform
from tilt_filter import TiltFilter


class TelemetryLog:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open('x', encoding='utf-8')
        self.origin = time.monotonic(); self.last_imu = None; self.filter = TiltFilter()

    def record(self, line):
        now = time.monotonic()
        record = {'host_elapsed_s': now - self.origin, 'raw': line}
        if line.startswith('LIVE,'):
            fields = line.split(',')
            # Receiver revision with load/current telemetry: ID, position,
            # target, voltage (0.1 V), temperature, load (0.1% PWM), current
            # (6.5 mA units), device timestamp.
            if len(fields) == 9:
                try:
                    record.update(servo_id=int(fields[1]), actual_ticks=int(fields[2]),
                                  target_ticks=int(fields[3]), voltage_v=int(fields[4]) / 10,
                                  temperature_c=int(fields[5]), load_tenth_percent=int(fields[6]),
                                  current_ma=int(fields[7]) * 6.5, device_us=int(fields[8]))
                except ValueError as error: record['parse_error'] = str(error)
        if line.startswith('IMU,'):
            fields = line.split(',')
            if len(fields) == 8:
                try:
                    accel, angular, _, _, magnitude = transform([float(v) for v in fields[2:]])
                    dt = .05 if self.last_imu is None else now - self.last_imu
                    if not 0 < dt <= .5: self.filter = TiltFilter(); dt = .05
                    roll, pitch, gravity = self.filter.update(accel, angular, dt)
                    self.last_imu = now
                    record.update(device_us=int(fields[1]), roll_deg=roll, pitch_deg=pitch,
                                  angular_rad_s=angular.tolist(), projected_gravity=gravity.tolist(),
                                  acceleration_magnitude=magnitude)
                except (ValueError, OverflowError) as error: record['parse_error'] = str(error)
        self.file.write(json.dumps(record, allow_nan=False) + '\n'); self.file.flush()

    def close(self): self.file.close()


@contextmanager
def fine_timer():
    """Request 1 ms Windows timer resolution for the duration of playback."""
    timer = None
    if sys.platform == 'win32':
        import ctypes
        dll = ctypes.WinDLL('winmm')
        if dll.timeBeginPeriod(1) == 0: timer = dll
    try: yield
    finally:
        if timer is not None: timer.timeEndPeriod(1)


def load_plan(path, limits_path):
    limits = json.loads(limits_path.read_text())['joints']
    by_id = {v['id']: (v['minimum_ticks'] + 10, v['maximum_ticks'] - 10) for v in limits.values()}
    if set(by_id) != set(range(1, 13)):
        raise ValueError('Expected exactly IDs 1–12')
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows: raise ValueError('Empty plan')
    previous = -1.0
    for row in rows:
        t = float(row['time_seconds'])
        if not math.isfinite(t) or t <= previous: raise ValueError('Invalid timestamp')
        previous = t
        for sid in by_id:
            value = int(row[str(sid)])
            if not by_id[sid][0] <= value <= by_id[sid][1]:
                raise ValueError(f'ID {sid} target outside bounds')
    return rows, by_id


def exchange(port, command, expected, timeout=3.0, telemetry=None):
    port.write((command + '\n').encode('ascii')); port.flush()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        raw = port.readline().decode('ascii', errors='replace').strip()
        if not raw: continue
        if telemetry: telemetry.record(raw)
        if not raw.startswith('LIVE,'): print(raw, flush=True)
        if raw.startswith(('ERR,', 'STOPPED,', 'IMU_ERROR,')):
            raise RuntimeError(raw)
        if raw == expected: return
    raise TimeoutError(f'No acknowledgement for {command}')


def neutral_steps(starts, targets, increment=4):
    """Interpolate from measured positions with bounded per-update changes."""
    count = max(1, math.ceil(max(abs(targets[s] - starts[s]) for s in starts) / increment))
    for i in range(1, count + 1):
        yield {sid: round(starts[sid] + (targets[sid] - starts[sid]) * i / count) for sid in starts}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path, nargs='?')
    p.add_argument('--limits', type=Path, default=ROOT / 'hardware/calibrations/current-frame-limits-20261029.json')
    p.add_argument('--port', default='COM7')
    p.add_argument('--execute', action='store_true', help='Physically enable and move all 12 motors')
    p.add_argument('--neutral', action='store_true', help='Slowly move to saved approximate zero positions')
    p.add_argument('--log-imu', action='store_true', help='Enable and log experimental IMU streaming during replay')
    p.add_argument('--time-scale', type=float, default=1.0, help='Replay duration multiplier, at least 1 (2 means half speed)')
    p.add_argument('--duration', type=float, help='Maximum physical replay duration in seconds; uses the matching initial portion of the plan')
    args = p.parse_args()
    if not math.isfinite(args.time_scale) or args.time_scale < 1:
        p.error('time-scale must be finite and at least 1')
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration <= 0):
        p.error('duration must be a positive finite number')
    limits = json.loads(args.limits.read_text())['joints']
    bounds = {v['id']: (v['minimum_ticks'] + 10, v['maximum_ticks'] - 10) for v in limits.values()}
    if set(bounds) != set(range(1, 13)): raise ValueError('Expected all 12 IDs')
    zeros = json.loads((ROOT / 'hardware/calibrations/zero-points-current.json').read_text())['joints']
    targets = {v['id']: v['neutral_ticks'] for v in zeros.values()}
    if set(targets) != set(bounds) or any(not bounds[s][0] <= targets[s] <= bounds[s][1] for s in bounds):
        raise ValueError('Neutral target outside configured bounds')
    if args.neutral:
        rows = None
        print('Validated 12 saved approximate neutral targets. No hardware connection yet.')
    else:
        if not args.plan: p.error('provide a plan or --neutral')
        rows, bounds = load_plan(args.plan, args.limits)
        if args.duration is not None:
            simulated_duration = args.duration / args.time_scale
            rows = [row for row in rows if float(row['time_seconds']) <= simulated_duration]
            if not rows:
                raise ValueError('Requested duration is shorter than the first plan sample')
        print(f'Validated {len(rows)} samples and 12 configured limits. No hardware connection yet.')
    if not args.execute: return
    # No open-loop catch-up: abort when the host or bus falls behind.
    bus = serial.Serial(port=None, baudrate=115200, timeout=.05, write_timeout=.2)
    bus.dtr = False; bus.rts = False; bus.port = args.port
    telemetry = None
    try:
        bus.open()
        if args.log_imu:
            log_path = ROOT / 'runs/sim2real-hardware' / ('telemetry-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.jsonl')
            telemetry = TelemetryLog(log_path)
            print(f'Telemetry log: {log_path}', flush=True)
            exchange(bus, 'IMUSTREAM', 'OK,IMUSTREAM', telemetry=telemetry)
        for sid, (low, high) in sorted(bounds.items()):
            exchange(bus, f'LIMIT,{sid},{low},{high}', f'OK,LIMIT,{sid}', telemetry=telemetry)
        # ARM emits actual positions; preloading prevents a cached-goal jump.
        bus.write(b'ARM\n'); bus.flush()
        starts = {}; deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            message = bus.readline().decode('ascii', errors='replace').strip()
            if message: print(message, flush=True)
            if message and telemetry: telemetry.record(message)
            if message.startswith('STARTPOS,'):
                _, sid, ticks = message.split(','); starts[int(sid)] = int(ticks)
            elif message == 'ARMED': break
            elif message.startswith(('ERR,', 'STOPPED,')): raise RuntimeError(message)
        else: raise TimeoutError('ARM was not acknowledged')
        if set(starts) != set(bounds): raise RuntimeError('Missing starting position')
        if args.neutral:
            for step in neutral_steps(starts, targets):
                began = time.monotonic()
                for sid in sorted(bounds):
                    value = step[sid]
                    exchange(bus, f'GOAL,{sid},{value}', f'OK,GOAL,{sid},{value}', timeout=.4, telemetry=telemetry)
                while time.monotonic() - began < .25:
                    exchange(bus, 'KEEP', 'OK,KEEP', timeout=.4, telemetry=telemetry)
                    time.sleep(.05)
            print('Neutral targets sent; torque will be released. Confirm final positions separately.')
            return
        if any(abs(starts[sid] - int(rows[0][str(sid)])) > 12 for sid in bounds):
            raise RuntimeError('Starting pose differs from the simulation start; stopped')
        # A frame updates all 12 targets together. Keep simulation timing;
        # slow down rather than skipping frames if the host lags.
        with fine_timer():
            for row in rows:
                began = time.monotonic()
                values = [int(row[str(sid)]) for sid in sorted(bounds)]
                if telemetry: telemetry.record('FRAME_SENT,' + row['time_seconds'] + ',' + ','.join(map(str, values)))
                exchange(bus, 'FRAME,' + ','.join(map(str, values)), 'OK,FRAME', timeout=.4, telemetry=telemetry)
                remaining = .02 * args.time_scale - (time.monotonic() - began)
                if remaining > 0: time.sleep(remaining)
    finally:
        if bus.is_open:
            try:
                bus.write(b'STOP\n'); bus.flush()
                deadline = time.monotonic() + 3
                released = False
                while time.monotonic() < deadline:
                    message = bus.readline().decode('ascii', errors='replace').strip()
                    if message: print(message, flush=True)
                    if message and telemetry: telemetry.record(message)
                    if message == 'STOPPED,RELEASE_VERIFIED': released = True; break
                    if message == 'STOPPED,RELEASE_UNCONFIRMED': break
                if not released: print('Torque release unconfirmed; use the physical power cutoff.', file=sys.stderr)
            finally: bus.close()
        if telemetry: telemetry.close()


if __name__ == '__main__': main()
