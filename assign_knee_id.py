"""Assign the single connected STS knee servo ID 3; never command motion."""
from servo_usb_scan import serial
import time


def request(bus, sid, instruction, params=()):
    body = bytes([sid, len(params) + 2, instruction, *params])
    packet = b'\xff\xff' + body + bytes([(~sum(body)) & 255])
    bus.reset_input_buffer()
    bus.write(packet)
    bus.flush()
    data = bus.read(64)
    for i in range(len(data) - 5):
        if data[i:i+2] != b'\xff\xff':
            continue
        length = data[i+3]
        frame = data[i:i+length+4]
        if length >= 2 and len(frame) == length+4 and frame != packet and sum(frame[2:]) & 255 == 255:
            return frame
    return None


with serial.Serial('COM5', 1_000_000, timeout=0.05, write_timeout=1) as bus:
    ids = []
    for sid in range(254):
        reply = request(bus, sid, 1)
        if reply and reply[2] == sid:
            ids.append(sid)
    print('Connected IDs:', ids, flush=True)
    if ids != [1]:
        raise SystemExit('Expected only ID 1. No settings changed.')
    reply = request(bus, 1, 3, [55, 0])  # Unlock EEPROM.
    if not reply or reply[4] != 0:
        request(bus, 1, 3, [55, 1])
        raise SystemExit('Unlock not confirmed; ID unchanged, relock attempted.')
    try:
        request(bus, 1, 3, [5, 3])  # ID register only.
        time.sleep(0.1)
    finally:
        request(bus, 3, 3, [55, 1])  # Relock at the new address.
        request(bus, 1, 3, [55, 1])  # Relock old address if rename failed.
    ping = request(bus, 3, 1)
    identity = request(bus, 3, 2, [5, 1])
    lock = request(bus, 3, 2, [55, 1])
    old = request(bus, 1, 1)
    if not (ping and ping[2] == 3 and ping[4] == 0
            and identity and identity[4:6] == bytes([0, 3])
            and lock and lock[4:6] == bytes([0, 1]) and old is None):
        raise SystemExit(f'Verification incomplete: ping={ping!r}, ID={identity!r}, lock={lock!r}, old={old!r}')
    print('Success: knee ID = 3; EEPROM locked; ID 1 no longer responds. No motion commanded.')
