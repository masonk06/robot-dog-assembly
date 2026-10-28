"""Apply a saved tilt reference without discarding gravity or claiming XYZ position."""
import math


def zero_frame(vector, calibration):
    """Rotate sensor coordinates into the captured level frame; heading is arbitrary."""
    roll=calibration['roll_reference_rad']
    pitch=calibration['pitch_reference_rad']
    x,y,z=vector
    cr,sr=math.cos(roll),math.sin(roll)
    cp,sp=math.cos(pitch),math.sin(pitch)
    ry,rz=cr*y-sr*z,sr*y+cr*z
    return cp*x+sp*rz,ry,-sp*x+cp*rz


def relative_tilt_degrees(acceleration, calibration):
    x,y,z=zero_frame(acceleration,calibration)
    if math.sqrt(x*x+y*y+z*z)<1e-6:
        raise ValueError('No gravity direction available')
    return math.degrees(math.atan2(y,z)),math.degrees(math.atan2(-x,math.hypot(y,z)))


def corrected_gyro_rad_s(gyro, calibration):
    return zero_frame([v-b for v,b in zip(gyro,calibration['gyro_bias_rad_s'])],calibration)
