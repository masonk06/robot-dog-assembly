"""Safely nudge one RoboDog STS3215 joint, return it, and release torque.

Usage: python test_joint_nudge.py <servo-id> [delta-ticks]

The default delta is +114 ticks (about +10 degrees). This tool refuses to
run unless the selected servo is in position mode with torque disabled. It
checks electronic angle limits and temperature, then restores the initial
position and disables torque even if a communication error occurs.
"""
import sys
import time

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) >= 2 else 0
DELTA = int(sys.argv[2]) if len(sys.argv) >= 3 else 114

if not 1 <= SERVO_ID <= 12:
    raise SystemExit("Usage: python test_joint_nudge.py <servo-id 1..12> [delta-ticks]")
if not -114 <= DELTA <= 114 or DELTA == 0:
    raise SystemExit("delta-ticks must be between -114 and +114 and cannot be zero")


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
    result = exchange(bus, 2, [address, count])
    if len(result) != count:
        raise RuntimeError("Incorrect read length")
    return result


def write(bus, address, values):
    exchange(bus, 3, [address, *values])


def word(value):
    return list(value.to_bytes(2, "little"))


with serial.Serial("COM5", 1_000_000, timeout=0.08, write_timeout=1) as bus:
    if read(bus, 33, 1)[0] != 0 or read(bus, 40, 1)[0] != 0:
        raise SystemExit("Expected position mode and torque disabled; no movement attempted.")
    telemetry = read(bus, 56, 8)
    start = int.from_bytes(telemetry[:2], "little")
    limits = read(bus, 9, 4)
    low = int.from_bytes(limits[:2], "little")
    high = int.from_bytes(limits[2:], "little")
    target = start + DELTA
    if not (0 <= start <= 4095 and low <= start <= high and low <= target <= high and target <= 4095):
        raise SystemExit(f"Target is outside limits: start={start}, target={target}, limits={low}..{high}")
    if telemetry[7] >= 50:
        raise SystemExit("Temperature too high for test; no movement attempted.")
    old_settings = read(bus, 41, 7)
    print(f"ID {SERVO_ID}: start={start}, target={target}, temperature={telemetry[7]} C", flush=True)
    try:
        # First make the current position the target; this prevents an old goal
        # from causing a jump when torque is enabled.
        write(bus, 41, [5, *word(start), 0, 0, *word(100)])
        write(bus, 40, [1])
        time.sleep(0.25)
        write(bus, 42, word(target))
        time.sleep(1)
        print("Position after nudge:", int.from_bytes(read(bus, 56, 2), "little"), flush=True)
        write(bus, 42, word(start))
        time.sleep(1)
        print("Position after return:", int.from_bytes(read(bus, 56, 2), "little"), flush=True)
    finally:
        try:
            write(bus, 40, [0])
            print(f"Servo ID {SERVO_ID} torque disabled.", flush=True)
        finally:
            write(bus, 41, [old_settings[0]])
            write(bus, 46, list(old_settings[5:7]))
