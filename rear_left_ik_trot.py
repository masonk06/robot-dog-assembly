"""Cartesian, inverse-kinematics trot test for the rear-left leg.

Default: preview the foot path and solved joint range; no motor communication.
Motion:  python rear_left_ik_trot.py --run --lift-mm 10

The path is derived from the rear-left hip, knee, and foot locations in the
MuJoCo/CAD model.  It keeps hip roll unpowered and generates a 15 mm fore-aft
foot stroke with a 6 mm lifted swing arc.  It begins and ends at the measured
physical neutral pose, so enabling torque cannot cause a path-start jump.

The physical knee installation is mirrored relative to the model's positive
knee axis: model-positive knee angle is written as a negative raw-tick change.
"""
import argparse
import math
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
    smoothstep,
    sync_write,
    torque_off,
    verify_servo,
    word,
    write,
)


LEG_CONFIG = {
    # The rear-left physical/model sign relationship was validated against the
    # MuJoCo 10 mm lift preview on hardware.
    "rear-left": {"hip": 8, "knee": 9, "hip_sign": +1, "knee_sign": -1, "status": "validated"},
    # Rear-right has the same physical directions as rear-left; IDs are 10/12.
    "rear-right": {"hip": 10, "knee": 12, "hip_sign": +1, "knee_sign": -1, "status": "candidate"},
    # Front-right directions were individually observed; its model transfer
    # remains a candidate until a one-leg test confirms it.
    "front-right": {"hip": 5, "knee": 6, "hip_sign": +1, "knee_sign": +1, "status": "candidate"},
}
CYCLE_SECONDS = 8.0
UPDATE_SECONDS = 0.05
SWING_FRACTION = 0.40
STRIDE_M = 0.015
SWING_HEIGHT_M = 0.006
MAX_HIP_DEGREES = 18.0
MAX_KNEE_DEGREES = 25.0

# x/z positions in metres, relative to the rear-left hip-pitch axis.  These
# are the vectors encoded by mujoco_v2/robot_dog_v2.xml at neutral.
UPPER = (0.030752551, -0.047093570)  # hip pitch -> knee pitch
LOWER = (-0.045000000, -0.070000000)  # knee pitch -> foot site
L1 = math.hypot(*UPPER)
L2 = math.hypot(*LOWER)
ALPHA = math.atan2(UPPER[1], UPPER[0])
BETA = math.atan2(LOWER[1], LOWER[0])
NEUTRAL_FOOT = (UPPER[0] + LOWER[0], UPPER[1] + LOWER[1])
NEUTRAL_ELB_BRANCH = BETA - ALPHA  # Negative branch passes through q=(0, 0).


def inverse_kinematics(x, z):
    """Solve the model's 2-DOF pitch chain; q=0 is the physical neutral."""
    radius_squared = x * x + z * z
    cosine = (radius_squared - L1 * L1 - L2 * L2) / (2 * L1 * L2)
    if not -1.0 <= cosine <= 1.0:
        raise ValueError(f"Foot target ({x:.4f}, {z:.4f}) is outside the reachable workspace")
    # Preserve the CAD's neutral elbow configuration rather than flipping to
    # the alternate mathematical solution.
    elbow = -math.acos(max(-1.0, min(1.0, cosine))) if NEUTRAL_ELB_BRANCH < 0 else math.acos(cosine)
    shoulder = math.atan2(z, x) - math.atan2(L2 * math.sin(elbow), L1 + L2 * math.cos(elbow))
    hip = shoulder - ALPHA
    knee = elbow - NEUTRAL_ELB_BRANCH
    return hip, knee


def foot_target(phase):
    """Lift and travel forward first, then sweep backward through stance."""
    x0, z0 = NEUTRAL_FOOT
    if phase < SWING_FRACTION:
        progress = phase / SWING_FRACTION
        return (
            x0 - STRIDE_M * smoothstep(progress),
            z0 + SWING_HEIGHT_M * math.sin(math.pi * progress),
        )
    progress = (phase - SWING_FRACTION) / (1 - SWING_FRACTION)
    return (
        x0 - STRIDE_M + STRIDE_M * smoothstep(progress),
        z0,
    )


def trajectory(samples):
    solved = []
    for index in range(samples + 1):
        phase = index / samples
        x, z = foot_target(phase)
        hip, knee = inverse_kinematics(x, z)
        solved.append((phase, x, z, hip, knee))
    return solved


def target_ticks(neutral_ticks, radians, direction_sign):
    value = neutral_ticks + round(direction_sign * math.degrees(radians) * TICKS_PER_DEGREE)
    if not 0 <= value <= 4095:
        raise ValueError(f"Servo target {value} is outside its raw encoder range")
    return value


