"""Create a six-second, 144 Hz P2S crawl reference without hardware I/O."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simulation/p2s_crawl"))
from generate_ik_crawl import LEGS, pose_at
from generate_ik_diagnostic import JOINTS

CYCLE_SECONDS = 6
SAMPLE_HZ = 144
SAMPLES_PER_CYCLE = CYCLE_SECONDS * SAMPLE_HZ


def generate_rows(cycles=1, cycle_seconds=6.0, stroke_mm=8.0, lift_mm=5.0):
    if not isinstance(cycles, int) or not 1 <= cycles <= 10:
        raise ValueError("cycles must be an integer from 1 to 10")
    if not math.isfinite(cycle_seconds) or not 4 <= cycle_seconds <= 20:
        raise ValueError("cycle-seconds must be finite and 4..20")
    if not 1 <= stroke_mm <= 30 or not 1 <= lift_mm <= 15:
        raise ValueError("stroke must be 1..30 mm and lift 1..15 mm")
    intervals = round(cycle_seconds * SAMPLE_HZ)
    if not math.isclose(intervals / SAMPLE_HZ, cycle_seconds, abs_tol=1e-10, rel_tol=0):
        raise ValueError("cycle duration must contain a whole number of 144 Hz intervals")
    # Include the closing endpoint for finite replay. When looping, omit that
    # duplicate endpoint and schedule each cycle on the absolute time grid.
    return [{"time_seconds": i / SAMPLE_HZ, **pose_at(
        i / SAMPLE_HZ, cycle_seconds, stroke_mm / 1000, lift_mm / 1000, 0.0)}
        for i in range(cycles * intervals + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, default=1)
    parser.add_argument("--cycle-seconds", type=float, default=6.0)
    parser.add_argument("--stroke-mm", type=float, default=8.0)
    parser.add_argument("--lift-mm", type=float, default=5.0)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "runs/pi-crawl" /
                        datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    args = parser.parse_args()
    rows = generate_rows(args.cycles, args.cycle_seconds, args.stroke_mm, args.lift_mm)
    if any(not math.isfinite(row[j]) or abs(row[j]) > .40 for row in rows for j in JOINTS):
        raise ValueError("Reference exceeds the 0.40 radian envelope")
    args.output_dir.mkdir(parents=True, exist_ok=False)
    path = args.output_dir / "crawl-model-angles.csv"
    with path.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=["time_seconds", *JOINTS])
        writer.writeheader()
        writer.writerows(rows)
    metadata = dict(status="offline_model_reference_only", cycle_seconds=args.cycle_seconds,
                    sample_hz=SAMPLE_HZ, samples_per_cycle=round(args.cycle_seconds * SAMPLE_HZ),
                    cycles=args.cycles, rows_including_closing_endpoint=len(rows),
                    duration_seconds=args.cycles * args.cycle_seconds, units="radians",
                    stroke_mm=args.stroke_mm, lift_mm=args.lift_mm, sway_deg=0, swing_order=LEGS,
                    joint_envelope_rad=0.40, hardware_validated=False)
    (args.output_dir / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(f"Created {path}: {args.cycles} x {args.cycle_seconds:g}-second cycles at 144 Hz; no hardware I/O.")


if __name__ == "__main__":
    main()
