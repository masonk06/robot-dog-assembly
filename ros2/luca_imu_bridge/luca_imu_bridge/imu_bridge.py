"""Publish read-only ESP32 IMU telemetry as sensor_msgs/msg/Imu.

The bridge deliberately never writes to its serial port.  Servo arming and
motion commands remain exclusively under the ESP32 safety receiver.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import serial
from serial import SerialException


@dataclass(frozen=True)
class ImuSample:
    """Firmware IMU line, already expressed in m/s^2 and rad/s."""

    device_us: int
    ax: float
    ay: float
    az: float
    gx: float
    gy: float
    gz: float


def parse_imu_line(line: str) -> Optional[ImuSample]:
    """Parse one exact ESP32 ``IMU,...`` line; reject all other telemetry."""
    fields = line.strip().split(",")
    if len(fields) != 8 or fields[0] != "IMU":
        return None
    try:
        return ImuSample(int(fields[1]), *(float(value) for value in fields[2:]))
    except ValueError:
        return None


class LucaImuBridge(Node):
    """Non-commanding serial reader for the Luca ESP32 IMU stream."""

    def __init__(self) -> None:
        super().__init__("luca_imu_bridge")
        self.declare_parameter("port", "/dev/ttyACM0")
        self.declare_parameter("baud", 115200)
        self.declare_parameter("frame_id", "imu_link")
        self._port = str(self.get_parameter("port").value)
        self._baud = int(self.get_parameter("baud").value)
        self._frame_id = str(self.get_parameter("frame_id").value)
        self._serial: Optional[serial.Serial] = None
        self._publisher = self.create_publisher(Imu, "/imu/data_raw", 20)
        self.create_timer(0.01, self._poll)

    def _connect(self) -> bool:
        if self._serial and self._serial.is_open:
            return True
        try:
            # This constructor only opens/reads.  No command bytes are emitted.
            self._serial = serial.Serial(self._port, self._baud, timeout=0)
            self.get_logger().info(f"Reading IMU telemetry from {self._port} at {self._baud} baud")
            return True
        except SerialException as error:
            self._serial = None
            self.get_logger().warn(f"Waiting for ESP32 serial device {self._port}: {error}", throttle_duration_sec=5.0)
            return False

    def _poll(self) -> None:
        if not self._connect():
            return
        try:
            raw = self._serial.readline()
        except SerialException as error:
            self.get_logger().warn(f"Lost ESP32 serial connection: {error}")
            self._serial = None
            return
        if not raw:
            return
        sample = parse_imu_line(raw.decode("utf-8", errors="replace"))
        if sample is None:
            return
        message = Imu()
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = self._frame_id
        # Orientation is intentionally unavailable until an estimator is added.
        message.orientation_covariance[0] = -1.0
        message.linear_acceleration.x = sample.ax
        message.linear_acceleration.y = sample.ay
        message.linear_acceleration.z = sample.az
        message.angular_velocity.x = sample.gx
        message.angular_velocity.y = sample.gy
        message.angular_velocity.z = sample.gz
        self._publisher.publish(message)

    def destroy_node(self) -> bool:
        if self._serial and self._serial.is_open:
            self._serial.close()
        return super().destroy_node()


def main() -> None:
    rclpy.init()
    node = LucaImuBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
