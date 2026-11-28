"""Generate an offline, four-beat IK crawl reference for the P2S model.

This is a kinematic reference for MuJoCo review and later policy training.
It deliberately has no serial or hardware dependency.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from generate_ik_diagnostic import JOINTS, NEUTRAL_FOOT, inverse_kinematics, smoothstep


# One swing leg at a time preserves a three-foot support triangle.
LEGS = ("rear_left", "front_right", "rear_right", "front_left")
SWING_FRACTION = 0.25


def leg_phase(leg: str, cycle_phase: float) -> float:
    return (cycle_phase - LEGS.index(leg) / len(LEGS)) % 1.0


def foot_target(local_phase: float, stroke_m: float, lift_m: float) -> tuple[float, float]:
    """Return one foot target in its hip-pitch plane.

    During swing, the foot travels from rear to front while lifted. During
    stance it travels slowly back under the body, approximating a planted foot
    while the body advances.  The stroke is intentionally small for a
    quasi-static crawl reference.
    """
    x0, z0 = NEUTRAL_FOOT
    rear, front = x0 + stroke_m / 2.0, x0 - stroke_m / 2.0
    if local_phase < SWING_FRACTION:
        progress = smoothstep(local_phase / SWING_FRACTION)
        return rear + (front - rear) * progress, z0 + lift_m * math.sin(math.pi * progress)
    progress = smoothstep((local_phase - SWING_FRACTION) / (1.0 - SWING_FRACTION))
    return front + (rear - front) * progress, z0


def hip_roll(leg: str, local_phase: float, sway_rad: float) -> float:
    """Shift toward the planted side while the opposite foot swings."""
    if local_phase >= SWING_FRACTION:
        return 0.0
    side = -1.0 if leg.endswith("left") else 1.0
    return side * sway_rad * math.sin(math.pi * local_phase / SWING_FRACTION)


def pose_at(time_s: float, cycle_s: float, stroke_m: float, lift_m: float,
            sway_rad: float) -> dict[str, float]:
    values = {joint: 0.0 for joint in JOINTS}
    cycle_phase = (time_s % cycle_s) / cycle_s
    for leg in LEGS:
        local = leg_phase(leg, cycle_phase)
        hip, knee = inverse_kinematics(*foot_target(local, stroke_m, lift_m))
        values[f"{leg}_hip_roll"] = hip_roll(leg, local, sway_rad)
        values[f"{leg}_hip_pitch"] = hip
        values[f"{leg}_knee_pitch"] = knee
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=16.0)
    parser.add_argument("--cycle-seconds", type=float, default=8.0)
    parser.add_argument("--stroke-mm", type=float, default=8.0)
    parser.add_argument("--lift-mm", type=float, default=5.0)
    parser.add_argument("--sway-deg", type=float, default=2.0)
    parser.add_argument("--sample-hz", type=float, default=20.0)
    args = parser.parse_args()
    if not (4 <= args.cycle_seconds <= 20 and 0 < args.seconds <= 60):
        parser.error("cycle-seconds must be 4..20 and seconds must be 0..60")
    if not (1 <= args.stroke_mm <= 12 and 1 <= args.lift_mm <= 8 and 0 <= args.sway_deg <= 4):
        parser.error("crawl limits: stroke 1..12 mm, lift 1..8 mm, sway 0..4 deg")
    if not 5 <= args.sample_hz <= 50:
        parser.error("sample-hz must be 5..50")
    rows = [{"time_seconds": i / args.sample_hz, **pose_at(
        i / args.sample_hz, args.cycle_seconds, args.stroke_mm / 1000.0,
        args.lift_mm / 1000.0, math.radians(args.sway_deg))}
        for i in range(round(args.seconds * args.sample_hz) + 1)]
    ranges = {joint: [min(row[joint] for row in rows), max(row[joint] for row in rows)] for joint in JOINTS}
    if max(abs(value) for limits in ranges.values() for value in limits) > 0.30:
        raise RuntimeError("crawl reference exceeds 0.30 radian joint envelope")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("time_seconds", *JOINTS))
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps({"status": "offline_ik_crawl_reference_only", "cycle_order": LEGS,
                      "stroke_mm": args.stroke_mm, "lift_mm": args.lift_mm,
                      "sway_deg": args.sway_deg, "joint_ranges_radians": ranges}, indent=2))


if __name__ == "__main__":
    main()
