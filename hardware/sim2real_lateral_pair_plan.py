"""Dry-run translation of the MuJoCo lateral-pair gait into STS3215 targets.

This program never opens the serial port and cannot move the robot.  It exists
to make the sim-to-real conversion reviewable before any hardware command is
considered.  The current gait is rear-left -> front-left, then rear-right ->
front-right, with each front foot delayed by 12% of the cycle.
"""
import argparse
import json
import sys
from pathlib import Path
from joint_mapping import KNEE_MODEL_TO_SERVO_SIGN

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT.parent / "simulation" / "mujoco"))

import rear_left_ik_trot as ik  # noqa: E402
import view_dog_walk as gait  # noqa: E402
from single_leg_trot import TICKS_PER_DEGREE, load_neutral  # noqa: E402


# Only rear-left pitch signs have been physically checked.  Front-left is
# deliberately blocked because ID 2 has a known frame-contact/direction issue.
# Other legs remain candidates until their one-leg, in-air tests are completed.
TRANSFER_STATUS = {
    "rear_left": {"hip": 8, "knee": 9, "hip_sign": +1, "knee_sign": KNEE_MODEL_TO_SERVO_SIGN["rear_left"], "status": "validated"},
    "front_left": {"status": "BLOCKED: front-left hip-pitch ID 2 has unresolved direction/frame-contact risk"},
    "rear_right": {"hip": 10, "knee": 12, "hip_sign": +1, "knee_sign": KNEE_MODEL_TO_SERVO_SIGN["rear_right"], "status": "validated: matched rear-left in-air path on 2026-10-24"},
    "front_right": {"hip": 5, "knee": 6, "hip_sign": +1, "knee_sign": KNEE_MODEL_TO_SERVO_SIGN["front_right"], "status": "direction corrected by live comparison 2026-10-26"},
}
MANUAL_LIMITS_PATH = ROOT / "manual_range_of_motion.json"
MANUAL_MARGIN_TICKS = 25  # roughly 2.2 degrees, applied inside every endpoint


def ticks(neutral, radians, sign):
    value = neutral + round(sign * radians * 180 / 3.141592653589793 * TICKS_PER_DEGREE)
    if not 0 <= value <= 4095:
        raise ValueError(f"Generated encoder target {value} is outside 0..4095")
    return value


def joint_ranges(leg, samples, neutral):
    config = TRANSFER_STATUS[leg]
    values = []
    for index in range(samples + 1):
        phase = index / samples
        x, z = gait.walk_foot_target(gait.leg_phase(leg, phase))
        hip, knee = ik.inverse_kinematics(x, z)
        values.append((ticks(neutral[config["hip"]], hip, config["hip_sign"]),
                       ticks(neutral[config["knee"]], knee, config["knee_sign"])))
    hips, knees = zip(*values)
    return min(hips), max(hips), min(knees), max(knees)


def manual_ranges():
    if not MANUAL_LIMITS_PATH.exists():
        return {}
    return json.loads(MANUAL_LIMITS_PATH.read_text(encoding="utf-8")).get("records", {})


def report_manual_gate(label, target_min, target_max, records):
    record = records.get(label)
    if not record:
        print(f"    manual range: NOT CAPTURED - target is planning-only")
        return False
    safe_min = record["minimum"]["ticks"] + MANUAL_MARGIN_TICKS
    safe_max = record["maximum"]["ticks"] - MANUAL_MARGIN_TICKS
    permitted = safe_min <= target_min and target_max <= safe_max
    status = "inside manual envelope" if permitted else "OUTSIDE manual envelope"
    print(f"    manual safe envelope: {safe_min}..{safe_max} ticks -> {status}")
    return permitted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stride-mm", type=float, default=20.0, help="foot stroke to translate (default: 20)")
    parser.add_argument("--lift-mm", type=float, default=10.0, help="foot lift to translate (default: 10)")
    parser.add_argument("--samples", type=int, default=200, help="samples per 10-second cycle (default: 200)")
    args = parser.parse_args()
    if not 5 <= args.stride_mm <= 40 or not 0 < args.lift_mm <= 20 or args.samples < 20:
        raise SystemExit("Use a 5..40 mm stride, 0..20 mm lift, and at least 20 samples")

    gait.STRIDE_M = args.stride_mm / 1000
    ik.SWING_HEIGHT_M = args.lift_mm / 1000
    neutral = load_neutral()
    measured = manual_ranges()
    print("SIM-TO-REAL DRY RUN - no serial port is opened and no servo can move.")
    print(f"Gait: rear-left -> front-left (12% delayed), then rear-right -> front-right; "
          f"stroke {args.stride_mm:.0f} mm, lift {args.lift_mm:.0f} mm.")
    print("Hip-roll commands are withheld: their physical signs have not been validated.")
    for leg in gait.LEGS:
        config = TRANSFER_STATUS[leg]
        print(f"\n{leg.replace('_', ' ').title()}: {config['status']}")
        if "hip" not in config:
            continue
        hip_min, hip_max, knee_min, knee_max = joint_ranges(leg, args.samples, neutral)
        print(f"  hip pitch ID {config['hip']}: {hip_min}..{hip_max} ticks")
        report_manual_gate(f"{leg.replace('_', '-')}-hip-pitch", hip_min, hip_max, measured)
        print(f"  knee pitch ID {config['knee']}: {knee_min}..{knee_max} ticks")
        report_manual_gate(f"{leg.replace('_', '-')}-knee", knee_min, knee_max, measured)
    print("\nHardware gate: do not run a paired/full-body gait until front-left ID 2 has a"
          " reviewed safe mapping and the physical hip-roll directions are verified.")


if __name__ == "__main__":
    main()
