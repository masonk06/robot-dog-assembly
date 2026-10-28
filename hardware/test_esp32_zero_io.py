import pytest
from esp32_zero_io import ZeroSamples, parse_servo_csv


def sample(ticks=2000, device_us=100, now=10, torque=0, mode=0, status=0):
    return parse_servo_csv(f'servo,1,{device_us},{ticks},12.0,31,{torque},{mode},{status}', now=now)


def history(**changes):
    result = ZeroSamples()
    for i in range(3): result.add(sample(device_us=100 + i * 1200000, now=10 + 1.2 * i, **changes))
    return result


def test_full_csv_contract_and_no_synthetic_samples():
    assert parse_servo_csv('imu,123,0,1,2,3') is None
    assert parse_servo_csv('# servo,id,...') is None
    assert sample()['torque'] == 0
    with pytest.raises(ValueError): parse_servo_csv('servo,1,100,2000,12,31')
    with pytest.raises(ValueError): parse_servo_csv('servo,1,100,2000,nan,31,0,0,0')


def test_capture_requires_operator_live_stable_off_and_position_mode():
    good = history()
    assert good.capture(1, True, now=12.5)['neutral_ticks'] == 2000
    for torque, mode, status in [(1, 0, 0), (0, 1, 0), (0, 0, 32)]:
        with pytest.raises(ValueError): history(torque=torque, mode=mode, status=status).capture(1, True, now=12.5)
    with pytest.raises(ValueError): good.capture(1, False, now=12.5)
    with pytest.raises(ValueError): good.capture(1, True, now=16)
    with pytest.raises(ValueError): history(ticks=-1).capture(1, True, now=12.5)


def test_duplicate_reset_failed_read_and_motion_cannot_pass():
    h = ZeroSamples()
    for i in range(3): h.add(sample(device_us=100, now=10 + i))
    with pytest.raises(ValueError): h.capture(1, True, now=12)
    h = history(); h.add(sample(ticks=2100, device_us=4000000, now=12.5))
    with pytest.raises(ValueError): h.capture(1, True, now=12.5)
    h = history(); h.invalidate(1)
    with pytest.raises(ValueError): h.capture(1, True, now=12.5)
    h = history(); h.add(sample(device_us=10, now=12.5))
    with pytest.raises(ValueError): h.capture(1, True, now=12.5)


def test_micros_wrap_is_not_mistaken_for_three_duplicate_samples():
    h = ZeroSamples()
    for us, now in [(2**32 - 2000000, 10), (2**32 - 800000, 11.2), (400000, 12.4)]:
        h.add(sample(device_us=us, now=now))
    assert h.capture(1, True, now=12.5)['neutral_ticks'] == 2000
