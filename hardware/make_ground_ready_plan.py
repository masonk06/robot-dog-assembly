"""Make a conservative copy of a learned replay for first ground-contact checks.

This tool deliberately changes only front-knee excursion.  It does not claim to
infer foot contact or alter the learned gait's phase timing.
"""
import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONT_KNEE_IDS = (3, 6)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=float, default=0.65,
                        help="Front-knee excursion multiplier around saved neutral (default: 0.65)")
    args = parser.parse_args()
    if not 0.0 < args.scale <= 1.0:
        parser.error("scale must be in (0, 1]")

    zero_data = json.loads((ROOT / "hardware/calibrations/zero-points-current.json").read_text())
    neutral = {joint["id"]: joint["neutral_ticks"] for joint in zero_data["joints"].values()}
    with args.input.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = list(reader)
    if fields is None or not rows or any(str(sid) not in fields for sid in range(1, 13)):
        raise ValueError("Expected a non-empty 12-servo replay CSV")

    for row in rows:
        for servo_id in FRONT_KNEE_IDS:
            original = int(row[str(servo_id)])
            row[str(servo_id)] = str(round(neutral[servo_id] + (original - neutral[servo_id]) * args.scale))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    metadata = {
        "source": str(args.input),
        "front_knee_ids": list(FRONT_KNEE_IDS),
        "front_knee_excursion_scale": args.scale,
        "note": "Conservative replay copy. Timing and all non-front-knee targets are unchanged.",
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} frames to {args.output}")


if __name__ == "__main__":
    main()
