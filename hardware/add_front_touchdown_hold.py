"""Add a brief front-leg target hold immediately after reference touchdown.

This is a conservative open-loop sim-to-real adaptation.  It derives touchdown
phase from the trained reference schedule (3.0 s cycle, front-left offset .25,
front-right offset .75).  It is not contact sensing and it does not modify the
saved neural-network weights.
"""
import argparse
import bisect
import csv
import json
from pathlib import Path


CYCLE_SECONDS = 3.0
LEGS = {
    "front_left": {"offset": 0.25, "ids": (4, 5, 6)},
    "front_right": {"offset": 0.75, "ids": (1, 2, 3)},
}
SWING_FRACTION = 0.20


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--hold-seconds", type=float, default=0.10,
                        help="Simulated seconds to hold immediately after touchdown (default: 0.10)")
    parser.add_argument("--max-front-tick-step", type=int, default=18,
                        help="Maximum target change per 20 ms frame for front-leg servos (default: 18)")
    args = parser.parse_args()
    if not 0 < args.hold_seconds < CYCLE_SECONDS * (1 - SWING_FRACTION):
        parser.error("hold-seconds must fit inside the reference stance interval")
    if not 0 < args.max_front_tick_step <= 20:
        parser.error("max-front-tick-step must be in [1, 20] to satisfy the receiver guard")

    with args.input.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if fields is None or not rows or any(str(sid) not in fields for sid in range(1, 13)):
        raise ValueError("Expected a non-empty 12-servo replay CSV")
    times = [float(row["time_seconds"]) for row in rows]

    held_frames = {leg: 0 for leg in LEGS}
    for index, row in enumerate(rows):
        now = times[index]
        phase = (now / CYCLE_SECONDS) % 1.0
        for leg, spec in LEGS.items():
            local = (phase - spec["offset"]) % 1.0
            touchdown = SWING_FRACTION
            hold_fraction = args.hold_seconds / CYCLE_SECONDS
            if touchdown <= local < touchdown + hold_fraction:
                # The last sample at/before reference touchdown is the planted target.
                touchdown_time = now - (local - touchdown) * CYCLE_SECONDS
                source_index = max(0, bisect.bisect_right(times, touchdown_time + 1e-9) - 1)
                source = rows[source_index]
                for servo_id in spec["ids"]:
                    row[str(servo_id)] = source[str(servo_id)]
                held_frames[leg] += 1

    # A hold can otherwise create a large target discontinuity at release.
    # Bound only the two front legs; the source trajectory for every other leg
    # is kept byte-for-byte as learned.
    for previous, row in zip(rows, rows[1:]):
        for servo_id in (1, 2, 3, 4, 5, 6):
            old = int(previous[str(servo_id)])
            desired = int(row[str(servo_id)])
            delta = max(-args.max_front_tick_step,
                        min(args.max_front_tick_step, desired - old))
            row[str(servo_id)] = str(old + delta)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    args.output.with_suffix(".json").write_text(json.dumps({
        "source": str(args.input),
        "cycle_seconds": CYCLE_SECONDS,
        "swing_fraction": SWING_FRACTION,
        "front_touchdown_hold_simulated_seconds": args.hold_seconds,
        "maximum_front_tick_step_per_20ms": args.max_front_tick_step,
        "held_frames": held_frames,
        "note": "Open-loop target hold after reference touchdown; no physical contact is inferred.",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} frames to {args.output}; held frames: {held_frames}")


if __name__ == "__main__":
    main()
