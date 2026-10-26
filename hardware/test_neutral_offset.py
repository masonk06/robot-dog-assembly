"""Move one joint to an exact offset from the saved neutral pose, then return.

Usage: python test_neutral_offset.py <servo-id> <offset-degrees>

The requested target is calculated from neutral_pose.json, not from the
instantaneous encoder value. This keeps repeated tests at a precise physical
offset. It is deliberately limited to +/-20 degrees and refuses targets that
would cross the 0/4095 raw encoder seam. It never changes EEPROM settings.
"""
import json
import sys
import time
from pathlib import Path

from servo_usb_scan import serial

SERVO_ID = int(sys.argv[1]) if len(sys.argv) >= 2 else 0
OFFSET_DEGREES = float(sys.argv[2]) if len(sys.argv) >= 3 else 999.0
if not 1 <= SERVO_ID <= 12 or not -20.0 <= OFFSET_DEGREES <= 20.0 or OFFSET_DEGREES == 0:
    raise SystemExit("Usage: python test_neutral_offset.py <servo-id 1..12> <offset-degrees within +/-20>")

neutral_data = json.loads((Path(__file__).with_name("neutral_pose.json")).read_text())
neutral_ticks = next(item["neutral_ticks"] for item in neutral_data["positions"] if item["id"] == SERVO_ID)
ticks_per_degree = 1 / neutral_data["tick_resolution_degrees"]
target = neutral_ticks + round(OFFSET_DEGREES * ticks_per_degree)
if not 0 <= target <= 4095:
    raise SystemExit("This test would cross the raw encoder seam; no movement attempted.")
# The cautious test speed below is 100 ticks/s.  Allow the requested motion
# plus a small settle margin rather than mistaking an in-progress move for a
# mechanical stop.
MOVE_SPEED_TICKS_PER_SECOND = 100
SETTLE_SECONDS = max(1.0, abs(target - neutral_ticks) / MOVE_SPEED_TICKS_PER_SECOND + 0.5)


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
    if telemetry[7] >= 50:
        raise SystemExit("Temperature too high for test; no movement attempted.")
    old_settings = read(bus, 41, 7)
    print(f"ID {SERVO_ID}: start={start}, neutral={neutral_ticks}, target={target} ({OFFSET_DEGREES:+g} deg)", flush=True)
    try:
        # Preserve the present pose at torque-on, then settle at the saved neutral
        # before making the precisely bounded test movement.
        write(bus, 41, [5, *word(start), 0, 0, *word(100)])
        write(bus, 40, [1])
        time.sleep(0.25)
        write(bus, 42, word(neutral_ticks))
        time.sleep(SETTLE_SECONDS)
        print("Position at neutral:", int.from_bytes(read(bus, 56, 2), "little"), flush=True)
        write(bus, 42, word(target))
        time.sleep(SETTLE_SECONDS)
        print("Position at test target:", int.from_bytes(read(bus, 56, 2), "little"), flush=True)
        write(bus, 42, word(neutral_ticks))
        time.sleep(SETTLE_SECONDS)
        print("Position after return to neutral:", int.from_bytes(read(bus, 56, 2), "little"), flush=True)
    finally:
        try:
            write(bus, 40, [0])
            print(f"Servo ID {SERVO_ID} torque disabled.", flush=True)
        finally:
            write(bus, 41, [old_settings[0]])
            write(bus, 46, list(old_settings[5:7]))