def describe(path, hip_neutral, knee_neutral, config):
    hip_degrees = [math.degrees(item[3]) for item in path]
    knee_degrees = [math.degrees(item[4]) for item in path]
    x_values = [item[1] for item in path]
    z_values = [item[2] for item in path]
    if max(map(abs, hip_degrees)) > MAX_HIP_DEGREES or max(map(abs, knee_degrees)) > MAX_KNEE_DEGREES:
        raise ValueError("IK path exceeds the intentionally conservative first-test angle envelope")
    print("Rear-left IK foot path (hip roll remains unpowered):")
    print(f"  fore-aft stroke: {(max(x_values) - min(x_values)) * 1000:.1f} mm")
    print(f"  swing lift:      {(max(z_values) - NEUTRAL_FOOT[1]) * 1000:.1f} mm")
    print(f"  hip pitch:       {min(hip_degrees):+.1f} to {max(hip_degrees):+.1f} deg")
    print(f"  knee pitch:      {min(knee_degrees):+.1f} to {max(knee_degrees):+.1f} deg")
    print(
        f"  raw targets:     hip {min(target_ticks(hip_neutral, item[3], config['hip_sign']) for item in path)}.."
        f"{max(target_ticks(hip_neutral, item[3], config['hip_sign']) for item in path)}, knee "
        f"{min(target_ticks(knee_neutral, item[4], config['knee_sign']) for item in path)}.."
        f"{max(target_ticks(knee_neutral, item[4], config['knee_sign']) for item in path)}"
    )


def run(path, hip_neutral, knee_neutral, config):
    hip_id, knee_id = config["hip"], config["knee"]
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        hip_start, hip_temp, hip_settings = verify_servo(bus, hip_id, hip_neutral)
        knee_start, knee_temp, knee_settings = verify_servo(bus, knee_id, knee_neutral)
        print(
            f"Checked leg: hip ID {hip_id}={hip_start} ({hip_temp} C), "
            f"knee ID {knee_id}={knee_start} ({knee_temp} C).",
            flush=True,
        )
        try:
            for servo_id, start in ((hip_id, hip_start), (knee_id, knee_start)):
                write(bus, servo_id, 41, [ACCELERATION, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
            write(bus, hip_id, 40, [1])
            write(bus, knee_id, 40, [1])
            for phase, x, z, hip, knee in path:
                sync_write(
                    bus, 42, 2,
                    ((hip_id, word(target_ticks(hip_neutral, hip, config["hip_sign"]))),
                     (knee_id, word(target_ticks(knee_neutral, knee, config["knee_sign"]))),),
                )
                time.sleep(UPDATE_SECONDS)
            for servo_id, expected in ((hip_id, hip_neutral), (knee_id, knee_neutral)):
                telemetry = read(bus, servo_id, 56, 8)
                position = int.from_bytes(telemetry[:2], "little")
                if telemetry[7] >= MAX_TEMPERATURE_C:
                    raise RuntimeError(f"ID {servo_id}: reached {telemetry[7]} C during IK trot")
                if abs(position - expected) > 35:
                    raise RuntimeError(f"ID {servo_id}: did not return to neutral; expected {expected}, got {position}")
            print("IK cycle completed and returned to neutral.", flush=True)
        finally:
            torque_off(bus)
            for servo_id, settings in ((hip_id, hip_settings), (knee_id, knee_settings)):
                bus.write(packet(servo_id, 3, [41, settings[0]]))
                bus.write(packet(servo_id, 3, [46, *settings[5:7]]))
            bus.flush()
            print("Broadcast torque-off sent; rear-left leg is released.", flush=True)


def main():
    global SWING_HEIGHT_M
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="execute one in-air IK cycle")
    parser.add_argument("--leg", choices=LEG_CONFIG, default="rear-left", help="leg to preview or test (default: rear-left)")
    parser.add_argument("--lift-mm", type=float, default=6.0, help="swing lift in millimetres (default: 6; maximum: 10)")
    args = parser.parse_args()
    if not 0 < args.lift_mm <= 10:
        raise SystemExit("--lift-mm must be greater than 0 and no more than 10 for the current hardware test")
    SWING_HEIGHT_M = args.lift_mm / 1000
    neutral = load_neutral()
    config = LEG_CONFIG[args.leg]
    hip_id, knee_id = config["hip"], config["knee"]
    path = trajectory(round(CYCLE_SECONDS / UPDATE_SECONDS))
    print(f"Leg: {args.leg} ({config['status']} physical-to-model mapping)")
    describe(path, neutral[hip_id], neutral[knee_id], config)
    if not args.run:
        print("Preview only. Use --run only with the robot secured on the stand.")
        return
    run(path, neutral[hip_id], neutral[knee_id], config)


if __name__ == "__main__":
    main()
