# Luca ROS 2 IMU bridge

This package reads existing `IMU,...` lines from the ESP32-S3 and publishes
them as `sensor_msgs/msg/Imu` on `/imu/data_raw`. It never writes serial
bytes, arms a servo, or sends a motion command.

## Pi / Docker build

Start the container from the Pi host, passing through the ESP32 device:

```bash
sudo docker run --rm -it --name luca-ros-imu \
  --device=/dev/ttyACM0 \
  --mount type=bind,source="$HOME/robot-dog-assembly",target=/ws/src/robot-dog-assembly \
  --workdir /ws ros:jazzy-ros-base bash
```

Inside it:

```bash
source /opt/ros/jazzy/setup.bash
apt-get update && apt-get install -y python3-serial python3-colcon-common-extensions
colcon build --packages-select luca_imu_bridge
source install/setup.bash
ros2 run luca_imu_bridge imu_bridge
```

In the same shell, background the node for a one-message check:

```bash
ros2 run luca_imu_bridge imu_bridge > /tmp/luca_imu_bridge.log 2>&1 &
sleep 2
ros2 topic echo /imu/data_raw --once
kill %1
```

The ESP32 must already be producing its disarmed `IMU,...` stream. It is
responsible for motion safety; this package is telemetry-only.
