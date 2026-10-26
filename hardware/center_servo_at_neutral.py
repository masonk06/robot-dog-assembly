"""Calibrate one torque-off STS3215's current physical pose to encoder 2048.

Usage: python center_servo_at_neutral.py <servo-id>

For STS-series servos, writing 128 to register 40 invokes the documented
"middle position" calibration. This script only runs when torque is off,
verifies the post-calibration position is near 2048, and explicitly leaves
torque disabled. It sends no motion goal.
"""
import sys
import time

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) == 2 else 0
if not 1 <= SERVO_ID <= 12:
    raise SystemExit("Usage: python center_servo_at_neutral.py <servo-id 1..12>")


def exchange(bus, instruction, params):
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
            if frame[4]:
                raise RuntimeError(f"Servo reports error {frame[4]}")
            return frame[5:-1]
    raise RuntimeError(f"No valid response from servo ID {SERVO_ID}")


def read(bus, address, count):
    response = exchange(bus, 2, [address, count])
    if len(response) != count:
        raise RuntimeError("Incorrect read length")
    return response


def write(bus, address, values):
    exchange(bus, 3, [address, *values])


with serial.Serial("COM5", 1_000_000, timeout=0.1, write_timeout=1) as bus:
    before = int.from_bytes(read(bus, 56, 2), "little")
    torque_before = read(bus, 40, 1)[0]
    if torque_before != 0:
        raise SystemExit(f"ID {SERVO_ID} has torque_enable={torque_before}; no calibration attempted.")
    print(f"ID {SERVO_ID}: calibrating current position {before} ticks to 2048; torque is off.", flush=True)
    try:
        write(bus, 40, [128])
        time.sleep(0.2)
        after = int.from_bytes(read(bus, 56, 2), "little")
        if abs(after - 2048) > 8:
            raise RuntimeError(f"Unexpected centered position {after}; expected approximately 2048")
        print(f"ID {SERVO_ID}: centered successfully; position={after}", flush=True)
    finally:
        # Middle-position calibration should not enable torque, but leave the
        # bus in the known-safe state even if a servo firmware differs.
        write(bus, 40, [0])
        print(f"ID {SERVO_ID}: torque disabled.", flush=True)
