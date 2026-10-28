"""Pure mock-bus tests. This module never opens a serial device."""
from calibration_io import read_packet,read_telemetry,to_degrees,default_mapping


class FakeBus:
    def __init__(self):
        payload=(2200).to_bytes(2,'little')+bytes([0,0,0,0,120,32])
        body=bytes([9,10,0])+payload
        self.response=bytes([255,255])+body+bytes([(~sum(body))&255])
        self.requests=[];self.data=bytearray()
    @property
    def in_waiting(self):return len(self.data)
    def reset_input_buffer(self):self.data.clear()
    def write(self,packet):
        assert packet[4]==2, 'Only READ is permitted'
        self.requests.append(packet)
        self.data.extend(b'noise'+packet+self.response)
    def flush(self):pass
    def read(self,count):
        result=bytes(self.data[:count]);del self.data[:count];return result


def test_telemetry_with_noise_and_echo_sends_only_read():
    bus=FakeBus()
    reading=read_telemetry(bus,9)
    assert reading['ticks']==2200 and reading['voltage']==12 and reading['temperature']==32
    assert bus.requests==[read_packet(9)]
    assert sum(bus.requests[0][2:])&255==255


def test_display_mapping_has_correct_rear_right_ids_and_invertible_signs():
    mapping=default_mapping({str(i):2048 for i in range(1,13)})
    assert [mapping['front_left_'+joint]['id'] for joint in ('hip_roll','hip_pitch','knee_pitch')]==[4,5,6]
    assert [mapping['front_right_'+joint]['id'] for joint in ('hip_roll','hip_pitch','knee_pitch')]==[1,2,3]
    assert mapping['rear_right_hip_roll']['id']==11
    assert mapping['rear_right_hip_pitch']['id']==10
    assert mapping['rear_left_knee_pitch']['sign']==-1
    assert mapping['front_left_knee_pitch']['sign']==-1
    assert mapping['front_right_knee_pitch']['sign']==-1
    assert abs(to_degrees(2048+4096/36,2048,-1)+10)<1e-8


def test_hardware_conversion_sites_share_the_corrected_knee_signs():
    import ast
    import json
    from pathlib import Path
    from joint_mapping import KNEE_MODEL_TO_SERVO_SIGN
    folder=Path(__file__).parent
    # Evaluate only configuration literals; never import motion scripts.
    for filename,variable in [('rear_left_ik_trot.py','LEG_CONFIG'),('sim2real_lateral_pair_plan.py','TRANSFER_STATUS')]:
        tree=ast.parse((folder/filename).read_text())
        assignment=next(n for n in tree.body if isinstance(n,ast.Assign) and
                        any(isinstance(t,ast.Name) and t.id==variable for t in n.targets))
        configs=eval(compile(ast.Expression(assignment.value),filename,'eval'),
                     {'__builtins__':{},'KNEE_MODEL_TO_SERVO_SIGN':KNEE_MODEL_TO_SERVO_SIGN})
        for leg,config in configs.items():
            if 'knee_sign' in config:
                assert config['knee_sign']==KNEE_MODEL_TO_SERVO_SIGN[leg.replace('-','_')]
    safety=json.loads((folder/'joint_safety_config.json').read_text())
    for joint in safety['joints']:
        if joint['name'].endswith('_knee_pitch'):
            assert joint['model_to_servo_sign']==KNEE_MODEL_TO_SERVO_SIGN[joint['name'].removesuffix('_knee_pitch')]


def test_register_reads_for_torque_and_mode_are_read_only():
    from calibration_io import read_register
    class RegisterBus(FakeBus):
        def write(self,packet):
            assert packet[5] in (33,40) and packet[6]==1
            body=bytes([9,3,0,0])
            self.response=bytes([255,255])+body+bytes([(~sum(body))&255])
            super().write(packet)
    bus=RegisterBus()
    assert read_register(bus,9,40,1)==b'\x00'
    assert read_register(bus,9,33,1)==b'\x00'


def test_capture_rejects_powered_stale_and_inconsistent_limits():
    import copy
    import pytest
    from limit_capture import JOINTS,checked_snapshot,verified_record
    readings={name:{'ticks':zero,'torque':0,'mode':0,'timestamp':10.} for name,zero in zip(JOINTS,(1749,1698))}
    neutral=checked_snapshot(readings,{},now=10.)
    with pytest.raises(ValueError):checked_snapshot(readings,{},now=11.)
    powered=copy.deepcopy(readings);powered[JOINTS[0]]['torque']=1
    with pytest.raises(ValueError):checked_snapshot(powered,{},now=10.)
    captures={'neutral':neutral}
    for name in JOINTS:
        for endpoint,ticks in [('A',1500),('B',2000)]:
            sample=copy.deepcopy(neutral);sample['positions'][name]['ticks']=ticks
            captures[f'{name}:{endpoint}']=sample
    result=verified_record(captures)
    assert result['joints'][JOINTS[1]]['neutral_ticks']==1698
    captures[f'{JOINTS[1]}:A']['positions'][JOINTS[1]]['ticks']=2202
    captures[f'{JOINTS[1]}:B']['positions'][JOINTS[1]]['ticks']=3592
    with pytest.raises(ValueError):verified_record(captures)
