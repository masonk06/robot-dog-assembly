from luca_imu_bridge.imu_bridge import parse_imu_line


def test_parse_imu_line() -> None:
    sample = parse_imu_line("IMU,264111377,-0.4453,-2.1787,9.807,0.1,0.2,0.3")
    assert sample is not None
    assert sample.device_us == 264111377
    assert sample.az == 9.807


def test_parser_rejects_non_imu_telemetry() -> None:
    assert parse_imu_line("READY,DISARMED") is None
    assert parse_imu_line("IMU,bad,0,0,0,0,0,0") is None
