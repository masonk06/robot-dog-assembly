from setuptools import find_packages, setup

package_name = "luca_imu_bridge"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Mason Marsden",
    maintainer_email="mason@example.invalid",
    description="Read-only ESP32 IMU telemetry bridge for Luca.",
    license="MIT",
    entry_points={"console_scripts": ["imu_bridge = luca_imu_bridge.imu_bridge:main"]},
)
