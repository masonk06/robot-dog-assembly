"""Run a cautious, in-air trot-like cycle on one RoboDog leg.

Default: print the planned rear-left trajectory only (no serial port access).
Motion:  python single_leg_trot.py --run

The initial motion profile is deliberately modest: the rear-left hip pitch
moves no more than 14 degrees and the knee no more than 16 degrees from the
user-confirmed physical neutral pose.  Waypoints are blended at 50 ms intervals
instead of using abrupt, stop-and-go moves.  The robot must be secured on its
stand with the tested leg clear of the stand and ground.  Every exit path
broadcasts torque-off to the entire bus.

This is a planar first-gait test, so hip roll stays unpowered at neutral.
"""
import argparse
import json
import time
from pathlib import Path

from servo_usb_scan import serial


PORT = "COM5"
BAUD = 1_000_000
TICKS_PER_DEGREE = 4096 / 360
SPEED_TICKS_PER_SECOND = 120
ACCELERATION = 20
MAX_TEMPERATURE_C = 45
MAX_START_OFFSET_TICKS = 35
INTERPOLATION_STEP_SECONDS = 0.05
ROOT = Path(__file__).parent

# Rear-left directions were physically checked: +hip is backward; +knee bends
# toward the body.  This curved joint-space path flexes before the forward swing,
# reaches forward while lifted, then extends and sweeps backward through stance.
# It intentionally avoids every front-leg restriction.
JOINTS = {
    "rear_left": {"hip_pitch": 8, "knee": 9},
}
PHASES = (
    ("neutral", 0.0, 0.0, 0.2),
    ("unweight", +2.0, +5.0, 0.8),
    ("lift and swing", -10.0, +14.0, 1.9),
    ("swing apex", -14.0, +16.0, 0.6),
    ("reach", -10.0, +5.0, 1.7),
    ("touchdown", -8.0, -2.0, 1.0),
    ("stance mid", 0.0, -2.0, 1.2),
    ("push-off", +12.0, -1.0, 1.8),
    ("return neutral", 0.0, 0.0, 1.8),
)


def packet(servo_id, instruction, params):
    body = bytes([servo_id, len(params) + 2, instruction, *params])
    return b"\xff\xff" + body + bytes([(~sum(body)) & 255])


def exchange(bus, servo_id, instruction, params):
    body = bytes([servo_id, len(params) + 2, instruction, *params])
    bus.reset_input_buffer()
    bus.write(b"\xff\xff" + body + bytes([(~sum(body)) & 255]))
    bus.flush()
    data = bus.read(64)
    for index in range(len(data) - 5):
        if data[index:index + 3] != bytes([255, 255, servo_id]):
            continue
        length = data[index + 3]
        frame = data[index:index + length + 4]
        if length >= 2 and len(frame) == length + 4 and sum(frame[2:]) & 255 == 255:
            if frame[4]:
                raise RuntimeError(f"ID {servo_id} reports status error {frame[4]}")
            return frame[5:-1]
    raise RuntimeError(f"No valid response from ID {servo_id}")


def read(bus, servo_id, address, count):
    value = exchange(bus, servo_id, 2, [address, count])
    if len(value) != count:
        raise RuntimeError(f"ID {servo_id}: incorrect read length")
    return value


def write(bus, servo_id, address, values):
    exchange(bus, servo_id, 3, [address, *values])


def sync_write(bus, address, value_size, values):
    """Broadcast one same-register update to multiple servos without replies."""
    params = [address, value_size]
    for servo_id, value in values:
        if len(value) != value_size:
            raise ValueError("Sync-write payload has an incorrect length")
        params.extend([servo_id, *value])
    bus.write(packet(254, 0x83, params))
    bus.flush()


def word(value):
    return list(value.to_bytes(2, "little"))


def target(neutral, degrees):
    value = neutral + round(degrees * TICKS_PER_DEGREE)
    if not 0 <= value <= 4095:
        raise ValueError(f"Target {value} is outside raw encoder range")
    return value


def load_neutral():
    return {int(key): value for key, value in json.loads(
        (ROOT / "physical_neutral_pose.json").read_text(encoding="utf-8")
    )["positions"].items()}


def describe(hip_neutral, knee_neutral):
    print("Rear-left in-air trot profile (no hip-roll command):")
    for name, hip_degrees, knee_degrees, duration_seconds in PHASES:
        print(
            f"  {name:15} hip={hip_degrees:+5.1f} deg ({target(hip_neutral, hip_degrees)}), "
            f"knee={knee_degrees:+5.1f} deg ({target(knee_neutral, knee_degrees)}), "
            f"duration={duration_seconds:.1f}s"
        )


def torque_off(bus):
    # Broadcast avoids relying on a response from a servo in a protection state.
    bus.write(packet(254, 3, [40, 0]))
    bus.flush()


