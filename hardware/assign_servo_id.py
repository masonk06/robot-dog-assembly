"""Safely rename one isolated STS3215 servo; does not command motion."""

import sys
import time

from servo_usb_scan import serial


def request(bus, servo_id, instruction, params=()):
    body = bytes([servo_id, len(params) + 2, instruction, *params])
    packet = b"\xff\xff" + body + bytes([(~sum(body)) & 0xFF])
    bus.reset_input_buffer()
    bus.write(packet)
    bus.flush()
    data = bus.read(64)
    for index in range(len(data) - 5):
        if data[index:index + 2] != b"\xff\xff":
            continue
        length = data[index + 3]
        frame = data[index:index + length + 4]
        if length >= 2 and len(frame) == length + 4 and frame != packet and sum(frame[2:]) & 0xFF == 0xFF:
            return frame
    return None


def ping(bus, servo_id):
    reply = request(bus, servo_id, 1)
    return reply is not None and reply[2] == servo_id and reply[4] == 0


if len(sys.argv) != 3:
    raise SystemExit("Usage: python assign_servo_id.py <current-id> <new-id>")

old_id, new_id = map(int, sys.argv[1:])
if not 0 <= old_id <= 253 or not 0 <= new_id <= 253 or old_id == new_id:
    raise SystemExit("IDs must be different values in 0..253.")

with serial.Serial("COM5", 1_000_000, timeout=0.05, write_timeout=1) as bus:
    responders = [servo_id for servo_id in range(254) if ping(bus, servo_id)]
    if responders != [old_id]:
        raise SystemExit(f"Expected exactly one isolated servo at ID {old_id}; found {responders}. No settings changed.")

    unlocked = request(bus, old_id, 3, [55, 0])
    if not unlocked or unlocked[4] != 0:
        raise SystemExit("Could not unlock EEPROM. ID unchanged.")
    try:
        changed = request(bus, old_id, 3, [5, new_id])
        if not changed or changed[4] != 0:
            raise SystemExit("Servo rejected the ID write.")
        time.sleep(0.1)
    finally:
        request(bus, new_id, 3, [55, 1])
        request(bus, old_id, 3, [55, 1])

    if not ping(bus, new_id) or ping(bus, old_id):
        raise SystemExit(f"Verification failed: expected only ID {new_id} to respond.")
    identity = request(bus, new_id, 2, [5, 1])
    locked = request(bus, new_id, 2, [55, 1])
    if not identity or identity[4:6] != bytes([0, new_id]) or not locked or locked[4:6] != bytes([0, 1]):
        raise SystemExit("Rename response received, but ID or EEPROM-lock verification failed.")

print(f"Success: ID {old_id} -> {new_id}; EEPROM locked; no motion commands sent.")
