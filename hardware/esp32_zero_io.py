"""Pure CSV parsing and stationary zero checks. No serial/motor operations."""
from collections import deque
from datetime import datetime
import math
from statistics import median
import time


def parse_servo_csv(line, now=None):
    fields = line.strip().split(',')
    if not fields or fields[0] != 'servo':
        return None
    if len(fields) != 9:
        raise ValueError('Expected full servo CSV including torque, mode and status')
    try:
        sid, device_us, ticks = (int(fields[i]) for i in (1, 2, 3))
        voltage = float(fields[4])
        temperature, torque, mode, status = (int(fields[i]) for i in (5, 6, 7, 8))
    except ValueError as exc:
        raise ValueError('Malformed servo CSV') from exc
    if not (1 <= sid <= 12 and 0 <= device_us < 2**32 and -32767 <= ticks <= 32767
            and math.isfinite(voltage) and 0 <= voltage <= 25.5
            and 0 <= temperature <= 255 and torque in (0, 1)
            and 0 <= mode <= 255 and 0 <= status <= 255):
        raise ValueError('Servo CSV values outside expected register ranges')
    return dict(id=sid, device_us=device_us, ticks=ticks, voltage=voltage,
                temperature=temperature, torque=torque, mode=mode, status=status,
                timestamp=time.monotonic() if now is None else now)


class ZeroSamples:
    def __init__(self):
        self.samples = {sid: deque(maxlen=6) for sid in range(1, 13)}

    def add(self, reading):
        history = self.samples[reading['id']]
        if history:
            advance = (reading['device_us'] - history[-1]['device_us']) % 2**32
            if advance == 0:
                return  # A repeated device sample cannot satisfy the stillness gate.
            if advance >= 2**31:
                history.clear()  # Reset or out-of-order data: require three new samples.
        history.append(dict(reading))

    def invalidate(self, sid):
        if sid in self.samples:
            self.samples[sid].clear()

    def capture(self, sid, operator_confirmed, now=None):
        if not operator_confirmed:
            raise ValueError('Confirm the physical joint ID and its model-zero pose first')
        now = time.monotonic() if now is None else now
        readings = list(self.samples[sid])[-3:]
        if len(readings) != 3:
            raise ValueError('Wait for three distinct live samples (about 4 seconds)')
        if not 0 <= now - readings[-1]['timestamp'] <= 2 or now - readings[0]['timestamp'] > 6:
            raise ValueError('Fresh telemetry required; this is a stationary manual check only')
        if any(r['torque'] != 0 for r in readings):
            raise ValueError('Torque must report OFF; this tool cannot release it')
        if any(r['mode'] != 0 or r['status'] != 0 for r in readings):
            raise ValueError('Position mode and zero servo status are required')
        ticks = [r['ticks'] for r in readings]
        if any(not 0 <= tick <= 4095 for tick in ticks):
            raise ValueError('Encoder is outside the no-wrap interval 0..4095')
        if max(ticks) - min(ticks) > 8:
            raise ValueError('Joint is moving: hold its zero pose and wait for stable readings')
        return dict(id=sid, neutral_ticks=int(round(median(ticks))), sample_ticks=ticks,
                    sample_device_us=[r['device_us'] for r in readings],
                    captured_local=datetime.now().astimezone().isoformat(),
                    operator_confirmed_joint_id_and_zero_pose=True,
                    torque_reported_off=True, position_mode=True, servo_status=0,
                    direction_verified=False, limits_verified=False)
