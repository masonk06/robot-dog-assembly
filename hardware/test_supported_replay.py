"""Mock-only replay tests. No serial hardware is imported or opened."""
import csv
import json
from pathlib import Path
import threading
import time
import pytest
from supported_replay import execute,load_plan,preflight,packet,release_selected


class ServoBus:
    def __init__(self):
        self.memory={sid:bytearray(128) for sid in (8,9)}
        for sid,zero in ((8,1677),(9,1572)):
            m=self.memory[sid];m[56:58]=zero.to_bytes(2,'little');m[62]=122;m[63]=31
        self.rx=bytearray();self.sent=[]
    @property
    def in_waiting(self):return len(self.rx)
    def reset_input_buffer(self):self.rx.clear()
    def flush(self):pass
    def read(self,count):result=bytes(self.rx[:count]);del self.rx[:count];return result
    def write(self,p):
        assert sum(p[2:])&255==255
        self.sent.append(p)
        sid,op=p[2],p[4]
        if op==0x83:
            assert sid==254 and p[5:7]==bytes([42,2])
            for i in (7,10):
                selected=p[i];assert selected in (8,9)
                self.memory[selected][56:58]=p[i+1:i+3]
            return
        assert sid in (8,9)
        if op==2:
            payload=self.memory[sid][p[5]:p[5]+p[6]]
        else:
            assert op==3
            self.memory[sid][p[5]:p[5]+len(p[6:-1])]=p[6:-1]
            payload=b''
        body=bytes([sid,len(payload)+2,0])+payload
        self.rx.extend(b'\xff\xff'+body+bytes([(~sum(body))&255]))


def make_plan(folder):
    report={'controlled_ids':[8,9],'within_recorded_limits':True,'checks':[
        {'id':8,'neutral_ticks':1677,'recorded_safe_ticks_with_margin':[722,2846]},
        {'id':9,'neutral_ticks':1572,'recorded_safe_ticks_with_margin':[26,2443]}]}
    (folder/'report.json').write_text(json.dumps(report))
    (folder/'rear-left-small-preview.csv').write_text('t,h,k,ht,kt\n0,0,0,1677,1572\n0.02,0,0,1677,1572\n')


def test_mock_completed_replay_releases_only_selected_joints(tmp_path):
    make_plan(tmp_path);bus=ServoBus()
    result=execute(bus,tmp_path,threading.Event(),lambda *args:None,tmp_path/'log.csv')
    assert result['status']=='completed'
    assert all(bus.memory[s][40]==0 for s in (8,9))
    assert any(p[4]==0x83 for p in bus.sent)


def test_operator_stop_releases_both_joints(tmp_path):
    make_plan(tmp_path);bus=ServoBus();stop=threading.Event()
    def sample(*args):stop.set()
    with pytest.raises(RuntimeError,match='Stopped by operator'):
        execute(bus,tmp_path,stop,sample,tmp_path/'log.csv')
    assert all(bus.memory[s][40]==0 for s in (8,9))


def test_bad_start_does_not_enable_torque(tmp_path):
    make_plan(tmp_path);bus=ServoBus();bus.memory[9][56:58]=(2000).to_bytes(2,'little')
    with pytest.raises(ValueError,match='return manually'):
        execute(bus,tmp_path,threading.Event(),lambda *args:None,tmp_path/'log.csv')
    assert all(p[4]==2 for p in bus.sent)


def test_temperature_is_logged_without_software_abort(tmp_path):
    make_plan(tmp_path);bus=ServoBus()
    bus.memory[8][63]=50
    result=execute(bus,tmp_path,threading.Event(),lambda *args:None,tmp_path/'log.csv')
    assert result['status']=='completed'
    rows=list(csv.DictReader((tmp_path/'log.csv').open()))
    assert any(r['servo_id']=='8' and r['temperature_c']=='50' for r in rows)
    assert all(bus.memory[s][40]==0 for s in (8,9))


def test_release_waits_for_ack_before_contacting_next_servo():
    class HalfDuplexBus(ServoBus):
        def write(self,p):
            assert not self.rx, 'Next request collided with unread previous reply'
            super().write(p)
    bus=HalfDuplexBus()
    for sid in (8,9):bus.memory[sid][40]=1
    assert release_selected(bus)==[]
    assert all(bus.memory[s][40]==0 for s in (8,9))


def test_cleanup_failure_retains_original_motion_error(tmp_path,monkeypatch):
    import supported_replay
    make_plan(tmp_path);bus=ServoBus()
    def sample(*args):raise RuntimeError('original telemetry failure')
    monkeypatch.setattr(supported_replay,'release_selected',lambda bus:['ID 9: unavailable'])
    with pytest.raises(RuntimeError,match='original telemetry failure'):
        execute(bus,tmp_path,threading.Event(),sample,tmp_path/'log.csv')
    status=json.loads((tmp_path/'log.status.json').read_text())
    assert status['motion_error']=='original telemetry failure'
    assert status['release_verified'] is False


def test_preserved_replay_plans_validate_without_hardware():
    root=Path(__file__).parent/'replay_plans'
    for name in ('rear-left-3deg','rear-left-5deg','rear-left-full-46s'):
        report,data,neutral,limits=load_plan(root/name)
        assert list(neutral)==[1677,1572]
        assert (data[:,3:5]>=limits[:,0]).all() and (data[:,3:5]<=limits[:,1]).all()
