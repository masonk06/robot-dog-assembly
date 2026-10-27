"""Side-effect-free read-only telemetry and editable simulation/servo mapping."""
import time
from joint_mapping import KNEE_MODEL_TO_SERVO_SIGN

JOINT_IDS = [
    ('front_left_hip_roll',1),('front_left_hip_pitch',2),('front_left_knee_pitch',3),
    ('front_right_hip_roll',4),('front_right_hip_pitch',5),('front_right_knee_pitch',6),
    ('rear_left_hip_roll',7),('rear_left_hip_pitch',8),('rear_left_knee_pitch',9),
    ('rear_right_hip_roll',11),('rear_right_hip_pitch',10),('rear_right_knee_pitch',12)]
TICKS_PER_DEGREE = 4096/360


def read_packet(servo_id,address=56,count=8):
    body=bytes([servo_id,4,2,address,count])
    return b'\xff\xff'+body+bytes([(~sum(body))&255])


def read_register(bus,servo_id,address,count):
    # The only bus instruction implemented here is READ (0x02).
    request=read_packet(servo_id,address,count)
    bus.reset_input_buffer()
    bus.write(request)
    bus.flush()
    received=bytearray()
    deadline=time.monotonic()+.06
    while time.monotonic()<deadline:
        received.extend(bus.read(max(1,min(getattr(bus,'in_waiting',0),64))))
        for i in range(max(0,len(received)-(count+5))):
            if received[i:i+4]!=bytes([255,255,servo_id,count+2]): continue
            frame=received[i:i+count+6]
            if len(frame)==count+6 and (sum(frame[2:])&255)==255:
                if frame[4]: raise RuntimeError(f'servo status error {frame[4]}')
                return bytes(frame[5:-1])
    raise TimeoutError(f'ID {servo_id}: no valid telemetry response')


def read_telemetry(bus,servo_id):
    data=read_register(bus,servo_id,56,8)
    raw=int.from_bytes(data[:2],'little')
    ticks=-(raw&0x7fff) if raw&0x8000 else raw
    return {'ticks':ticks,'voltage':data[6]/10,'temperature':data[7],
            'timestamp':time.monotonic()}


def to_degrees(ticks,zero,sign):
    return sign*(ticks-zero)/TICKS_PER_DEGREE


def default_mapping(neutral):
    return {name:{'id':sid,'zero':neutral[str(sid)],
        'sign':KNEE_MODEL_TO_SERVO_SIGN[name.removesuffix('_knee_pitch')] if name.endswith('_knee_pitch') else 1,
        'note':'Editable display mapping; does not change servo EEPROM/calibration.'}
        for name,sid in JOINT_IDS}
