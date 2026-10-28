"""Read-only display of IMU tilt relative to the user's saved reference pose."""
import argparse
import json
import math
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from zero_reference import relative_tilt_degrees,corrected_gyro_rad_s


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',default='COM7')
    p.add_argument('--calibration',type=Path,default=Path(__file__).parent/'calibrations/current-zero.json')
    a=p.parse_args()
    calibration=json.loads(a.calibration.read_text(encoding='utf-8'))
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.servo_tools'))
    import serial
    stop=threading.Event();events=queue.Queue(maxsize=8)
    def publish(value):
        if events.full():
            try:events.get_nowait()
            except queue.Empty:pass
        events.put_nowait(value)
    def worker():
        port=serial.Serial(port=None,baudrate=115200,timeout=.2)
        port.port=a.port;port.dtr=False;port.rts=False
        try:
            port.open()
            while not stop.is_set():
                line=port.readline().decode('utf-8',errors='replace').strip()
                if not line.startswith('imu,'):continue
                parts=line.split(',')
                if len(parts)!=10:continue
                try:values=[float(v) for v in parts[3:]]
                except ValueError:continue
                if not all(math.isfinite(v) for v in values):continue
                publish(('sample',time.monotonic(),values))
        except Exception as error:publish(('error',str(error)))
        finally:
            if port.is_open:port.close()
    root=tk.Tk();root.title('IMU - saved zero reference (read only)')
    root.geometry('580x335')
    frame=ttk.Frame(root,padding=20);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='Tilt relative to your saved pose',font=('Segoe UI',16)).pack(anchor='w')
    angles=tk.StringVar(value='Roll: --       Pitch: --')
    ttk.Label(frame,textvariable=angles,font=('Consolas',23)).pack(anchor='w',pady=(20,10))
    rates=tk.StringVar(value='Bias-corrected gyro: --')
    ttk.Label(frame,textvariable=rates,font=('Consolas',11)).pack(anchor='w')
    status=tk.StringVar(value=f'Connecting to {a.port}...')
    ttk.Label(frame,textvariable=status).pack(anchor='w',pady=12)
    ttk.Label(frame,text='Heading / XYZ location are not measured by this display.\nRobot mounting-axis mapping is still pending.').pack(anchor='w')
    ttk.Label(frame,text=f"Zero captured: {calibration['created_at']}").pack(anchor='w',pady=(12,0))
    last=0.;failure=None;filtered=None
    def update():
        nonlocal last,failure,filtered
        try:
            while True:
                item=events.get_nowait()
                if item[0]=='error':failure=item[1];continue
                _,now,values=item
                acc=values[:3]
                if filtered is None:filtered=acc
                else:
                    alpha=1-math.exp(-max(0.,now-last)/.15)
                    filtered=[old+alpha*(new-old) for old,new in zip(filtered,acc)]
                roll,pitch=relative_tilt_degrees(filtered,calibration)
                gyro=corrected_gyro_rad_s(values[3:6],calibration)
                angles.set(f'Roll: {roll:+6.2f}°  Pitch: {pitch:+6.2f}°')
                rates.set('Gyro (rad/s): '+', '.join(f'{v:+.4f}' for v in gyro))
                last=now
        except queue.Empty:pass
        if failure:status.set('Connection error: '+failure)
        elif last and time.monotonic()-last<=.5:status.set(f'LIVE - {a.port} - sensor-only readout')
        else:status.set('STALE - waiting for fresh IMU data')
        if not stop.is_set():root.after(50,update)
    def close():stop.set();root.destroy()
    root.protocol('WM_DELETE_WINDOW',close)
    thread=threading.Thread(target=worker,daemon=True);thread.start()
    root.after(50,update);root.mainloop();stop.set();thread.join(timeout=1)


if __name__=='__main__':main()
