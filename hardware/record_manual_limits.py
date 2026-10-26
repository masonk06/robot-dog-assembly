"""Record manually measured safe joint limits without commanding the RoboDog.

Torque must already be OFF.  Move one joint by hand slowly, stop before hard
contact/cable tension, back off 2-3 degrees, then run this program to record
that endpoint.  This program only reads servo state; it never writes to the
servos or changes torque.
"""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from single_leg_trot import BAUD, MAX_TEMPERATURE_C, PORT, read, serial


ROOT = Path(__file__).parent
OUT = ROOT / "manual_range_of_motion.json"
JOINTS = {
    "front-left-hip-roll": 1, "front-left-hip-pitch": 2, "front-left-knee": 3,
    "front-right-hip-roll": 4, "front-right-hip-pitch": 5, "front-right-knee": 6,
    "rear-left-hip-roll": 7, "rear-left-hip-pitch": 8, "rear-left-knee": 9,
    "rear-right-hip-pitch": 10, "rear-right-hip-roll": 11, "rear-right-knee": 12,
}


def measure(bus, servo_id):
    torque = read(bus, servo_id, 40, 1)[0]
    telemetry = read(bus, servo_id, 56, 8)
    position = int.from_bytes(telemetry[:2], "little")
    temperature = telemetry[7]
    if torque != 0:
        raise RuntimeError(f"ID {servo_id} still has torque ON; turn torque off before moving it by hand")
    if temperature >= MAX_TEMPERATURE_C:
        raise RuntimeError(f"ID {servo_id} is {temperature} C; let it cool before calibration")
    return position, temperature


def load_records():
    if OUT.exists():
        return json.loads(OUT.read_text(encoding="utf-8"))
    return {
        "description": "Manual safe endpoints. Each reading was captured torque-off after backing away from first contact/cable tension.",
        "units": "raw STS3215 encoder ticks (0..4095)",
        "records": {},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--joint", choices=JOINTS, required=True, help="joint being moved manually")
    parser.add_argument("--endpoint", choices=("minimum", "maximum"), help="record the current backed-off safe endpoint")
    parser.add_argument("--watch", action="store_true", help="display live encoder readings; press Ctrl+C to stop")
    parser.add_argument("--note", default="", help="optional short description, such as 'frame clearance'")
    args = parser.parse_args()
    if not args.watch and not args.endpoint:
        parser.error("choose --watch or supply --endpoint")
    servo_id = JOINTS[args.joint]
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        if args.watch:
            print(f"Watching {args.joint}, ID {servo_id}. Torque remains OFF; Ctrl+C when finished.")
            try:
                while True:
                    position, temperature = measure(bus, servo_id)
                    print(f"{position:4d} ticks, {temperature} C", flush=True)
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("Watch stopped; no value recorded.")
            return
        position, temperature = measure(bus, servo_id)
    records = load_records()
    record = {
        "id": servo_id,
        "ticks": position,
        "temperature_c": temperature,
        "note": args.note,
        "captured_local": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    records["records"].setdefault(args.joint, {})[args.endpoint] = record
    OUT.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Recorded {args.joint} {args.endpoint}: {position} ticks ({temperature} C).")
    print(f"Saved to {OUT.name}. No servo command was sent.")


if __name__ == "__main__":
    main()