def verify_servo(bus, servo_id, neutral):
    mode = read(bus, servo_id, 33, 1)[0]
    torque = read(bus, servo_id, 40, 1)[0]
    telemetry = read(bus, servo_id, 56, 8)
    position = int.from_bytes(telemetry[:2], "little")
    temperature = telemetry[7]
    if mode != 0 or torque != 0:
        raise RuntimeError(f"ID {servo_id}: expected position mode with torque off; mode={mode}, torque={torque}")
    if temperature >= MAX_TEMPERATURE_C:
        raise RuntimeError(f"ID {servo_id}: {temperature} C is too warm for a gait test")
    if abs(position - neutral) > MAX_START_OFFSET_TICKS:
        raise RuntimeError(
            f"ID {servo_id}: position {position} is not at physical neutral {neutral} "
            f"(difference {position - neutral:+d} ticks); no movement attempted"
        )
    return position, temperature, read(bus, servo_id, 41, 7)


def smoothstep(value):
    """Cubic zero-slope blend, which avoids abrupt velocity changes."""
    return value * value * (3 - 2 * value)


def move_phase(bus, hip_id, knee_id, hip_goal, knee_goal, previous, phase_name, duration_seconds):
    # Send a blended trajectory to both joints.  Synchronous broadcast writes
    # avoid serial-response delays that make individual writes look stair-stepped.
    steps = max(1, round(duration_seconds / INTERPOLATION_STEP_SECONDS))
    for step in range(1, steps + 1):
        blend = smoothstep(step / steps)
        hip_command = round(previous[0] + (hip_goal - previous[0]) * blend)
        knee_command = round(previous[1] + (knee_goal - previous[1]) * blend)
        sync_write(bus, 42, 2, ((hip_id, word(hip_command)), (knee_id, word(knee_command))))
        time.sleep(duration_seconds / steps)
    for servo_id, expected in ((hip_id, hip_goal), (knee_id, knee_goal)):
        telemetry = read(bus, servo_id, 56, 8)
        position = int.from_bytes(telemetry[:2], "little")
        if telemetry[7] >= MAX_TEMPERATURE_C:
            raise RuntimeError(f"ID {servo_id}: reached {telemetry[7]} C during {phase_name}")
        if abs(position - expected) > 35:
            raise RuntimeError(f"ID {servo_id}: missed {phase_name} goal; expected {expected}, got {position}")
    print(f"Completed {phase_name}.", flush=True)
    return hip_goal, knee_goal


def run(hip_id, knee_id, hip_neutral, knee_neutral, cycles):
    with serial.Serial(PORT, BAUD, timeout=0.1, write_timeout=1) as bus:
        hip_start, hip_temp, hip_settings = verify_servo(bus, hip_id, hip_neutral)
        knee_start, knee_temp, knee_settings = verify_servo(bus, knee_id, knee_neutral)
        print(
            f"Checked rear-left: hip ID {hip_id}={hip_start} ({hip_temp} C), "
            f"knee ID {knee_id}={knee_start} ({knee_temp} C).",
            flush=True,
        )
        try:
            # Set current positions as goals before torque is enabled, preventing a jump.
            for servo_id, start in ((hip_id, hip_start), (knee_id, knee_start)):
                write(bus, servo_id, 41, [ACCELERATION, *word(start), 0, 0, *word(SPEED_TICKS_PER_SECOND)])
            write(bus, hip_id, 40, [1])
            write(bus, knee_id, 40, [1])
            time.sleep(0.3)
            previous = (hip_start, knee_start)
            for cycle in range(1, cycles + 1):
                print(f"Cycle {cycle}/{cycles}", flush=True)
                for name, hip_degrees, knee_degrees, duration_seconds in PHASES:
                    previous = move_phase(
                        bus, hip_id, knee_id,
                        target(hip_neutral, hip_degrees), target(knee_neutral, knee_degrees),
                        previous, name, duration_seconds,
                    )
        finally:
            torque_off(bus)
            # Velocity/acceleration are RAM settings: restore them before leaving.
            for servo_id, settings in ((hip_id, hip_settings), (knee_id, knee_settings)):
                bus.write(packet(servo_id, 3, [41, settings[0]]))
                bus.write(packet(servo_id, 3, [46, *settings[5:7]]))
            bus.flush()
            print("Broadcast torque-off sent; rear-left leg is released.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="execute the motion; default is a no-motion trajectory preview")
    parser.add_argument("--cycles", type=int, default=1, choices=range(1, 4), metavar="1..3")
    args = parser.parse_args()
    ids = JOINTS["rear_left"]
    neutral = load_neutral()
    hip_neutral, knee_neutral = neutral[ids["hip_pitch"]], neutral[ids["knee"]]
    describe(hip_neutral, knee_neutral)
    if not args.run:
        print("Dry run only. Use --run only with the robot secured on the stand.")
        return
    run(ids["hip_pitch"], ids["knee"], hip_neutral, knee_neutral, args.cycles)


if __name__ == "__main__":
    main()
