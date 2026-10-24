"""Slowly return one centered RoboDog joint to raw position 2048, then release it.

Usage: python move_joint_to_neutral.py <servo-id>

This is a temporary motion command only. It requires torque to be disabled,
uses a low speed of 100 ticks/s, waits for the commanded distance, and always
disables torque at the end. It does not write EEPROM settings.
"""
import sys
import time

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) == 2 else 0
NEUTRAL = 2048
SPEED_TICKS_PER_SECOND = 100
if not 1 <= SERVO_ID <= 12:
    raise SystemExit("Usage: python move_joint_to_neutral.py <servo-id 1..12>")
if SERVO_ID == 2:
    raise SystemExit(
        "ID 2 direct-neutral motion is disabled: its physical direction is "
        "not consistent with the current absolute-position mapping. Use a "
        "reviewed coordinated trajectory instead."
    )


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


def packet(servo_id, instruction, params):
    body = bytes([servo_id, len(params) + 2, instruction, *params])
    return b"\xff\xff" + body + bytes([(~sum(body)) & 255])


def broadcast_torque_off(bus):
    # Broadcast writes have no status reply, so this remains effective when a
    # target servo is already reporting a protection fault.
    bus.write(packet(254, 3, [40, 0]))
    bus.flush()


def read(bus, address, count):
    value = exchange(bus, 2, [address, count])
    if len(value) != count:
        raise RuntimeError("Incorrect read length")
    return value


def write(bus, address, values):
    exchange(bus, 3, [address, *values])


def word(value):
    return list(value.to_bytes(2, "little"))


with serial.Serial("COM5", 1_000_000, timeout=0.1, write_timeout=1) as bus:
    if read(bus, 33, 1)[0] != 0 or read(bus, 40, 1)[0] != 0:
        raise SystemExit("Expected position mode and torque disabled; no movement attempted.")
    telemetry = read(bus, 56, 8)
    start = int.from_bytes(telemetry[:2], "little")
    if telemetry[7] >= 50:
        raise SystemExit("Temperature too high for movement; no movement attempted.")
    old_settings = read(bus, 41, 7)
    print(f"ID {SERVO_ID}: moving slowly from {start} to neutral {NEUTRAL}.", flush=True)
    try:
        write(bus, 41, [5, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
        write(bus, 40, [1])
        time.sleep(0.25)
        write(bus, 42, word(NEUTRAL))
        time.sleep(abs(NEUTRAL - start) / SPEED_TICKS_PER_SECOND + 0.75)
        after = int.from_bytes(read(bus, 56, 2), "little")
        print(f"ID {SERVO_ID}: final position={after}", flush=True)
    finally:
        broadcast_torque_off(bus)
        # These are volatile motion settings. Restore them without requiring
        # a healthy status reply from a servo that may be in protection.
        bus.write(packet(SERVO_ID, 3, [41, old_settings[0]]))
        bus.write(packet(SERVO_ID, 3, [46, *old_settings[5:7]]))
        bus.flush()
        print("Broadcast torque-off sent.", flush=True)
