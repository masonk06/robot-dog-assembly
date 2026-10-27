"""Explicit-start, monitored rear-left open-loop replay. Not policy deployment."""
import csv
import json
from pathlib import Path
import threading
import sys
from functools import wraps
import time
import numpy as np
from calibration_io import read_register,read_telemetry

IDS=(8,9)
NAMES=('rear_left_hip_pitch','rear_left_knee_pitch')


def packet(sid,instruction,params):
    body=bytes([sid,len(params)+2,instruction,*params])
    return b'\xff\xff'+body+bytes([(~sum(body))&255])


def word(value):
    if not 0<=int(value)<=4095:raise ValueError('Raw position outside no-wrap interval')
    return list(int(value).to_bytes(2,'little'))


def write_register(bus,sid,address,values):
    if sid not in IDS or address not in (40,41,44,46):
        raise ValueError('Write outside selected joints/RAM profile')
    bus.reset_input_buffer()
    bus.write(packet(sid,3,[address,*values]));bus.flush()
    response=bytearray();deadline=time.monotonic()+.08
    while time.monotonic()<deadline:
        response.extend(bus.read(max(1,min(getattr(bus,'in_waiting',0),64))))
        for i in range(max(0,len(response)-5)):
            frame=response[i:i+6]
            if len(frame)==6 and frame[:4]==bytes([255,255,sid,2]) and sum(frame[2:])&255==255:
                if frame[4]:raise RuntimeError(f'ID {sid}: write status {frame[4]}')
                return
    raise TimeoutError(f'ID {sid}: no valid write acknowledgement')


def goals(bus,values):
    if len(values)!=2:raise ValueError('Exactly IDs 8 and 9 are supported')
    params=[42,2]
    for sid,value in zip(IDS,values):params += [sid,*word(value)]
    bus.write(packet(254,0x83,params));bus.flush()


def release_selected(bus):
    # Serialize request/ACK/readback on the half-duplex bus. Sending the next
    # command while the prior servo replies can collide with that reply.
    # Still attempt both independently if one fails; no bus-wide torque change.
    failures=[]
    for sid in IDS:
        last_error=None
        for _ in range(2):
            try:
                try:write_register(bus,sid,40,[0])
                except (TimeoutError,RuntimeError):
                    # A missing ACK doesn't prove the write failed. Let any
                    # delayed reply drain, then inspect the register directly.
                    time.sleep(.01)
                if read_register(bus,sid,40,1)!=b'\x00':
                    raise RuntimeError('torque is not reported off')
                last_error=None
                break
            except Exception as exc:last_error=exc
        if last_error is not None:failures.append(f'ID {sid}: {last_error}')
    return failures


def load_plan(folder):
    folder=Path(folder)
    report=json.loads((folder/'report.json').read_text())
    data=np.loadtxt(folder/'rear-left-small-preview.csv',delimiter=',',skiprows=1,ndmin=2)
    if report['controlled_ids']!=list(IDS) or not report.get('within_recorded_limits'):
        raise ValueError('Plan did not pass the selected-joint limit check')
    if [c['id'] for c in report['checks']]!=list(IDS):raise ValueError('Limit joint order mismatch')
    if data.shape[1]!=5 or not np.isfinite(data).all() or np.any(np.diff(data[:,0])<=0):
        raise ValueError('Invalid replay trajectory')
    amplitude=float(report.get('maximum_model_excursion_degrees',3))
    full=report.get('full_amplitude_supported_rear_left',False)
    if full:
        if report.get('amplitude_scale')!=1 or amplitude>45 or data[-1,0]>180:
            raise ValueError('Full rear-left replay exceeds its reviewed amplitude/time envelope')
    elif abs(amplitude-3)>1e-5 and abs(amplitude-5)>1e-5:
        raise ValueError('Small replay must declare 3 or 5 degrees')
    elif data[-1,0]>16:
        raise ValueError('Small replay exceeds duration limit')
    if np.max(np.abs(data[:,1:3]))>amplitude+.001:
        raise ValueError('Trajectory exceeds declared amplitude')
    neutral=np.array([int(c['neutral_ticks']) for c in report['checks']])
    limits=np.array([c['recorded_safe_ticks_with_margin'] for c in report['checks']])
    ticks=np.rint(data[:,3:5]).astype(int)
    if np.any(ticks<limits[:,0]) or np.any(ticks>limits[:,1]):raise ValueError('Trajectory outside safe interval')
    if np.any(np.abs(ticks[0]-neutral)>1) or np.any(np.abs(ticks[-1]-neutral)>1):
        raise ValueError('Replay must begin and end at neutral')
    expected=neutral+np.rint(data[:,1:3]*np.array([1,-1])*4096/360).astype(int)
    if not np.array_equal(ticks,expected):raise ValueError('Joint direction/encoder mapping mismatch')
    speed=report.get('profile_speed_ticks_per_second',60)
    if speed not in (60,120):raise ValueError('Unsupported test speed')
    if report.get('profile_acceleration',10) not in (10,20):raise ValueError('Unsupported acceleration')
    if np.max(np.abs(np.diff(ticks,axis=0))/np.diff(data[:,0])[:,None])>speed+1e-6:
        raise ValueError(f'Plan exceeds {speed} ticks/s test profile')
    return report,data,neutral,limits


