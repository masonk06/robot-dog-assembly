"""Generate a conservative, training-free P2S IK diagnostic trajectory.

This script has no serial, ROS, or servo dependency.  It creates model-angle
CSV samples for a slow one-leg-at-a-time exercise so the same motion can first
be reviewed in MuJoCo and only later converted through a verified physical
joint map.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path


LEGS = ("rear_left", "front_right", "rear_right", "front_left")
JOINTS = tuple(f"{leg}_{joint}" for leg in (
    "front_left", "front_right", "rear_left", "rear_right"
) for joint in ("hip_roll", "hip_pitch", "knee_pitch"))

# Pitch-chain vectors from the P2S MuJoCo neutral model, metres.
UPPER = (0.030752551, -0.047093570)
LOWER = (-0.045000000, -0.070000000)
L1, L2 = math.hypot(*UPPER), math.hypot(*LOWER)
ALPHA, BETA = math.atan2(UPPER[1], UPPER[0]), math.atan2(LOWER[1], LOWER[0])
NEUTRAL_FOOT = (UPPER[0] + LOWER[0], UPPER[1] + LOWER[1])
NEUTRAL_ELB_BRANCH = BETA - ALPHA


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def inverse_kinematics(x: float, z: float) -> tuple[float, float]:
    """Solve the P2S pitch chain using the branch through model zero."""
    cosine = (x * x + z * z - L1 * L1 - L2 * L2) / (2.0 * L1 * L2)
    if not -1.0 <= cosine <= 1.0:
        raise ValueError(f"Foot target ({x:.4f}, {z:.4f}) is unreachable")
    elbow = -math.acos(cosine) if NEUTRAL_ELB_BRANCH < 0 else math.acos(cosine)
    shoulder = math.atan2(z, x) - math.atan2(L2 * math.sin(elbow), L1 + L2 * math.cos(elbow))
    return shoulder - ALPHA, elbow - NEUTRAL_ELB_BRANCH


def swing_target(progress: float, stride_m: float, lift_m: float) -> tuple[float, float]:
    """Closed lift-forward-return arc; begins and ends at model zero pose."""
    x0, z0 = NEUTRAL_FOOT
    if progress <= 0.5:
        advance = smoothstep(progress * 2.0)
    else:
        advance = smoothstep((1.0 - progress) * 2.0)
    return x0 - stride_m * advance, z0 + lift_m * math.sin(math.pi * progress)


def pose_at(time_s: float, cycle_s: float, stride_m: float, lift_m: float) -> dict[str, float]:
    """One swing leg at a time; every other joint remains at model zero."""
    values = {joint: 0.0 for joint in JOINTS}
    phase = (time_s % cycle_s) / cycle_s
    leg_index = min(len(LEGS) - 1, int(phase * len(LEGS)))
    local = phase * len(LEGS) - leg_index
    leg = LEGS[leg_index]
    hip, knee = inverse_kinematics(*swing_target(local, stride_m, lift_m))
    values[f"{leg}_hip_pitch"] = hip
    values[f"{leg}_knee_pitch"] = knee
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seconds", type=float, default=16.0)
    parser.add_argument("--cycle-seconds", type=float, default=8.0)
    parser.add_argument("--stride-mm", type=float, default=8.0)
    parser.add_argument("--lift-mm", type=float, default=5.0)
    parser.add_argument("--sample-hz", type=float, default=20.0)
    args = parser.parse_args()
    if not (0 < args.seconds <= 60 and 4 <= args.cycle_seconds <= 20):
        parser.error("seconds must be 0..60 and cycle-seconds must be 4..20")
    if not (1 <= args.stride_mm <= 12 and 1 <= args.lift_mm <= 8 and 5 <= args.sample_hz <= 50):
        parser.error("diagnostic limits: stride 1..12 mm, lift 1..8 mm, sample rate 5..50 Hz")
    samples = round(args.seconds * args.sample_hz)
    rows = []
    for index in range(samples + 1):
        time_s = index / args.sample_hz
        rows.append({"time_seconds": time_s, **pose_at(
            time_s, args.cycle_seconds, args.stride_mm / 1000.0, args.lift_mm / 1000.0
        )})
    ranges = {
        joint: [min(row[joint] for row in rows), max(row[joint] for row in rows)]
        for joint in JOINTS
    }
    max_pitch_deg = max(abs(value) for joint in JOINTS for value in ranges[joint]
                        if joint.endswith(("hip_pitch", "knee_pitch"))) * 180.0 / math.pi
    if max_pitch_deg > 18.0:
        raise RuntimeError(f"Diagnostic exceeds 18 degree pitch envelope ({max_pitch_deg:.2f})")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=("time_seconds", *JOINTS))
        writer.writeheader()
        writer.writerows(rows)
    report = {
        "status": "offline_model_angle_trajectory_only",
        "cycle_order": list(LEGS),
        "seconds": args.seconds,
        "cycle_seconds": args.cycle_seconds,
        "stride_mm": args.stride_mm,
        "lift_mm": args.lift_mm,
        "sample_hz": args.sample_hz,
        "joint_ranges_radians": ranges,
        "note": "No physical encoder mapping or serial commands are produced by this script.",
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
