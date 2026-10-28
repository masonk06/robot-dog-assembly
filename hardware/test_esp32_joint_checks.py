from copy import deepcopy
import pytest
from esp32_joint_checks import JointChecks, neutral_neighbors


def sample(ticks, sid=1):
    return dict(id=sid, measured_ticks=ticks, sample_ticks=[ticks]*3,
                sample_device_us=[1,2,3], torque_reported_off=True,
                operator_confirmed_joint_id_and_zero_pose=True)


def checker():
    zeros={'joints':{'joint':{'id':1,'neutral_ticks':2000},'neighbor':{'id':2,'neutral_ticks':2100}}}
    return JointChecks(zeros,{'joint':[-.5,.5],'neighbor':[-.5,.5]})


def verified(sign=1):
    c=checker();c.baseline('joint',sample(2000))
    c.direction('joint',True,sample(2000+sign*57))
    assert c.direction('joint',False,sample(2000-sign*57))
    return c


def test_both_directions_and_valid_baseline_required():
    for sign in (-1,1):
        c=verified(sign)
        assert c.records['joint']['sign']==sign
        assert c.counts()==(1,0)
    c=checker()
    with pytest.raises(ValueError):c.direction('joint',True,sample(2057))
    with pytest.raises(ValueError):c.baseline('joint',sample(2100))
    c.baseline('joint',sample(2000));c.direction('joint',True,sample(2057))
    with pytest.raises(ValueError):c.direction('joint',False,sample(2060))
    with pytest.raises(ValueError):c.direction('joint',False,sample(2005))
    with pytest.raises(ValueError):c.direction('joint',False,sample(1600))
    assert not c.records['joint']['direction_verified']


def test_limits_use_verified_sign_margin_model_range_and_fresh_baseline():
    for sign in (-1,1):
        c=verified(sign)
        with pytest.raises(ValueError):c.endpoint('joint',True,sample(2000+sign*200),{})
        c.limit_baseline('joint',sample(2000))
        assert c.records['joint']['direction_verified']
        assert not c.endpoint('joint',True,sample(2000+sign*200),{})
        assert c.endpoint('joint',False,sample(2000-sign*100),{})
        r=c.records['joint']
        assert r['minimum_ticks']+25<2000<r['maximum_ticks']-25
        assert c.counts()==(1,1)
        c.baseline('joint',sample(2000))
        assert not c.records['joint']['direction_verified']
        assert 'minimum_ticks' not in c.records['joint']
    c=verified();c.limit_baseline('joint',sample(2000))
    for positive,ticks in [(True,2010),(False,2100),(True,3000),(True,5000)]:
        with pytest.raises(ValueError):c.endpoint('joint',positive,sample(ticks),{})


def test_all_neighbors_must_be_fresh_off_clear_and_near_zero():
    c=checker()
    latest={2:dict(id=2,ticks=2100,timestamp=10.,torque=0,mode=0,status=0)}
    assert neutral_neighbors(latest,c.zeros,'joint',11.)['neighbor']['ticks']==2100
    for field,value in [('timestamp',7.),('ticks',2200),('torque',1),('mode',1),('status',32)]:
        changed=deepcopy(latest);changed[2][field]=value
        with pytest.raises(ValueError):neutral_neighbors(changed,c.zeros,'joint',11.)


def test_direction_neutral_check_only_requires_same_leg_pose_but_all_off_and_fresh():
    joints={'front_left_hip_roll':dict(id=4,neutral_ticks=2130),
            'front_left_hip_pitch':dict(id=5,neutral_ticks=1788),
            'rear_left_hip_pitch':dict(id=8,neutral_ticks=1707)}
    latest={5:dict(ticks=1799,timestamp=10.,torque=0,mode=0,status=0),
            8:dict(ticks=1650,timestamp=10.,torque=0,mode=0,status=0)}
    assert neutral_neighbors(latest,joints,'front_left_hip_roll',11.,zero_scope='selected_leg')
    with pytest.raises(ValueError,match=r'rear_left_hip_pitch \(ID 8\)'):
        neutral_neighbors(latest,joints,'front_left_hip_roll',11.,zero_scope='all')
    latest[8]['torque']=1
    with pytest.raises(ValueError):
        neutral_neighbors(latest,joints,'front_left_hip_roll',11.,zero_scope='selected_leg')
