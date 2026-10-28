"""Read servo telemetry only; never send write or movement instructions."""
from servo_usb_scan import serial


def read(bus, sid, address, count):
    body = bytes([sid, 4, 2, address, count])
    bus.reset_input_buffer()
    bus.write(b'\xff\xff' + body + bytes([(~sum(body)) & 255]))
    bus.flush()
    data = bus.read(64)
    for i in range(len(data) - 5):
        if data[i:i+4] != bytes([255, 255, sid, count+2]):
            continue
        frame = data[i:i+count+6]
        if len(frame) == count+6 and sum(frame[2:]) & 255 == 255:
            if frame[4]:
                raise RuntimeError(f'ID {sid}: status error {frame[4]}')
            return frame[5:-1]
    raise RuntimeError(f'ID {sid}: no valid read response at address {address}')


SERVOS = [
    (1, 'Front-right hip roll'),
    (2, 'Front-right hip pitch'),
    (3, 'Front-right knee pitch'),
    (4, 'Front-left hip roll'),
    (5, 'Front-left hip pitch'),
    (6, 'Front-left knee pitch'),
    (7, 'Rear-left hip roll'),
    (8, 'Rear-left hip pitch'),
    (9, 'Rear-left knee pitch'),
    (10, 'Rear-right hip pitch'),
    (11, 'Rear-right hip roll'),
    (12, 'Rear-right knee pitch'),
]


with serial.Serial('COM5', 1_000_000, timeout=0.1, write_timeout=1) as bus:
    for sid, name in SERVOS:
        try:
            telemetry = read(bus, sid, 56, 8)
            raw = int.from_bytes(telemetry[:2], 'little')
            position = -(raw & 0x7fff) if raw & 0x8000 else raw
            mode = read(bus, sid, 33, 1)[0]
            torque = read(bus, sid, 40, 1)[0]
            print(f'{name} (ID {sid}): position={position} ticks, voltage={telemetry[6]/10:.1f} V, '
                  f'temperature={telemetry[7]} C, mode={mode}, torque_enable={torque}', flush=True)
        except RuntimeError as error:
            print(f'{name} (ID {sid}): ERROR: {error}', flush=True)
