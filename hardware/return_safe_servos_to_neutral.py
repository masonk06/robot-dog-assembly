"""Return RoboDog's verified-safe servos to the saved physical neutral pose.

This deliberately excludes front-left hip roll (ID 1) and front-left hip pitch
(ID 2): the newest manual endpoints and earlier overload report make a direct
powered return unsafe.  Every executed path ends with broadcast torque-off.
"""
import time

from single_leg_trot import (
    ACCELERATION, BAUD, MAX_TEMPERATURE_C, PORT, SPEED_TICKS_PER_SECOND,
    load_neutral, packet, read, serial, sync_write, torque_off, word, write,
)


SAFE_IDS = (3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
RETURN_SPEED_TICKS_PER_SECOND = 60
POSITION_TOLERANCE_TICKS = 35


def current_state(bus, servo_id):
    mode = read(bus, servo_id, 33, 1)[0]
    torque = read(bus, servo_id, 40, 1)[0]
    telemetry = read(bus, servo_id, 56, 8)
    position = int.from_bytes(telemetry[:2], "little")
    temperature = telemetry[7]
    if mode != 0:
        raise RuntimeError(f"ID {servo_id}: expected position mode, found mode {mode}")
    if torque != 0:
        raise RuntimeError(f"ID {servo_id}: torque is already on; no motion attempted")
    if temperature >= MAX_TEMPERATURE_C:
        raise RuntimeError(f"ID {servo_id}: {temperature} C is too warm")
    return position, temperature, read(bus, servo_id, 41, 7)


def main():
    neutral = load_neutral()
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        settings = {}
        starts = {}
        try:
            for servo_id in SAFE_IDS:
                starts[servo_id], temperature, settings[servo_id] = current_state(bus, servo_id)
                print(f"ID {servo_id}: {starts[servo_id]} -> {neutral[servo_id]} ticks ({temperature} C)")
            for servo_id in SAFE_IDS:
                write(bus, servo_id, 41, [ACCELERATION, *word(starts[servo_id]), 0, 0, *word(RETURN_SPEED_TICKS_PER_SECOND)])
            for servo_id in SAFE_IDS:
                write(bus, servo_id, 40, [1])
            sync_write(bus, 42, 2, tuple((servo_id, word(neutral[servo_id])) for servo_id in SAFE_IDS))
            longest_ticks = max(abs(neutral[servo_id] - starts[servo_id]) for servo_id in SAFE_IDS)
            time.sleep(longest_ticks / RETURN_SPEED_TICKS_PER_SECOND + 1.5)
            for servo_id in SAFE_IDS:
                telemetry = read(bus, servo_id, 56, 8)
                position = int.from_bytes(telemetry[:2], "little")
                temperature = telemetry[7]
                if temperature >= MAX_TEMPERATURE_C:
                    raise RuntimeError(f"ID {servo_id}: reached {temperature} C")
                if abs(position - neutral[servo_id]) > POSITION_TOLERANCE_TICKS:
                    raise RuntimeError(f"ID {servo_id}: expected {neutral[servo_id]}, reached {position}")
            print("Ten safe servos reached physical neutral.")
        finally:
            torque_off(bus)
            for servo_id, saved in settings.items():
                bus.write(packet(servo_id, 3, [41, saved[0]]))
                bus.write(packet(servo_id, 3, [46, *saved[5:7]]))
            bus.flush()
            print("Broadcast torque-off sent. IDs 1 and 2 were not commanded.")


if __name__ == "__main__":
    main()
