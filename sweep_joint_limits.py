"""Slowly validate symmetric software limits around a centered STS3215 neutral.

Usage: python sweep_joint_limits.py <servo-id> <absolute-degrees>

The servo must already be centered at its physical neutral (2048 ticks), be
in position mode, and have torque disabled. The test visits the negative and
positive endpoints at a cautious 100 ticks/s, returns to neutral after each,
and releases torque. It writes no EEPROM limits or motion settings.
"""
import sys
import time

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) >= 2 else 0
LIMIT_DEGREES = float(sys.argv[2]) if len(sys.argv) >= 3 else 0.0
if not 1 <= SERVO_ID <= 12 or not 0 < LIMIT_DEGREES <= 75:
    raise SystemExit("Usage: python sweep_joint_limits.py <servo-id 1..12> <absolute-degrees 0..75>")

NEUTRAL = 2048
TICKS_PER_DEGREE = 4096 / 360
SPEED_TICKS_PER_SECOND = 100
limit_ticks = round(LIMIT_DEGREES * TICKS_PER_DEGREE)
negative_target = NEUTRAL - limit_ticks
positive_target = NEUTRAL + limit_ticks
if not 0 <= negative_target <= positive_target <= 4095:
    raise SystemExit("Endpoints exceed the raw 0..4095 range; no movement attempted.")


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


def word(value):
    return list(value.to_bytes(2, "little"))


def telemetry(bus):
    value = read(bus, 56, 8)
    return int.from_bytes(value[:2], "little"), value[6] / 10, value[7]


with serial.Serial("COM5", 1_000_000, timeout=0.1, write_timeout=1) as bus:
    mode = read(bus, 33, 1)[0]
    torque = read(bus, 40, 1)[0]
    start, voltage, temperature = telemetry(bus)
    if mode != 0 or torque != 0:
        raise SystemExit(f"Expected position mode and torque disabled; found mode={mode}, torque={torque}.")
    if temperature >= 50:
        raise SystemExit(f"Temperature {temperature} C too high; no movement attempted.")
    old_settings = read(bus, 41, 7)
    print(f"ID {SERVO_ID}: sweeping +/-{LIMIT_DEGREES:g} deg ({negative_target}..{positive_target}), start={start}, {voltage:.1f} V, {temperature} C", flush=True)
    try:
        write(bus, 41, [5, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
        write(bus, 40, [1])
        time.sleep(0.25)
        previous = start
        for label, target in (("neutral", NEUTRAL), ("negative endpoint", negative_target), ("neutral", NEUTRAL), ("positive endpoint", positive_target), ("neutral", NEUTRAL)):
            write(bus, 42, word(target))
            time.sleep(abs(target - previous) / SPEED_TICKS_PER_SECOND + 0.5)
            position, voltage, temperature = telemetry(bus)
            print(f"{label}: position={position}, voltage={voltage:.1f} V, temperature={temperature} C", flush=True)
            if temperature >= 50:
                raise RuntimeError(f"Temperature reached {temperature} C; stopping sweep")
            previous = target
    finally:
        try:
            write(bus, 40, [0])
            print(f"Servo ID {SERVO_ID} torque disabled.", flush=True)
        finally:
            write(bus, 41, [old_settings[0]])
            write(bus, 46, list(old_settings[5:7]))
