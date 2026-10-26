"""Guided, torque-off manual safe-range calibration for the front-left leg.

Order: hip roll, hip pitch, knee pitch.  The program never sends a servo
command.  It reads two manually placed, backed-off safe endpoints per joint
and saves the smaller raw encoder value as ``minimum`` and the larger as
``maximum`` in manual_range_of_motion.json.

Do not force a hard stop.  At the first frame contact, cable tension, or other
resistance, move back 2-3 degrees before pressing Enter to capture a value.
"""
import json
from datetime import datetime

from record_manual_limits import JOINTS, OUT, load_records, measure
from single_leg_trot import BAUD, PORT, serial


FRONT_LEFT_ORDER = (
    ("front-left-hip-roll", "Hip roll"),
    ("front-left-hip-pitch", "Hip pitch"),
    ("front-left-knee", "Knee pitch"),
)


def capture_endpoint(bus, joint, title, prompt):
    servo_id = JOINTS[joint]
    input(f"\n{title} (ID {servo_id}) - {prompt}\nPress Enter only when the joint is backed off and safe: ")
    ticks, temperature = measure(bus, servo_id)
    print(f"Captured {ticks} ticks at {temperature} C.")
    return {"id": servo_id, "ticks": ticks, "temperature_c": temperature,
            "captured_local": datetime.now().astimezone().isoformat(timespec="seconds")}


def main():
    print("FRONT-LEFT MANUAL RANGE CALIBRATION")
    print("This tool sends no commands. Confirm the dog is on its stand and all torque is OFF.")
    input("Press Enter to check the three front-left servos: ")
    records = load_records()
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        # Read all three before asking the user to touch any of them.
        for joint, title in FRONT_LEFT_ORDER:
            position, temperature = measure(bus, JOINTS[joint])
            print(f"{title}: ID {JOINTS[joint]} at {position} ticks, {temperature} C, torque OFF.")
        for joint, title in FRONT_LEFT_ORDER:
            first = capture_endpoint(
                bus, joint, title,
                "move slowly in either direction until first resistance, then back off 2-3 degrees.",
            )
            second = capture_endpoint(
                bus, joint, title,
                "move to the opposite safe limit, again stopping at first resistance and backing off 2-3 degrees.",
            )
            low, high = sorted((first, second), key=lambda record: record["ticks"])
            low["note"] = "manual safe endpoint; smaller raw encoder value"
            high["note"] = "manual safe endpoint; larger raw encoder value"
            records["records"][joint] = {"minimum": low, "maximum": high}
            print(f"Recorded {title}: {low['ticks']}..{high['ticks']} ticks.")
    OUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"\nCalibration saved to {OUT.name}. No servo command was sent.")
    print("Keep front-left hip pitch out of any frame-contact region until we review these readings.")


if __name__ == "__main__":
    main()
