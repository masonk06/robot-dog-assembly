"""Guided torque-off manual safe-range calibration for the remaining RoboDog legs.

This continues the front-left process for front-right, rear-left, and
rear-right.  It only reads encoder positions after you manually place each
backed-off safe endpoint; it never writes to a servo or changes torque.
"""
import argparse
import json
from datetime import datetime

from record_manual_limits import JOINTS, OUT, load_records, measure
from single_leg_trot import BAUD, PORT, serial


LEGS = {
    "front-right": (
        ("front-right-hip-roll", "Hip roll"),
        ("front-right-hip-pitch", "Hip pitch"),
        ("front-right-knee", "Knee pitch"),
    ),
    "rear-left": (
        ("rear-left-hip-roll", "Hip roll"),
        ("rear-left-hip-pitch", "Hip pitch"),
        ("rear-left-knee", "Knee pitch"),
    ),
    "rear-right": (
        ("rear-right-hip-roll", "Hip roll"),
        ("rear-right-hip-pitch", "Hip pitch"),
        ("rear-right-knee", "Knee pitch"),
    ),
}


def capture(bus, joint, title, prompt):
    servo_id = JOINTS[joint]
    input(f"\n{title} (ID {servo_id}) - {prompt}\nPress Enter only when it is backed off and safe: ")
    ticks, temperature = measure(bus, servo_id)
    print(f"Captured {ticks} ticks at {temperature} C.")
    return {
        "id": servo_id,
        "ticks": ticks,
        "temperature_c": temperature,
        "captured_local": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def calibrate(bus, records, leg):
    print(f"\n--- {leg.upper()} ---")
    sequence = LEGS[leg]
    for joint, title in sequence:
        position, temperature = measure(bus, JOINTS[joint])
        print(f"{title}: ID {JOINTS[joint]} at {position} ticks, {temperature} C, torque OFF.")
    for joint, title in sequence:
        first = capture(bus, joint, title, "move in either direction to first resistance, then back off 2-3 degrees")
        second = capture(bus, joint, title, "move to the opposite safe limit, again stopping at first resistance and backing off")
        low, high = sorted((first, second), key=lambda record: record["ticks"])
        low["note"] = "manual safe endpoint; smaller raw encoder value"
        high["note"] = "manual safe endpoint; larger raw encoder value"
        records["records"][joint] = {"minimum": low, "maximum": high}
        print(f"Recorded {title}: {low['ticks']}..{high['ticks']} ticks.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--leg", choices=(*LEGS, "all"), default="all", help="leg to calibrate (default: all remaining legs)")
    args = parser.parse_args()
    requested = tuple(LEGS) if args.leg == "all" else (args.leg,)
    print("MANUAL RANGE CALIBRATION - NO SERVO COMMANDS WILL BE SENT")
    print("Secure the dog, ensure every selected servo has torque OFF, and never force a hard stop.")
    input("Press Enter to begin: ")
    records = load_records()
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        for leg in requested:
            calibrate(bus, records, leg)
    OUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"\nSaved authoritative manual endpoints to {OUT.name}.")
    print("Future hardware trajectories must remain inside these endpoints with an added safety margin.")


if __name__ == "__main__":
    main()
