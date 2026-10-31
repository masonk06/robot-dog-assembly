"""Read-only, provisional IMU body-axis display; not a balance controller."""
import math
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / '.servo_tools'))
import serial
from tilt_filter import TiltFilter

# Rows transform sensor coordinates to model body axes (+X rear, +Y right, +Z up).
# Derived from operator-held poses; approximate, not control-ready.
SENSOR_TO_BODY = np.array([[.02364086, -.98450299, .17376699],
                           [-.99724308, -.01099415, .07338510],
                           [-.07033743, -.17502281, -.98204871]])
GYRO_BIAS = np.array([.02325, .00600, -.03411])


def transform(values):
    v = np.asarray(values, dtype=float)
    if v.shape != (6,) or not np.isfinite(v).all(): raise ValueError('Invalid IMU sample')
    accel = SENSOR_TO_BODY @ v[:3]
    angular = SENSOR_TO_BODY @ (v[3:] - GYRO_BIAS)
    magnitude = np.linalg.norm(accel)
    if magnitude < 1e-6: raise ValueError('Acceleration magnitude too small')
    up = accel / magnitude
    # +X is toward the rear; +Y is right. Accelerometer tilt is only
    # meaningful under low linear acceleration.
    roll = math.degrees(math.atan2(up[1], up[2]))
    pitch = math.degrees(math.atan2(-up[0], math.hypot(up[1], up[2])))
    return accel, angular, roll, pitch, magnitude


class View:
    def __init__(self, root):
        self.root = root
        root.title('Robot IMU body axes — read only')
        self.port = tk.StringVar(value='COM7')
        self.status = tk.StringVar(value='Disconnected')
        self.values = tk.StringVar(value='No samples yet')
        self.events = queue.Queue(); self.stop = threading.Event(); self.worker = None
        self.filter = TiltFilter(); self.last_sample_time = None
        top = ttk.Frame(root, padding=10); top.pack(fill='x')
        ttk.Label(top, text='Port').pack(side='left')
        ttk.Entry(top, textvariable=self.port, width=9).pack(side='left', padx=5)
        ttk.Button(top, text='Connect', command=self.connect).pack(side='left')
        ttk.Button(top, text='Disconnect', command=self.disconnect).pack(side='left', padx=5)
        ttk.Label(root, text='Approximate sensor-to-body mapping • disarmed readings only', padding=8).pack()
        ttk.Label(root, textvariable=self.values, font=('Consolas', 14), justify='left', padding=12).pack()
        ttk.Label(root, text='Tilt comes from acceleration and can be wrong during movement. Not for motor control.', wraplength=580, padding=8).pack()
        ttk.Label(root, textvariable=self.status, padding=8).pack()
        root.protocol('WM_DELETE_WINDOW', self.close); self.update()

    def connect(self):
        if self.worker and self.worker.is_alive(): return
        self.stop.clear(); self.filter = TiltFilter(); self.last_sample_time = None; port = self.port.get()
        def read():
            bus = serial.Serial(port=None, baudrate=115200, timeout=.15, write_timeout=.2)
            bus.dtr = False; bus.rts = False; bus.port = port
            try:
                bus.open(); bus.reset_input_buffer(); self.events.put(('status', f'Connected to {port}; no motor commands'))
                while not self.stop.is_set():
                    bus.write(b'IMU\n'); bus.flush(); deadline = time.monotonic() + .4
                    while time.monotonic() < deadline and not self.stop.is_set():
                        line = bus.readline().decode('ascii', errors='replace').strip()
                        if line.startswith('IMU,'):
                            fields = line.split(',')
                            if len(fields) == 8: self.events.put(('sample', (time.monotonic(), transform([float(v) for v in fields[2:]]))))
                            break
                        if line.startswith(('IMU_ERROR', 'ERR,')):
                            self.events.put(('status', line)); break
                    self.stop.wait(.1)
            except Exception as error: self.events.put(('status', f'Connection error: {error}'))
            finally:
                if bus.is_open: bus.close()
        self.worker = threading.Thread(target=read, daemon=True); self.worker.start()

    def disconnect(self): self.stop.set(); self.status.set('Disconnected')
    def close(self): self.stop.set(); self.root.destroy()
    def update(self):
        while True:
            try: kind, data = self.events.get_nowait()
            except queue.Empty: break
            if kind == 'status': self.status.set(data)
            else:
                now, (a, w, roll, pitch, magnitude) = data
                dt = .1 if self.last_sample_time is None else now - self.last_sample_time
                self.last_sample_time = now
                if dt <= 0 or dt > .5:
                    self.filter = TiltFilter(); dt = .1
                filtered_roll, filtered_pitch, gravity = self.filter.update(a, w, dt)
                self.values.set(f'Combined tilt estimate\n  roll:  {filtered_roll:+7.1f}°\n  pitch: {filtered_pitch:+7.1f}°\n\nBody angular rate (rad/s)\n  roll X:  {w[0]:+7.3f}\n  pitch Y: {w[1]:+7.3f}\n  yaw Z:   {w[2]:+7.3f}\n\nAcceleration magnitude: {magnitude:.2f} m/s²')
        self.root.after(100, self.update)


if __name__ == '__main__':
    root = tk.Tk(); View(root); root.mainloop()
