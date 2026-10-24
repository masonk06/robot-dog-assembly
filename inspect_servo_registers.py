"""Read selected STS3215 configuration and health registers; never writes."""
import sys

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) == 2 else 0
if not 1 <= SERVO_ID <= 12:
    raise SystemExit("Usage: python inspect_servo_registers.py <servo-id 1..12>")


def request(bus, instruction, params):
    body = bytes([SERVO_ID, len(params) + 2, instruction, *params])
    bus.reset_input_buffer()
    bus.write(b"\xff\xff" + body + bytes([(~sum(body)) & 255]))
    bus.flush()
    data = bus.read(64)
    for i in range(len(data) - 5):
        if data[i:i + 3] != bytes([255, 255, SERVO_ID]):
            continue
        length = data[i + 3]
        frame = data[i:i + length + 4]
        if length >= 2 and len(frame) == length + 4 and sum(frame[2:]) & 255 == 255:
            return frame[4], frame[5:-1]
    raise RuntimeError(f"No valid response from ID {SERVO_ID}")


def read(bus, address, count):
    status, value = request(bus, 2, [address, count])
    if len(value) != count:
        raise RuntimeError("Incorrect read length")
    return status, value


with serial.Serial("COM5", 1_000_000, timeout=0.1, write_timeout=1) as bus:
    fields = [
        (5, 1, "id"), (9, 4, "angle_limits"), (18, 1, "phase"),
        (31, 2, "position_offset"), (33, 1, "mode"), (34, 3, "protection"),
        (40, 1, "torque_enable"), (56, 8, "telemetry"), (65, 1, "servo_status"),
    ]
    for address, count, label in fields:
        status, value = read(bus, address, count)
        print(f"{label} @ {address}: status={status}, raw={value.hex(' ')}", flush=True)
