import math
import pytest
from zero_reference import relative_tilt_degrees,zero_frame,corrected_gyro_rad_s


@pytest.mark.parametrize('gravity',[(0,0,9.81),(0,0,-9.81),(-1.1,-2.04,-9.12),(2.,3.,8.)])
def test_captured_pose_reads_zero_even_when_sensor_is_upside_down(gravity):
    x,y,z=gravity
    c={'roll_reference_rad':math.atan2(y,z),
       'pitch_reference_rad':math.atan2(-x,math.hypot(y,z)),'gyro_bias_rad_s':[.02,.006,-.03]}
    assert relative_tilt_degrees(gravity,c)==pytest.approx((0,0),abs=1e-10)
    assert math.dist((0,0,0),zero_frame(gravity,c))==pytest.approx(math.dist((0,0,0),gravity))
    assert corrected_gyro_rad_s(c['gyro_bias_rad_s'],c)==pytest.approx((0,0,0),abs=1e-12)


def test_known_relative_pitch_and_roll_are_not_erased():
    c={'roll_reference_rad':0.,'pitch_reference_rad':0.}
    angle=math.radians(15)
    assert relative_tilt_degrees((0,9.81*math.sin(angle),9.81*math.cos(angle)),c)==pytest.approx((15,0))
    assert relative_tilt_degrees((-9.81*math.sin(angle),0,9.81*math.cos(angle)),c)==pytest.approx((0,15))
