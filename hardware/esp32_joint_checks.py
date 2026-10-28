"""Pure manual direction/endpoint validation; no serial or motor operations."""
from copy import deepcopy
import math

TICKS_PER_RADIAN = 4096 / (2 * math.pi)


def neutral_neighbors(latest, joints, selected, now, tolerance=35, zero_scope='all'):
    if zero_scope not in ('all','selected_leg'):
        raise ValueError('Unknown neutral-check scope')
    prefix='_'.join(selected.split('_')[:2])+'_'
    result = {}
    for name, joint in joints.items():
        if name == selected:
            continue
        reading = latest.get(joint['id'])
        if not reading or not 0 <= now - reading['timestamp'] <= 2:
            raise ValueError(f'{name}: fresh telemetry required for neighboring joints')
        if reading['torque'] != 0 or reading['mode'] != 0 or reading['status'] != 0:
            raise ValueError(f'{name}: torque OFF, position mode and clear status required')
        check_position=zero_scope=='all' or name.startswith(prefix)
        if check_position and abs(reading['ticks'] - joint['neutral_ticks']) > tolerance:
            selected_id=joints[selected]['id']
            raise ValueError(f'Selected {selected} (ID {selected_id}); waiting for {name} (ID {joint["id"]}) '
                             f'to be near ITS saved zero {joint["neutral_ticks"]} ticks (live {reading["ticks"]}).')
        result[name] = dict(id=joint['id'], ticks=reading['ticks'], torque=0,
                            mode=0, status=0, age_s=now - reading['timestamp'])
    return result


class JointChecks:
    def __init__(self, zero_record, model_limits):
        self.zeros = deepcopy(zero_record['joints'])
        self.limits = model_limits
        self.records = {name: dict(id=j['id'], neutral_ticks=j['neutral_ticks'],
                                  direction_verified=False, limits_verified=False)
                        for name, j in self.zeros.items()}

    def baseline(self, name, sample):
        if sample['id'] != self.zeros[name]['id']:
            raise ValueError('Servo ID mismatch')
        if abs(sample['measured_ticks'] - self.zeros[name]['neutral_ticks']) > 12:
            raise ValueError(f'Return this joint near {self.zeros[name]["neutral_ticks"]} ticks before baseline')
        self.records[name] = dict(id=sample['id'], neutral_ticks=self.zeros[name]['neutral_ticks'],
                                  baseline=deepcopy(sample), direction_verified=False, limits_verified=False)

    def direction(self, name, positive, sample):
        record = self.records[name]
        if 'baseline' not in record:
            raise ValueError('Capture a fresh neutral baseline for this joint first')
        if sample['id'] != record['id']:
            raise ValueError('Servo ID mismatch')
        delta = sample['measured_ticks'] - record['baseline']['measured_ticks']
        if not 20 <= abs(delta) <= 171:
            raise ValueError('Use a small clear manual movement: roughly 2–15 degrees from baseline, without wrap')
        key = 'positive_direction' if positive else 'negative_direction'
        other = record.get('negative_direction' if positive else 'positive_direction')
        if other:
            other_delta = other['measured_ticks'] - record['baseline']['measured_ticks']
            if delta * other_delta >= 0:
                raise ValueError('Positive and negative model movements must give opposite encoder changes')
        record[key] = deepcopy(sample)
        record['direction_verified'] = False
        record['limits_verified'] = False
        for field in ('minimum_ticks', 'maximum_ticks', 'negative_endpoint', 'positive_endpoint', 'limits_baseline', 'sign'):
            record.pop(field, None)
        if 'positive_direction' in record and 'negative_direction' in record:
            record['sign'] = 1 if record['positive_direction']['measured_ticks'] > record['baseline']['measured_ticks'] else -1
            record['direction_verified'] = True
        return record['direction_verified']

    def endpoint(self, name, positive, sample, neighbors, margin=25):
        record = self.records[name]
        if not record['direction_verified']:
            raise ValueError('Verify both directions for this joint before capturing limits')
        if 'limits_baseline' not in record:
            raise ValueError('Capture a new neutral baseline in Limits mode first')
        if sample['id'] != record['id']:
            raise ValueError('Servo ID mismatch')
        ticks = sample['measured_ticks']
        if not 0 <= ticks <= 4095:
            raise ValueError('Endpoint outside the continuous no-wrap encoder interval')
        delta = record['sign'] * (ticks - record['neutral_ticks'])
        if (delta <= margin if positive else delta >= -margin):
            raise ValueError('Endpoint must be on the indicated model-angle side, with a 25-tick inward margin')
        angle = delta / TICKS_PER_RADIAN
        low_angle, high_angle = self.limits[name]
        if not low_angle <= angle <= high_angle:
            raise ValueError('Endpoint is outside the simulated joint range; choose a smaller clear interval')
        key = 'positive_endpoint' if positive else 'negative_endpoint'
        record[key] = dict(sample=deepcopy(sample), neighbors=deepcopy(neighbors),
                           operator_confirmed_backed_off_clear_endpoint=True,
                           model_angle_rad=angle)
        record['limits_verified'] = False
        if 'positive_endpoint' in record and 'negative_endpoint' in record:
            bounds = sorted(record[k]['sample']['measured_ticks'] for k in ('negative_endpoint', 'positive_endpoint'))
            if not bounds[0] + margin < record['neutral_ticks'] < bounds[1] - margin:
                raise ValueError('Neutral must be inside both endpoints with the inward margin')
            record.update(minimum_ticks=bounds[0], maximum_ticks=bounds[1], margin_ticks=margin,
                          limits_verified=True, limit_scope='Manual endpoints with other joints near neutral only')
        return record['limits_verified']

    def limit_baseline(self, name, sample):
        record = self.records[name]
        if not record['direction_verified']:
            raise ValueError('Verify both directions before starting this joint’s limits')
        if sample['id'] != record['id'] or abs(sample['measured_ticks'] - record['neutral_ticks']) > 12:
            raise ValueError('Return this joint near its saved zero before starting limits')
        record['limits_baseline'] = deepcopy(sample)
        record['limits_verified'] = False
        for field in ('minimum_ticks', 'maximum_ticks', 'positive_endpoint', 'negative_endpoint'):
            record.pop(field, None)

    def counts(self):
        return (sum(j['direction_verified'] for j in self.records.values()),
                sum(j['limits_verified'] for j in self.records.values()))
