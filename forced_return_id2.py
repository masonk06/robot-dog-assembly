"""Deprecated safety stub.

STS3215 position mode does not use goal-position bit 15 to force an absolute
target's travel path.  Do not use this file for a directed return; a true
long-path move requires a separately reviewed temporary Step-mode procedure.
"""
import time

from servo_usb_scan import serial

raise SystemExit(
    "Deprecated: position mode cannot force an absolute target's direction. "
    "Do not run this file."
)

SERVO_ID = 2
NEUTRAL = 2048
FORCED_DIRECTION_TARGET = NEUTRAL | 0x8000
SPEED_TICKS_PER_SECOND = 100
EXPECTED_START_MIN = 3300
EXPECTED_START_MAX = 3600


def packet(servo_id, instruction, params=()):
    body = bytes([servo_id, len(params) + 2, instruction, *params])
    return b"\xff\xff" + body + bytes([(~sum(body)) & 255])


def request(bus, instruction, params=()):
    sent = packet(SERVO_ID, instruction, params)
    bus.reset_input_buffer()
    bus.write(sent)
    bus.flush()
    data = bus.read(64)
    for i in range(len(data) - 5):
        if data[i:i + 3] != bytes([255, 255, SERVO_ID]):
            continue
        length = data[i + 3]
        frame = data[i:i + length + 4]
        if length >= 2 and len(frame) == length + 4 and sum(frame[2:]) & 255 == 255:
            return frame[4], frame[5:-1]
    raise RuntimeError("No valid response from ID 2")


def read(bus, address, count):
    status, value = request(bus, 2, [address, count])
    if status:
        raise RuntimeError(f"Servo protection/error status {status}")
    if len(value) != count:
        raise RuntimeError("Incorrect read length")
    return value


def write(bus, address, values):
    status, _ = request(bus, 3, [address, *values])
    if status:
        raise RuntimeError(f"Servo protection/error status {status}")


def word(value):
    return list(value.to_bytes(2, "little"))


def broadcast_torque_off(bus):
    # Broadcasts do not return a status packet. This remains effective even if
    # ID 2 is reporting a protection flag.
    bus.write(packet(254, 3, [40, 0]))
    bus.flush()


with serial.Serial("COM5", 1_000_000, timeout=0.1, write_timeout=1) as bus:
    old_settings = None
    try:
        if read(bus, 33, 1)[0] != 0 or read(bus, 40, 1)[0] != 0:
            raise RuntimeError("Expected position mode and torque disabled")
        telemetry = read(bus, 56, 8)
        start = int.from_bytes(telemetry[:2], "little")
        if not EXPECTED_START_MIN <= start <= EXPECTED_START_MAX:
            raise RuntimeError(f"Unexpected start position {start}; no motion attempted")
        if telemetry[7] >= 45:
            raise RuntimeError(f"Temperature {telemetry[7]} C is too high; no motion attempted")
        old_settings = read(bus, 41, 7)
        print(f"ID 2 forced-direction return: start={start}, target={NEUTRAL}, command=0x{FORCED_DIRECTION_TARGET:04X}", flush=True)
        # Start at the present location so enabling torque cannot cause a jump.
        write(bus, 41, [5, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
        write(bus, 40, [1])
        time.sleep(0.25)
        write(bus, 42, word(FORCED_DIRECTION_TARGET))
        # The forced route is about 2661 ticks / 234 degrees. Poll frequently
        # for a protection flag instead of waiting blind.
        for second in range(31):
            status, value = request(bus, 2, [56, 8])
            if status:
                raise RuntimeError(f"Servo protection/error status {status} during motion")
            position = int.from_bytes(value[:2], "little")
            if value[7] >= 45:
                raise RuntimeError(f"Temperature reached {value[7]} C during motion")
            if second % 5 == 0:
                print(f"t={second:02d}s position={position}, temperature={value[7]} C", flush=True)
            if abs(position - NEUTRAL) <= 8:
                print(f"Reached neutral at t={second}s: position={position}", flush=True)
                break
            time.sleep(1)
        else:
            raise RuntimeError("Timed out before reaching neutral")
    finally:
        broadcast_torque_off(bus)
        if old_settings is not None:
            # Restore volatile acceleration/speed settings; torque stays off.
            bus.write(packet(SERVO_ID, 3, [41, old_settings[0]]))
            bus.write(packet(SERVO_ID, 3, [46, *old_settings[5:7]]))
            bus.flush()
        print("Broadcast torque-off sent.", flush=True)