def snapshot(bus):
    readings={}
    for name,sid in zip(NAMES,IDS):
        reading=read_telemetry(bus,sid)
        reading['torque']=read_register(bus,sid,40,1)[0]
        reading['mode']=read_register(bus,sid,33,1)[0]
        readings[name]=reading
    return readings


def preflight(readings,neutral):
    for name,sid,zero in zip(NAMES,IDS,neutral):
        r=readings[name]
        if time.monotonic()-r['timestamp']>.5:raise ValueError('Telemetry is stale')
        if r['mode']!=0 or r['torque']!=0:raise ValueError(f'ID {sid}: position mode and torque OFF required')
        if abs(r['ticks']-zero)>12:raise ValueError(f'ID {sid}: return manually near {zero} ticks; now {r["ticks"]}')


def precise_timer(function):
    @wraps(function)
    def wrapped(*args,**kwargs):
        timer=None
        if sys.platform=='win32':
            import ctypes
            dll=ctypes.WinDLL('winmm')
            if dll.timeBeginPeriod(1)==0:timer=dll
        try:return function(*args,**kwargs)
        finally:
            if timer is not None:timer.timeEndPeriod(1)
    return wrapped


@precise_timer
def execute(bus,folder,stop,on_sample,log_path):
    report,data,neutral,limits=load_plan(folder)
    readings=snapshot(bus)
    preflight(readings,neutral)
    if stop.is_set():raise RuntimeError('Start cancelled')
    settings={sid:read_register(bus,sid,41,7) for sid in IDS}
    log_path=Path(log_path);log_path.parent.mkdir(parents=True,exist_ok=True)
    enabled=False
    try:
        # Preload each current position BEFORE enabling torque; no cached-goal jump.
        for sid,name in zip(IDS,NAMES):
            write_register(bus,sid,41,[report.get('profile_acceleration',10),*word(readings[name]['ticks']),0,0,*word(report.get('profile_speed_ticks_per_second',60))])
        enabled=True  # From here, every exit attempts release of BOTH selected joints.
        for sid in IDS:
            if stop.is_set():raise RuntimeError('Start cancelled')
            write_register(bus,sid,40,[1])
        with log_path.open('w',newline='') as handle:
            writer=csv.writer(handle)
            writer.writerow(['time_s','servo_id','target_ticks','measured_ticks','error_ticks','temperature_c'])
            began=time.monotonic()
            previous=np.array([readings[n]['ticks'] for n in NAMES])
            for row in data:
                remaining=began+row[0]-time.monotonic()
                if remaining>0:stop.wait(remaining)
                if stop.is_set():raise RuntimeError('Stopped by operator')
                if time.monotonic()-began-row[0]>.25:raise RuntimeError('Control loop fell behind; stopped')
                target=np.rint(row[3:5]).astype(int)
                goals(bus,target)
                measured=[]
                for j,(name,sid) in enumerate(zip(NAMES,IDS)):
                    r=read_telemetry(bus,sid)
                    measured.append(r['ticks'])
                    if not limits[j,0]<=r['ticks']<=limits[j,1]:raise RuntimeError(f'ID {sid}: measured position outside limits')
                    if abs(r['ticks']-previous[j])>100:raise RuntimeError(f'ID {sid}: encoder jump/wrap detected')
                    if abs(r['ticks']-target[j])>35:raise RuntimeError(f'ID {sid}: tracking error above 35 ticks')
                    writer.writerow([time.monotonic()-began,sid,int(target[j]),r['ticks'],r['ticks']-int(target[j]),r['temperature']])
                    on_sample(name,r,int(target[j]))
                previous=np.array(measured)
                handle.flush()
            # Hold neutral briefly and verify actual return, without extra travel.
            goals(bus,neutral)
            if stop.wait(.4):raise RuntimeError('Stopped by operator')
            for name,sid,zero in zip(NAMES,IDS,neutral):
                r=read_telemetry(bus,sid)
                on_sample(name,r,int(zero))
                if abs(r['ticks']-zero)>12:raise RuntimeError(f'ID {sid}: final neutral check failed')
        return {'status':'completed','log':str(log_path),'duration_seconds':float(data[-1,0])}
    finally:
        if enabled:
            original_error=sys.exception()
            failures=release_selected(bus)
            if not failures:
                for sid in IDS:
                    # Restore only RAM profile after confirmed torque release.
                    for address,values in ((41,[settings[sid][0]]),(44,list(settings[sid][3:5])),(46,list(settings[sid][5:7]))):
                        try:write_register(bus,sid,address,values)
                        except Exception:pass
            log_path.with_suffix('.status.json').write_text(json.dumps({
                'motion_error':str(original_error) if original_error else None,
                'release_verified':not failures,'release_errors':failures,
                'plan_folder':str(Path(folder).resolve()),'controller_revision':'acknowledged-release-v2',
                'profile_speed_ticks_per_second':report.get('profile_speed_ticks_per_second',60)},indent=2))
            if failures:
                cause=f'Original test error: {original_error}. ' if original_error else ''
                raise RuntimeError(cause+'Release unconfirmed; use physical cutoff: '+'; '.join(failures)) from original_error
