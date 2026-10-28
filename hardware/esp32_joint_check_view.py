"""Read-only manual direction and conservative endpoint checks through ESP32 CSV."""
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import uuid
import mujoco
from PIL import Image, ImageTk
from calibration_io import JOINT_IDS
from esp32_zero_io import ZeroSamples, parse_servo_csv
from esp32_joint_checks import JointChecks, neutral_neighbors

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.servo_tools'))
import serial
from serial.tools import list_ports


class JointCheckView:
    def __init__(self, root):
        self.root = root
        root.title('REV 2 • ESP32 directions and limits — corrected front labels • READ ONLY')
        root.geometry('1350x940')
        self.zero_path = ROOT / 'hardware/calibrations/zero-points-current.json'
        self.zeros = json.loads(self.zero_path.read_text())
        self.zero_source_sha256 = hashlib.sha256(self.zero_path.read_bytes()).hexdigest()
        model_path = ROOT / 'simulation/mujoco/robot_dog_v2.xml'
        assert self.zeros['status'] == 'operator_verified_zero_points_only'
        assert self.zeros['model_sha256'] == hashlib.sha256(model_path.read_bytes()).hexdigest()
        self.model = mujoco.MjModel.from_xml_path(str(model_path))
        self.names = [name for name, _ in JOINT_IDS]
        self.qadr = {}
        limits = {}
        for name in self.names:
            joint = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            self.qadr[name] = self.model.jnt_qposadr[joint]
            limits[name] = self.model.jnt_range[joint].tolist()
        self.checks = JointChecks(self.zeros, limits)
        self.renderer = mujoco.Renderer(self.model, width=560, height=320)
        self.data = mujoco.MjData(self.model)
        self.camera = mujoco.MjvCamera()
        self.camera.lookat[:] = [0, 0, .065]
        self.camera.distance = .52
        self.camera.azimuth = 135
        self.camera.elevation = -15
        self.samples = ZeroSamples(); self.latest = {}; self.blocked = set()
        self.events = queue.Queue(); self.stop = threading.Event(); self.worker = None
        self.selected = tk.StringVar(value=self.names[0])
        self.port = tk.StringVar(value='COM7')
        self.confirmed = tk.BooleanVar(value=False)
        self.mode = tk.StringVar(value='Directions')
        self.view = tk.StringVar(value='Three-quarter')
        self.status = tk.StringVar(value='Disconnected. No motor goals, torque writes or EEPROM changes are implemented.')
        self.progress = tk.StringVar()
        self.hint = tk.StringVar(value='Begin with a neutral baseline. Only move a joint when torque is reported OFF.')
        self.ref_angle = 0.; self.armed_step = 'baseline'; self.path = None
        self.build(); root.protocol('WM_DELETE_WINDOW', self.close)
        self.tick()

    def build(self):
        top = ttk.Frame(self.root, padding=8); top.pack(fill='x')
        ttk.Label(top, text='MANUAL DIRECTIONS + LIMITS • READ ONLY', font=('Segoe UI', 14, 'bold')).pack(side='left')
        ttk.Combobox(top, textvariable=self.port, values=[p.device for p in list_ports.comports()], width=8).pack(side='left', padx=8)
        ttk.Button(top, text='Connect CSV 115200', command=self.connect).pack(side='left')
        ttk.Button(top, text='Disconnect', command=lambda: self.stop.set()).pack(side='left', padx=8)
        ttk.Label(self.root, text='Support the dog; keep hands clear of pinch points. Verify torque OFF before moving by hand. Do not seek hard stops.',
                  foreground='#9a3e10').pack(anchor='w', padx=10)
        pictures = ttk.Frame(self.root); pictures.pack()
        ttk.Label(pictures, text='ALL JOINTS AT MODEL ZERO').grid(row=0, column=0)
        ttk.Label(pictures, text='SELECTED JOINT • reference movement on screen only').grid(row=0, column=1)
        self.neutral_image = ttk.Label(pictures); self.neutral_image.grid(row=1, column=0, padx=5)
        self.reference_image = ttk.Label(pictures); self.reference_image.grid(row=1, column=1, padx=5)
        camera = ttk.Combobox(pictures, textvariable=self.view, values=['Three-quarter', 'Side', 'Front / rear', 'Top'], state='readonly')
        camera.grid(row=2, column=0, pady=4)
        ttk.Label(pictures, textvariable=self.hint, wraplength=600).grid(row=2, column=1)
        self.table = ttk.Treeview(self.root, columns=('id','ticks','zero','delta','torque','sign','limits','state'), show='tree headings', height=12)
        self.table.heading('#0', text='Joint'); self.table.column('#0', width=230)
        for key, title in [('id','ID'),('ticks','Live ticks'),('zero','Saved zero'),('delta','Live − zero'),('torque','Torque'),('sign','Verified sign'),('limits','Guarded ticks'),('state','State')]:
            self.table.heading(key, text=title); self.table.column(key, width=110, anchor='center')
        for name in self.names: self.table.insert('', 'end', iid=name, text=name)
        self.table.pack(fill='x', padx=10)
        self.table.bind('<<TreeviewSelect>>', self.select_row)
        row = ttk.Frame(self.root, padding=8); row.pack(fill='x')
        select = ttk.Combobox(row, textvariable=self.selected, values=self.names, width=30, state='readonly')
        select.pack(side='left'); select.bind('<<ComboboxSelected>>', lambda _: self.select_joint())
        mode = ttk.Combobox(row, textvariable=self.mode, values=['Directions', 'Limits'], width=14, state='readonly')
        mode.pack(side='left', padx=10); mode.bind('<<ComboboxSelected>>', lambda _: self.select_joint())
        ttk.Label(row, textvariable=self.progress).pack(side='left')
        ttk.Checkbutton(self.root, text='I checked the selected physical joint/ID and matched the shown movement direction, or chose a backed-off clear endpoint',
                        variable=self.confirmed).pack(anchor='w', padx=10)
        buttons = ttk.Frame(self.root, padding=8); buttons.pack(fill='x')
        ttk.Button(buttons, text='1. Capture neutral baseline', command=self.baseline).pack(side='left')
        ttk.Button(buttons, text='Show +5°', command=lambda: self.show(5, 'positive')).pack(side='left', padx=5)
        ttk.Button(buttons, text='Capture positive pose / endpoint', command=lambda: self.capture(True)).pack(side='left')
        ttk.Button(buttons, text='Show −5°', command=lambda: self.show(-5, 'negative')).pack(side='left', padx=5)
        ttk.Button(buttons, text='Capture negative pose / endpoint', command=lambda: self.capture(False)).pack(side='left')
        ttk.Button(buttons, text='Save session', command=self.save).pack(side='left', padx=8)
        ttk.Label(self.root, textvariable=self.status, wraplength=1300).pack(fill='x', padx=10, pady=6)

    def select_row(self, _):
        if self.table.selection():
            self.selected.set(self.table.selection()[0]); self.select_joint()

    def select_joint(self):
        self.ref_angle = 0; self.armed_step = 'baseline'; self.confirmed.set(False)
        name=self.selected.get();record=self.checks.records[name]
        scope='this leg' if self.mode.get()=='Directions' else 'all legs'
        self.hint.set(f'Selected {name}, ID {record["id"]}, saved zero {record["neutral_ticks"]} ticks. '
                      f'Return {scope} near their saved zeros and capture a baseline first.')

    def show(self, angle, step):
        self.ref_angle = angle; self.armed_step = step; self.confirmed.set(False)
        self.hint.set(f'{self.selected.get()}: model {angle:+.0f}°. Only the screen moves. '
                      + ('Move the real joint a few degrees the same way and hold still.' if self.mode.get() == 'Directions'
                         else 'Choose a comfortable clear endpoint on this model-angle side; do not seek a hard stop.'))

    def connect(self):
        if self.worker and self.worker.is_alive(): return
        self.samples = ZeroSamples(); self.latest.clear(); self.blocked = set(range(1,13)); self.stop.clear()
        self.select_joint(); port = self.port.get()
        def read():
            try:
                bus = serial.Serial(port=None, baudrate=115200, timeout=.1)
                bus.dtr=False; bus.rts=False; bus.port=port
                with bus:
                    bus.reset_input_buffer()
                    pending=bytearray()
                    self.events.put(('status', f'Listening to {port}. Receive-only; no motor commands are sent.'))
                    while not self.stop.is_set():
                        pending.extend(bus.read(max(1,min(bus.in_waiting,512))))
                        while b'\n' in pending:
                            line,_,rest=pending.partition(b'\n');pending=bytearray(rest)
                            line=line.decode('ascii',errors='replace').strip()
                            if line.startswith('# RoboDog'): self.events.put(('restart',None))
                            elif line.startswith('servo_error,'):
                                try:self.events.put(('error',int(line.split(',')[1])))
                                except (ValueError,IndexError):pass
                            else:
                                try:
                                    value=parse_servo_csv(line)
                                    if value:self.events.put(('reading',value))
                                except ValueError as error:self.events.put(('invalid',str(error)))
                        if len(pending)>2048:
                            pending.clear();self.events.put(('invalid','Unsupported serial data'))
            except Exception as error:self.events.put(('status',f'Cannot read {port}: {error}. Disconnect the zero-check window or Serial Monitor first.'))
        self.worker=threading.Thread(target=read,daemon=True);self.worker.start()

    def sample(self, purpose='model_zero_pose'):
        if self.stop.is_set() or not self.worker or not self.worker.is_alive():raise ValueError('Connect to fresh ESP32 telemetry first')
        if hashlib.sha256(self.zero_path.read_bytes()).hexdigest()!=self.zero_source_sha256:
            raise ValueError('The zero-source file changed. Reopen this checker before recording more poses')
        name=self.selected.get();sid=self.zeros['joints'][name]['id']
        if not self.confirmed.get():raise ValueError('Confirm the selected physical joint/ID and shown reference before capture')
        sample=self.samples.capture(sid,self.confirmed.get())
        sample['measured_ticks']=sample.pop('neutral_ticks')
        sample.pop('operator_confirmed_joint_id_and_zero_pose',None)
        sample['operator_confirmed_selected_joint_and_'+purpose]=True
        neighbors=neutral_neighbors(self.latest,self.zeros['joints'],name,time.monotonic(),
                                   zero_scope='selected_leg' if self.mode.get()=='Directions' else 'all')
        return name,sid,sample,neighbors

    def baseline(self):
        try:
            name,sid,sample,_=self.sample()
            if self.mode.get()=='Limits':self.checks.limit_baseline(name,sample)
            else:self.checks.baseline(name,sample)
            self.blocked.discard(sid)
            self.ref_angle=0;self.armed_step='baseline';self.confirmed.set(False)
            self.save()
            self.status.set('Neutral baseline accepted. Click Show +5°, compare the screen, move gently by hand, and confirm before capture.')
        except ValueError as error:self.status.set(str(error))

    def capture(self,positive):
        try:
            if self.armed_step!=('positive' if positive else 'negative'):
                raise ValueError('Click the matching Show +5° or Show −5° reference first')
            name,sid,sample,neighbors=self.sample('reference_direction' if self.mode.get()=='Directions' else 'clear_endpoint')
            if sid in self.blocked:raise ValueError('New neutral baseline required after connection, restart, or suspected wrap/jump')
            if 'baseline' not in self.checks.records[name]:raise ValueError('Capture this joint’s neutral baseline first')
            if self.mode.get()=='Directions':
                done=self.checks.direction(name,positive,sample)
                message=(f'Direction verified: sign {self.checks.records[name]["sign"]:+d}. Return to zero before checking the next joint.' if done
                         else 'Positive pose recorded. Return through zero, select Show −5°, then move gently in that direction.')
            else:
                done=self.checks.endpoint(name,positive,sample,neighbors)
                message=('Both conservative endpoints recorded, with 25-tick inward margins. These limits apply only with other joints near neutral.' if done
                         else 'One endpoint recorded. Return through zero and record the opposite model-angle endpoint.')
            self.confirmed.set(False);self.save();self.status.set(message)
        except ValueError as error:self.status.set(str(error))

    def save(self):
        directions,bounds=self.checks.counts()
        if self.path is None:
            self.path=ROOT/'hardware/calibrations'/f'joint-checks-{time.strftime("%Y%m%d-%H%M%S")}-{uuid.uuid4().hex[:6]}.json'
        record=dict(status='checked_manual_capture' if bounds==12 else 'manual_joint_checks_incomplete',
                    recorded_local=datetime.now().astimezone().isoformat(),
                    zero_source=self.zero_path.relative_to(ROOT).as_posix(),
                    zero_source_sha256=self.zero_source_sha256,
                    model_sha256=self.zeros['model_sha256'],transport='ESP32 CSV 115200, receive only',
                    joints=self.checks.records,margin_ticks=25,direction_calibration_complete=directions==12,
                    travel_limit_calibration_complete=bounds==12,ready_for_motion=False,
                    scope='Operator-confirmed manual directions and static endpoints with other joints near neutral; no powered or coupled-pose validation')
        self.path.write_text(json.dumps(record,indent=2)+'\n')
        self.status.set(f'Saved {self.path.name}. No legacy calibration, firmware or servo settings changed.')

    def render(self,angle):
        self.data.qpos[:]=self.model.qpos0
        self.data.qpos[self.qadr[self.selected.get()]]=math.radians(angle)
        mujoco.mj_forward(self.model,self.data)
        self.renderer.update_scene(self.data,camera=self.camera)
        joint=mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,self.selected.get())
        body=self.model.jnt_bodyid[joint]
        for geom in self.renderer.scene.geoms[:self.renderer.scene.ngeom]:
            if geom.objtype!=mujoco.mjtObj.mjOBJ_GEOM or geom.objid<0:continue
            ancestor=int(self.model.geom_bodyid[geom.objid])
            while ancestor>0 and ancestor!=body:ancestor=int(self.model.body_parentid[ancestor])
            if ancestor==body:geom.rgba[:]=(.18,.65,.95,1)
        return ImageTk.PhotoImage(Image.fromarray(self.renderer.render()))

    def tick(self):
        while True:
            try:kind,value=self.events.get_nowait()
            except queue.Empty:break
            if kind=='reading':
                old=self.latest.get(value['id'])
                if old and abs(old['ticks']-value['ticks'])>2048:
                    self.blocked.add(value['id']);self.samples.invalidate(value['id'])
                    self.status.set(f'ID {value["id"]}: suspected encoder wrap/jump. A new neutral baseline is required.')
                self.samples.add(value);self.latest[value['id']]=value
            elif kind=='error':self.samples.invalidate(value);self.latest.pop(value,None)
            elif kind in ('restart','invalid'):
                self.samples=ZeroSamples();self.latest.clear();self.blocked.update(range(1,13));self.confirmed.set(False)
                self.status.set('Stream restart/error: wait for fresh samples and recapture a neutral baseline before moving.')
            else:self.status.set(value)
        now=time.monotonic()
        for name in self.names:
            record=self.checks.records[name];sid=record['id'];reading=self.latest.get(sid)
            limits=f'{record["minimum_ticks"]+25}..{record["maximum_ticks"]-25}' if record['limits_verified'] else 'unverified'
            if reading:
                state='STALE' if now-reading['timestamp']>2 else f'ERR {reading["status"]}' if reading['status'] else 'LIVE'
                values=(sid,reading['ticks'],record['neutral_ticks'],reading['ticks']-record['neutral_ticks'],
                        'OFF' if reading['torque']==0 else 'ON',record.get('sign','?'),limits,state)
            else:values=(sid,'—',record['neutral_ticks'],'—','?',record.get('sign','?'),limits,'NO DATA')
            self.table.item(name,values=values)
        directions,bounds=self.checks.counts()
        records=list(self.checks.records.values())
        baselines=sum('baseline' in r for r in records)
        positive=sum('positive_direction' in r for r in records)
        negative=sum('negative_direction' in r for r in records)
        self.progress.set(f'Baselines {baselines}/12 • + poses {positive}/12 • − poses {negative}/12 • Directions {directions}/12 • limits {bounds}/12')
        self.camera.azimuth,self.camera.elevation={'Three-quarter':(135,-15),'Side':(90,-8),'Front / rear':(0,-8),'Top':(90,-89)}[self.view.get()]
        self.neutral_photo=self.render(0);self.neutral_image.configure(image=self.neutral_photo)
        # Slow on-screen motion 0 -> selected angle -> 0; no actuator output exists.
        angle=self.ref_angle*(.5-.5*math.cos(2*math.pi*time.monotonic()/5))
        self.reference_photo=self.render(angle);self.reference_image.configure(image=self.reference_photo)
        self.root.after(150,self.tick)

    def close(self):
        self.stop.set()
        if self.worker:self.worker.join(timeout=.5)
        self.renderer.close();self.root.destroy()


def main():
    root=tk.Tk();JointCheckView(root);root.mainloop()


if __name__=='__main__':main()
