"""Pure read-only-capture validation. No serial or motor operations."""
from datetime import datetime
import time

JOINTS=('rear_left_hip_pitch','rear_left_knee_pitch')


def checked_snapshot(telemetry,errors,now=None):
    now=time.monotonic() if now is None else now
    result={}
    for name in JOINTS:
        reading=telemetry.get(name)
        if not reading or name in errors or now-reading['timestamp']>.75:
            raise ValueError(f'{name}: fresh live telemetry required')
        if reading.get('torque')!=0:
            raise ValueError(f'{name}: torque must be reported OFF; no manual capture while powered')
        if reading.get('mode')!=0:
            raise ValueError(f'{name}: expected position mode')
        if not 0<=reading['ticks']<=4095:
            raise ValueError(f'{name}: encoder reading outside 0..4095')
        result[name]=dict(reading)
    return {'captured_local':datetime.now().astimezone().isoformat(), 'positions':result}


def verified_record(captures,margin=25):
    if 'neutral' not in captures:raise ValueError('Capture neutral first')
    result={'description':'User-captured backed-off rear-left bounds in current encoder coordinates',
            'captured_local':datetime.now().astimezone().isoformat(),
            'neutral':captures['neutral'],'joints':{},'margin_ticks':margin,
            'scope':'Supported manual pose capture; no powered trajectory validation performed'}
    for name,sid in zip(JOINTS,(8,9)):
        if f'{name}:A' not in captures or f'{name}:B' not in captures:
            raise ValueError(f'{name}: capture both endpoints')
        endpoints=[captures[f'{name}:{label}'] for label in ('A','B')]
        endpoints.sort(key=lambda s:s['positions'][name]['ticks'])
        lo,hi=[s['positions'][name]['ticks'] for s in endpoints]
        zero=captures['neutral']['positions'][name]['ticks']
        if not lo+margin<zero<hi-margin:
            raise ValueError(f'{name}: neutral must sit inside both endpoints with {margin}-tick margins')
        result['joints'][name]={'id':sid,'neutral_ticks':zero,'minimum_ticks':lo,
            'maximum_ticks':hi,'minimum_capture':endpoints[0],'maximum_capture':endpoints[1]}
    return result
