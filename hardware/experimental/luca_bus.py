
import argparse
import time
from scservo_sdk import PortHandler, sms_sts, COMM_SUCCESS

PORT = "COM5"
BAUD = 1_000_000

# policy joint order, physical servo ids, neutral encoder positions
JOINTS = [
    ("front_left_hip_roll", 1, 2079),
    ("front_left_hip_pitch", 2, 1782),
    ("front_left_knee_pitch", 3, 1855),
    ("front_right_hip_roll", 4, 2101),
    ("front_right_hip_pitch", 5, 1840),
    ("front_right_knee_pitch", 6, 1928),
    ("rear_left_hip_roll", 7, 2047),
    ("rear_left_hip_pitch", 8, 1749),
    ("rear_left_knee_pitch", 9, 1698),
    ("rear_right_hip_roll", 11, 2048),
    ("rear_right_hip_pitch", 10, 1874),
    ("rear_right_knee_pitch", 12, 1778),
]

class LucaBus:
    def __init__(self):
        self.port = PortHandler(PORT)
        if not self.port.openPort():
            raise RuntimeError(f"Cannot open {PORT}")
        if not self.port.setBaudRate(BAUD):
            self.port.closePort()
            raise RuntimeError("Cannot set baud rate")
        self.servo = sms_sts(self.port)

    def check(self, result, error):
        if result != COMM_SUCCESS or error != 0:
            raise RuntimeError(
                f"Servo communication error: {result}, {error}"
            )

    def read_position(self, servo_id):
        pos, result, error = self.servo.ReadPos(servo_id)
        self.check(result, error)
        if not 0 <= pos <= 4095:
            raise RuntimeError(f"Invalid position: {pos}")
        return pos

    def set_torque(self, servo_id, enabled):
        result, error = self.servo.write1ByteTxRx(
            servo_id, 40, int(enabled)
        )
        self.check(result, error)

    def write_position(self, servo_id, ticks):
        if not 0 <= ticks <= 4095:
            raise ValueError("Target outside encoder range")
        result, error = self.servo.WritePosEx(
            servo_id, ticks, 80, 10
        )
        self.check(result, error)

    def read_all(self):
        for name, servo_id, neutral in JOINTS:
            pos = self.read_position(servo_id)
            print(
                f"{servo_id:2d} {name:25s} "
                f"position={pos:4d} delta={pos-neutral:+5d}"
            )

    def test_joint(self, servo_id):
        matches = [j for j in JOINTS if j[1] == servo_id]
        if not matches:
            raise ValueError("Unknown servo ID")

        name, _, neutral = matches[0]
        start = self.read_position(servo_id)
        target = start + 8

        if abs(start - neutral) > 120:
            raise RuntimeError(
                "Servo too far from captured neutral pose"
            )
        if target > 4095 or abs(target - neutral) > 120:
            raise RuntimeError("Target exceeds test limits")

        print(f"Testing {name}: {start} -> {target} -> {start}")
        answer = input("Type MOVE to enable motion: ")
        if answer != "MOVE":
            print("Cancelled")
            return

        try:
            self.write_position(servo_id, start)
            self.set_torque(servo_id, True)
            time.sleep(0.2)
            self.write_position(servo_id, target)
            time.sleep(0.5)
            self.write_position(servo_id, start)
            time.sleep(0.5)
            print("Final position:", self.read_position(servo_id))
        finally:
            self.set_torque(servo_id, False)

    def close(self):
        self.port.closePort()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jog", type=int)
    args = parser.parse_args()

    bus = LucaBus()
    try:
        if args.jog is None:
            bus.read_all()
        else:
            bus.test_joint(args.jog)
    finally:
        bus.close()
