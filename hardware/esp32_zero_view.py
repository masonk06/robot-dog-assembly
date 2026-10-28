"""Operator-confirmed 12-joint zero capture from ESP32 CSV. No serial writes."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import uuid
from PIL import Image, ImageTk
from calibration_io import JOINT_IDS
from esp32_zero_io import ZeroSamples, parse_servo_csv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.servo_tools'))
import serial
from serial.tools import list_ports


class ZeroView:
    def __init__(self, root):
        self.root = root
        root.title('ESP32 • all 12 zero points — READ ONLY')
        root.geometry('1390x870')
        self.old = json.loads((ROOT / 'hardware/display_joint_mapping.json').read_text())
        self.assignments = dict(JOINT_IDS)
        self.names = list(self.assignments)
        self.samples = ZeroSamples()
        self.latest = {}
        self.captures = {}
        self.path = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        self.port = tk.StringVar(value='COM7')
        self.selected = tk.StringVar(value=self.names[0])
        self.sid = tk.StringVar(value=str(self.assignments[self.selected.get()]))
        self.confirmed = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value='Disconnected. No motor commands, torque changes, or EEPROM writes are implemented.')
        self.progress = tk.StringVar(value='0 / 12 zeros captured; directions and limits remain separate')
        self.view = tk.StringVar(value='Three-quarter')
        self.build()
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.tick()

    def build(self):
        bar = ttk.Frame(self.root, padding=10); bar.pack(fill='x')
        ttk.Label(bar, text='ESP32 ZERO CHECK • READ ONLY', font=('Segoe UI', 16, 'bold')).pack(side='left')
        ports = [p.device for p in list_ports.comports()]
        ttk.Combobox(bar, textvariable=self.port, values=ports, width=9).pack(side='left', padx=10)
        ttk.Button(bar, text='Connect CSV 115200', command=self.connect).pack(side='left')
        ttk.Button(bar, text='Disconnect', command=self.disconnect).pack(side='left', padx=8)
        ttk.Label(self.root, text='Support the body. Never force a joint while torque is ON or unknown. This program cannot turn torque off.',
                  foreground='#9a3e10').pack(anchor='w', padx=12)
        body = ttk.Frame(self.root, padding=10); body.pack(fill='both', expand=True)
        left = ttk.Frame(body); left.pack(side='left', fill='y')
        ttk.Label(left, text='SIMULATION NEUTRAL • all joint angles 0°', font=('Segoe UI', 12, 'bold')).pack()
        self.image_label = ttk.Label(left); self.image_label.pack()
        view = ttk.Combobox(left, textvariable=self.view, values=['Side', 'Front / rear', 'Three-quarter', 'Top'], state='readonly')
        view.pack(pady=8); view.bind('<<ComboboxSelected>>', lambda _: self.show_reference())
        self.show_reference()
        ttk.Label(left, text='CAD mounting bends remain at model zero.\nMatch joint geometry, not encoder tick 0 or 2048.\nThe saved frame outline may differ from the new frame.',
                  wraplength=560).pack(pady=8)
        right = ttk.Frame(body); right.pack(side='left', fill='both', expand=True, padx=10)
        cols = ('id', 'ticks', 'torque', 'status', 'old', 'zero', 'age')
        self.table = ttk.Treeview(right, columns=cols, show='tree headings', height=12)
        self.table.heading('#0', text='Physical joint'); self.table.column('#0', width=205)
        for key, title, width in zip(cols, ['ID', 'Ticks', 'Torque', 'Status', 'Old zero', 'New zero', 'Age s'], [35, 55, 55, 75, 60, 60, 50]):
            self.table.heading(key, text=title); self.table.column(key, width=width, anchor='center')
        for name in self.names: self.table.insert('', 'end', iid=name, text=name)
        self.table.pack(fill='x')
        self.table.bind('<<TreeviewSelect>>', self.select_row)
        ttk.Label(right, textvariable=self.progress).pack(anchor='w', pady=12)
        joint = ttk.Combobox(right, textvariable=self.selected, values=self.names, width=30, state='readonly')
        joint.pack(anchor='w'); joint.bind('<<ComboboxSelected>>', lambda _: self.select_joint())
        row = ttk.Frame(right); row.pack(anchor='w', pady=10)
        ttk.Label(row, text='Verified physical servo ID:').pack(side='left')
        sid = ttk.Combobox(row, textvariable=self.sid, values=list(range(1, 13)), width=5, state='readonly')
        sid.pack(side='left', padx=8); sid.bind('<<ComboboxSelected>>', self.change_id)
        ttk.Checkbutton(right, text='I verified this physical joint’s ID and placed it at the shown model-zero pose',
                        variable=self.confirmed).pack(anchor='w', pady=8)
        ttk.Button(right, text='Capture selected zero', command=self.capture).pack(anchor='w', pady=8)
        ttk.Button(right, text='Save all 12 zero points', command=self.save_complete).pack(anchor='w', pady=8)
        ttk.Label(right, text='Old zero is historical, not a target. Capture needs 3 stable samples, torque OFF, position mode and clear status.\n'
                  'Captures go to a NEW local file. Existing mappings, limits and firmware stay unchanged.',
                  wraplength=680).pack(anchor='w', pady=10)
        ttk.Label(self.root, textvariable=self.status, wraplength=1350).pack(fill='x', padx=12, pady=12)

    def show_reference(self):
        path = ROOT / 'reports/sim2real/simulation-neutral-reference.png'
        with Image.open(path) as whole:
            index = ['Side', 'Front / rear', 'Three-quarter', 'Top'].index(self.view.get())
            x, y = 20 + (index % 2) * 710, 108 + (index // 2) * 505
            picture = whole.crop((x, y, x + 700, y + 450)).resize((560, 360))
        self.photo = ImageTk.PhotoImage(picture)
        self.image_label.configure(image=self.photo)

    def select_row(self, _):
        selection = self.table.selection()
        if selection:
            self.selected.set(selection[0]); self.select_joint()

    def select_joint(self):
        self.sid.set(str(self.assignments[self.selected.get()]))
        self.confirmed.set(False)

    def change_id(self, _):
        name = self.selected.get()
        self.assignments[name] = int(self.sid.get())
        self.captures.pop(name, None)
        self.confirmed.set(False)
        self.status.set('ID assignment changed in this session only. Confirm its physical location before capture.')

    def connect(self):
        if self.worker and self.worker.is_alive():
            self.status.set('Already connected; disconnect before changing ports.'); return
        if self.captures:
            self.status.set('Save this session and reopen the tool before starting another connection.'); return
        self.samples = ZeroSamples(); self.latest.clear(); self.stop.clear(); self.confirmed.set(False)
        port = self.port.get()
        def read():
            try:
                bus = serial.Serial(port=None, baudrate=115200, timeout=.1)
                bus.dtr = False; bus.rts = False; bus.port = port
                with bus:
                    bus.reset_input_buffer()
                    pending = bytearray()
                    self.events.put(('status', f'Listening on {port}; receiving only. Requires the combined servo CSV readout sketch.'))
                    while not self.stop.is_set():
                        pending.extend(bus.read(max(1, min(bus.in_waiting, 512))))
                        while b'\n' in pending:
                            line, _, remainder = pending.partition(b'\n'); pending = bytearray(remainder)
                            line = line.decode('ascii', errors='replace').strip()
                            if line.startswith('# RoboDog'):
                                self.events.put(('restart', None))
                            elif line.startswith('servo_error,'):
                                parts = line.split(',')
                                try: self.events.put(('error', int(parts[1])))
                                except (ValueError, IndexError): pass
                            else:
                                try:
                                    reading = parse_servo_csv(line)
                                    if reading: self.events.put(('reading', reading))
                                except ValueError as error: self.events.put(('invalid', str(error)))
                        if len(pending) > 2048:
                            pending.clear(); self.events.put(('status', 'Unsupported or oversized serial line; no capture accepted.'))
            except Exception as error:
                self.events.put(('status', f'Cannot read {port}: {error}. Close other serial programs; no firmware was changed.'))
        self.worker = threading.Thread(target=read, daemon=True); self.worker.start()

    def disconnect(self):
        self.stop.set()
        self.confirmed.set(False)
        self.status.set('Disconnecting. Servo torque is unchanged; no motor commands were sent.')

    def capture(self):
        try:
            if self.stop.is_set() or not self.worker or not self.worker.is_alive():
                raise ValueError('Connect to fresh ESP32 telemetry first')
            name = self.selected.get(); sid = self.assignments[name]
            if any(v['id'] == sid for joint, v in self.captures.items() if joint != name):
                raise ValueError('This ID is already assigned to a different captured joint')
            self.captures[name] = self.samples.capture(sid, self.confirmed.get())
            self.save_progress()
            self.confirmed.set(False)
            next_name = next((joint for joint in self.names if joint not in self.captures), name)
            self.selected.set(next_name); self.select_joint()
            self.status.set(f'Captured {name}: ID {sid} = {self.captures[name]["neutral_ticks"]} ticks. Saved locally; no servo settings changed.')
        except ValueError as error:
            self.status.set(str(error))

    def save_progress(self, complete=False):
        if self.path is None:
            folder = ROOT / 'hardware/calibrations'; folder.mkdir(exist_ok=True)
            self.path = folder / f'zeros-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.json'
        model = ROOT / 'simulation/mujoco/robot_dog_v2.xml'
        record = dict(status='operator_verified_zero_points_only' if complete else 'incomplete_zero_session',
                      recorded_local=datetime.now().astimezone().isoformat(),
                      transport='ESP32 read-only CSV 115200', port=self.port.get(),
                      model_sha256=hashlib.sha256(model.read_bytes()).hexdigest(),
                      model_zero_radians=[0.] * 12, joints=self.captures,
                      ready_for_motion=False, direction_calibration_complete=False,
                      travel_limit_calibration_complete=False,
                      note='New-frame zero captures only. Existing mapping/calibration files were not overwritten.')
        self.path.write_text(json.dumps(record, indent=2) + '\n')

    def save_complete(self):
        if len(self.captures) != 12 or {v['id'] for v in self.captures.values()} != set(range(1, 13)):
            self.status.set('Capture all 12 joints with unique physical IDs first.'); return
        self.save_progress(complete=True)
        self.status.set(f'All 12 zero points saved: {self.path}. Directions and limits still need verification before motion.')

    def tick(self):
        while True:
            try: kind, value = self.events.get_nowait()
            except queue.Empty: break
            if kind == 'reading':
                self.samples.add(value); self.latest[value['id']] = value
            elif kind == 'error':
                self.samples.invalidate(value); self.latest.pop(value, None)
            elif kind == 'restart':
                self.samples = ZeroSamples(); self.latest.clear(); self.confirmed.set(False)
                self.status.set('ESP32 restart detected. Waiting for new samples; check the physical pose again.')
            elif kind == 'invalid':
                self.samples = ZeroSamples(); self.latest.clear(); self.confirmed.set(False)
                self.status.set(value + '; waiting for three new valid samples.')
            else: self.status.set(value)
        now = time.monotonic()
        for name in self.names:
            sid = self.assignments[name]; reading = self.latest.get(sid)
            candidate = self.captures.get(name, {}).get('neutral_ticks', '—')
            if reading:
                age = now - reading['timestamp']
                state = 'STALE' if age > 2 else f'ERR {reading["status"]}' if reading['status'] else 'LIVE'
                values = (sid, reading['ticks'], 'OFF' if reading['torque'] == 0 else 'ON', state,
                          self.old[name]['zero'], candidate, f'{age:.1f}')
            else: values = (sid, '—', '?', 'NO DATA', self.old[name]['zero'], candidate, '—')
            self.table.item(name, values=values)
        self.progress.set(f'{len(self.captures)} / 12 zeros captured; directions and limits remain separate')
        self.root.after(150, self.tick)

    def close(self):
        self.stop.set()
        if self.worker: self.worker.join(timeout=.5)
        self.root.destroy()


def main():
    root = tk.Tk(); ZeroView(root); root.mainloop()


if __name__ == '__main__': main()
