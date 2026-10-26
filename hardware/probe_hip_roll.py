"""Cautious, one-joint in-air probe for RoboDog hip-roll directions.

The selected hip-roll servo moves only 3 degrees from the captured physical
neutral, pauses so the direction can be observed, returns to neutral, then
broadcasts torque-off.  Run only with the dog secured on its stand.
"""
import argparse
import time

from single_leg_trot import (
    ACCELERATION,
    BAUD,
    MAX_TEMPERATURE_C,
    PORT,
    SPEED_TICKS_PER_SECOND,
    TICKS_PER_DEGREE,
    load_neutral,
    packet,
    read,
    serial,
    sync_write,
    torque_off,
    verify_servo,
    word,
    write,
)


HIP_ROLLS = {
    "rear-left": 7,
    "rear-right": 11,
    "front-right": 4,
    "front-left": 1,
}
PROBE_DEGREES = 3.0
HOLD_SECONDS = 1.0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leg", choices=HIP_ROLLS, required=True)
    parser.add_argument("--run", action="store_true", help="perform the 3-degree probe")
    args = parser.parse_args()
    servo_id = HIP_ROLLS[args.leg]
    neutral = load_neutral()[servo_id]
    target = neutral + round(PROBE_DEGREES * TICKS_PER_DEGREE)
    print(f"{args.leg} hip roll: ID {servo_id}, {neutral} -> {target} -> {neutral} ticks.")
    if not args.run:
        print("Preview only. Use --run only with the dog secured on the stand.")
        return
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        start, temperature, settings = verify_servo(bus, servo_id, neutral)
        print(f"Checked ID {servo_id}={start} ({temperature} C).", flush=True)
        try:
            write(bus, servo_id, 41, [ACCELERATION, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
            write(bus, servo_id, 40, [1])
            sync_write(bus, 42, 2, ((servo_id, word(target)),))
            time.sleep(HOLD_SECONDS)
            sync_write(bus, 42, 2, ((servo_id, word(neutral)),))
            time.sleep(HOLD_SECONDS)
            telemetry = read(bus, servo_id, 56, 8)
            if telemetry[7] >= MAX_TEMPERATURE_C:
                raise RuntimeError(f"ID {servo_id}: reached {telemetry[7]} C during hip-roll probe")
            position = int.from_bytes(telemetry[:2], "little")
            if abs(position - neutral) > 35:
                raise RuntimeError(f"ID {servo_id}: did not return to neutral; expected {neutral}, got {position}")
            print("Probe completed and returned to neutral.", flush=True)
        finally:
            torque_off(bus)
            bus.write(packet(servo_id, 3, [41, settings[0]]))
            bus.write(packet(servo_id, 3, [46, *settings[5:7]]))
            bus.flush()
            print("Broadcast torque-off sent.", flush=True)


if __name__ == "__main__":
    main()
