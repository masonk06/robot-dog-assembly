"""Reference and encoder-driven robot views. READ-only serial; no motor commands."""
import argparse
import csv
import json
import math
from pathlib import Path
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
import mujoco
import numpy as np
from PIL import Image,ImageTk
from calibration_io import JOINT_IDS,default_mapping,read_telemetry,read_register,to_degrees
from limit_capture import JOINTS as CAPTURE_JOINTS,checked_snapshot,verified_record

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.servo_tools'))
import serial
from serial.tools import list_ports


class CalibrationView:
    def __init__(self,root):
        self.root=root
        root.title('RoboDog • Live calibration comparison — READ ONLY')
        self.mapping_path=ROOT/'hardware'/'display_joint_mapping.json'
        self.mapping=(json.loads(self.mapping_path.read_text()) if self.mapping_path.exists() else
            default_mapping(json.loads((ROOT/'hardware'/'physical_neutral_pose.json').read_text())['positions']))
        self.model=mujoco.MjModel.from_xml_path(str(ROOT/'simulation'/'mujoco'/'robot_dog_v2.xml'))
        self.reference=mujoco.MjData(self.model)
        self.measured=mujoco.MjData(self.model)
        self.names=[name for name,_ in JOINT_IDS]
        self.qadr={name:self.model.jnt_qposadr[mujoco.mj_name2id(self.model,mujoco.mjtObj.mjOBJ_JOINT,name)] for name in self.names}
        self.renderer=mujoco.Renderer(self.model,height=350,width=500)
        self.camera=mujoco.MjvCamera()
        self.camera.lookat[:]=[0,0,.08]
        self.camera.distance=.65;self.camera.azimuth=135;self.camera.elevation=-22
        self.telemetry={};self.errors={};self.events=queue.Queue()
        self.stop=threading.Event();self.worker=None;self.bus=None
        self.selected=tk.StringVar(value=self.names[0]);self.target=tk.DoubleVar(value=0)
        self.port=tk.StringVar();self.status=tk.StringVar(value='Disconnected. Opening this screen never moves the robot.')
        self.preview=tk.BooleanVar(value=False);self.demo=tk.BooleanVar(value=False)
        self.sign=tk.StringVar(value='1');self.zero=tk.StringVar()
        self.live_state=tk.StringVar(value='No telemetry — neutral placeholder')
        self.log=None;self.writer=None;self.frames=0
        self.captures={};self.capture_window=None;self.capture_file=None
        self.capture_status=tk.StringVar(value='Begin at the physical neutral pose. Capture neutral before moving anything.')
        self.capture_live=tk.StringVar(value='Connect read-only to see IDs 8 and 9.')
        self.build()
        self.refresh_ports();self.select_joint()
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.update()

    def build(self):
        top=ttk.Frame(self.root,padding=10);top.pack(fill='x')
        ttk.Label(top,text='Live robot + simulated reference',font=('Segoe UI',16,'bold')).pack(side='left')
        ttk.Label(top,text='READ ONLY • no torque or position writes',foreground='#146b46').pack(side='right')
        bar=ttk.Frame(self.root,padding=(10,0));bar.pack(fill='x')
        ttk.Label(bar,text='Waveshare USB bus:').pack(side='left')
        self.ports=ttk.Combobox(bar,textvariable=self.port,width=13,state='readonly');self.ports.pack(side='left',padx=5)
        ttk.Button(bar,text='Refresh',command=self.refresh_ports).pack(side='left')
        self.connect_button=ttk.Button(bar,text='Connect read-only',command=self.connect);self.connect_button.pack(side='left',padx=5)
        ttk.Button(bar,text='Disconnect',command=self.disconnect).pack(side='left')
        ttk.Checkbutton(bar,text='Offline demo',variable=self.demo).pack(side='left',padx=10)
        ttk.Button(bar,text='Record CSV',command=self.record).pack(side='right')
        ttk.Button(bar,text='Re-record rear-left limits',command=self.open_capture).pack(side='right',padx=6)
        views=ttk.Frame(self.root,padding=10);views.pack()
        for column,(title,attribute) in enumerate((('SIMULATED REFERENCE — blue','ref_image'),('LIVE ENCODERS — green','live_image'))):
            ttk.Label(views,text=title,font=('Segoe UI',11,'bold')).grid(row=0,column=column)
            label=ttk.Label(views);label.grid(row=1,column=column,padx=5)
            setattr(self,attribute,label)
        ttk.Label(views,text='Reference controls below move this model only.').grid(row=2,column=0)
        ttk.Label(views,textvariable=self.live_state).grid(row=2,column=1)
        controls=ttk.Frame(self.root,padding=(10,0));controls.pack(fill='x')
        joint=ttk.Combobox(controls,textvariable=self.selected,values=self.names,width=28,state='readonly')
        joint.pack(side='left');joint.bind('<<ComboboxSelected>>',lambda _:self.select_joint())
        ttk.Label(controls,text='Reference angle:').pack(side='left',padx=6)
        ttk.Scale(controls,from_=-10,to=10,variable=self.target,length=190).pack(side='left')
        ttk.Checkbutton(controls,text='±5° slow preview (screen only)',variable=self.preview).pack(side='left',padx=8)
        ttk.Button(controls,text='Reference neutral',command=lambda:self.target.set(0)).pack(side='left')
        mapping=ttk.Frame(self.root,padding=10);mapping.pack(fill='x')
        ttk.Label(mapping,text='Display zero (ticks):').pack(side='left')
        ttk.Entry(mapping,textvariable=self.zero,width=8).pack(side='left',padx=4)
        ttk.Label(mapping,text='Direction:').pack(side='left')
        ttk.Combobox(mapping,textvariable=self.sign,values=['1','-1'],width=4,state='readonly').pack(side='left')
        ttk.Button(mapping,text='Apply display mapping',command=self.apply_mapping).pack(side='left',padx=5)
        ttk.Button(mapping,text='Use current reading as display zero',command=self.capture_zero).pack(side='left')
        ttk.Label(mapping,text='Changes affect this viewer only.',foreground='#666666').pack(side='left',padx=8)
        self.table=ttk.Treeview(self.root,columns=('id','target','measured','error','raw','temp','age'),show='tree headings',height=12)
        self.table.heading('#0',text='Joint');self.table.column('#0',width=230)
        for key,title in [('id','ID'),('target','Ref °'),('measured','Live °'),('error','Live − ref °'),('raw','Ticks'),('temp','°C'),('age','Status')]:
            self.table.heading(key,text=title);self.table.column(key,width=100,anchor='center')
        for name,sid in JOINT_IDS:self.table.insert('', 'end',iid=name,text=name,values=(sid,'0','—','—','—','—','NO DATA'))
        self.table.pack(fill='x',padx=10)
        ttk.Label(self.root,textvariable=self.status,wraplength=1000).pack(fill='x',padx=10,pady=8)
        ttk.Label(self.root,text='Move a joint on the supported physical robot to check correspondence. Use the direct servo-bus USB port, not an ESP32 console. Body pose is fixed; joint encoders do not measure world position.',wraplength=1000,foreground='#555555').pack(fill='x',padx=10,pady=(0,8))

    def refresh_ports(self):
        choices=[p.device for p in list_ports.comports()]
        self.ports['values']=choices
        if not self.port.get() and choices:self.port.set('COM5' if 'COM5' in choices else choices[0])

    def select_joint(self):
        m=self.mapping[self.selected.get()];self.zero.set(str(m['zero']));self.sign.set(str(m['sign']))

    def apply_mapping(self):
        try:
            zero=int(self.zero.get());sign=int(self.sign.get())
            if not 0<=zero<=4095 or sign not in (-1,1):raise ValueError()
        except ValueError:
            self.status.set('Display zero must be 0..4095 and direction +1 or -1.');return
        self.mapping[self.selected.get()].update(zero=zero,sign=sign)
        self.mapping_path.write_text(json.dumps(self.mapping,indent=2))
        self.status.set('Display mapping saved locally. No servo registers were changed.')

    def capture_zero(self):
        reading=self.telemetry.get(self.selected.get())
        if not reading or time.monotonic()-reading['timestamp']>1:
            self.status.set('A fresh live reading is required.');return
        self.zero.set(str(reading['ticks']));self.apply_mapping()

    def open_capture(self):
        if self.capture_window and self.capture_window.winfo_exists():
            self.capture_window.lift();return
        window=tk.Toplevel(self.root);self.capture_window=window
        window.title('Rear-left neutral and backed-off limits — READ ONLY')
        window.geometry('620x420')
        ttk.Label(window,text='Rear-left recapture: IDs 8 and 9',font=('Segoe UI',15,'bold')).pack(padx=14,pady=12)
        ttk.Label(window,text='Keep the robot supported. Both servos must report torque OFF. Capture the current neutral first. Then move ONE joint gently by hand, back away from contact/cable tension, and capture endpoints A and B. Keep the other joint near neutral.',wraplength=580).pack(padx=14)
        ttk.Label(window,textvariable=self.capture_live,font=('Consolas',11)).pack(pady=12)
        ttk.Button(window,text='1. Capture both joints at neutral',command=lambda:self.capture_point('neutral')).pack(pady=5)
        for name,label in zip(CAPTURE_JOINTS,('Hip pitch — ID 8','Knee pitch — ID 9')):
            row=ttk.Frame(window);row.pack(pady=5)
            ttk.Label(row,text=label,width=22).pack(side='left')
            for endpoint in ('A','B'):
                ttk.Button(row,text=f'Capture endpoint {endpoint}',command=lambda n=name,e=endpoint:self.capture_point(f'{n}:{e}')).pack(side='left',padx=4)
        ttk.Button(window,text='Save checked neutral + limits',command=self.save_capture).pack(pady=10)
        ttk.Label(window,textvariable=self.capture_status,wraplength=580).pack(padx=14,pady=6)

    def capture_point(self,key):
        try:
            if self.demo.get():raise ValueError('Offline demo cannot record hardware calibration')
            snapshot=checked_snapshot(self.telemetry,self.errors)
            if key!='neutral':
                if 'neutral' not in self.captures:raise ValueError('Capture neutral first')
                moving=key.split(':')[0]
                other=next(n for n in CAPTURE_JOINTS if n!=moving)
                if abs(snapshot['positions'][other]['ticks']-self.captures['neutral']['positions'][other]['ticks'])>35:
                    raise ValueError(f'Keep {other} within about 3 degrees of its captured neutral')
            elif self.captures:
                raise ValueError('Neutral already captured for this session; keep it fixed while recording endpoints')
            self.captures[key]=snapshot
            if self.capture_file is None:
                folder=ROOT/'hardware'/'calibrations';folder.mkdir(parents=True,exist_ok=True)
                self.capture_file=folder/f'rear-left-{time.strftime("%Y%m%d-%H%M%S")}.json'
            self.capture_file.write_text(json.dumps({'status':'incomplete','captures':self.captures},indent=2))
            self.capture_status.set(f'Captured {key}. {len(self.captures)}/5 points recorded. No servo settings changed.')
        except ValueError as error:self.capture_status.set(str(error))

    def save_capture(self):
        try:
            record=verified_record(self.captures)
            self.capture_file.write_text(json.dumps({'status':'checked_manual_capture',**record},indent=2))
            self.capture_status.set(f'Saved {self.capture_file.name}. Old calibration files preserved. Ready for offline replay-limit check.')
            print(f'CALIBRATION_SAVED {self.capture_file}',flush=True)
        except ValueError as error:self.capture_status.set(str(error))

    def connect(self):
        if self.worker and self.worker.is_alive():return
        self.demo.set(False);self.stop.clear()
        port=self.port.get()
        def poll():
            try:
                with serial.Serial(port,1_000_000,timeout=.005,write_timeout=.2) as bus:
                    self.bus=bus
                    while not self.stop.is_set():
                        for name,sid in JOINT_IDS:
                            if self.stop.is_set():break
                            try:
                                reading=read_telemetry(bus,sid)
                                if sid in (8,9):
                                    reading['torque']=read_register(bus,sid,40,1)[0]
                                    reading['mode']=read_register(bus,sid,33,1)[0]
                                self.events.put((name,reading,None))
                            except Exception as exc:self.events.put((name,None,str(exc)))
                        self.stop.wait(.02)
            except Exception as exc:self.events.put(('',None,f'Connection: {exc}'))
            finally:self.bus=None
        self.worker=threading.Thread(target=poll,daemon=True);self.worker.start()
        self.status.set(f'Reading {port} at 1 Mbps. No motor commands will be sent.')

    def disconnect(self):
        self.stop.set()
        self.status.set('Disconnected. Torque state is unchanged; this tool never enables or disables motors.')

    def record(self):
        if self.log:
            self.log.close();self.log=None;self.writer=None;self.status.set('CSV recording stopped.');return
        folder=ROOT/'runs'/'calibration';folder.mkdir(parents=True,exist_ok=True)
        path=folder/f'{time.strftime("%Y%m%d-%H%M%S")}.csv'
        self.log=path.open('w',newline='');self.writer=csv.writer(self.log)
        self.writer.writerow(['time_monotonic','joint','servo_id','reference_deg','measured_deg','error_deg','ticks','temperature_c','age_s','demo'])
        self.status.set(f'Recording comparisons to {path}')

    def reference_angles(self):
        target=5*math.sin(time.monotonic()*math.pi/4) if self.preview.get() else self.target.get()
        return {name:(target if name==self.selected.get() else 0.) for name in self.names}

    def update(self):
        while True:
            try:name,reading,error=self.events.get_nowait()
            except queue.Empty:break
            if error:
                self.errors[name]=error
                if not name:self.status.set(error)
            else:self.telemetry[name]=reading;self.errors.pop(name,None)
        now=time.monotonic()
        lines=[]
        for name,sid in ((CAPTURE_JOINTS[0],8),(CAPTURE_JOINTS[1],9)):
            reading=self.telemetry.get(name,{})
            fresh_read=now-reading.get('timestamp',0)<.75 and name not in self.errors
            lines.append(f"ID {sid}: {reading.get('ticks','—')} ticks | torque {reading.get('torque','?')} | {'LIVE' if fresh_read else 'STALE'}")
        self.capture_live.set('\n'.join(lines))
        fresh=sum(now-v['timestamp']<1 and name not in self.errors for name,v in self.telemetry.items())
        self.live_state.set('OFFLINE DEMO — synthetic data' if self.demo.get() else
            f'{fresh}/12 fresh readings; missing joints shown at neutral' if fresh else
            'NO LIVE DATA — neutral/last-known pose is a placeholder')
        references=self.reference_angles()
        for data in (self.reference,self.measured):
            data.qpos[:]=self.model.qpos0
        for name,angle in references.items():self.reference.qpos[self.qadr[name]]=math.radians(angle)
        for name,sid in JOINT_IDS:
            ref=references.get(name,0.)
            reading=self.telemetry.get(name)
            age=now-reading['timestamp'] if reading else float('inf')
            if self.demo.get():
                degrees=ref*.9;raw='DEMO';temperature='—';age=0;state='DEMO'
            elif reading:
                m=self.mapping[name];degrees=to_degrees(reading['ticks'],m['zero'],m['sign'])
                raw=reading['ticks'];temperature=reading['temperature']
                state='LIVE' if age<1 and name not in self.errors else 'STALE / NO REPLY'
            else:
                self.table.item(name,values=(sid,f'{ref:.1f}','—','—','—','—','NO DATA'));continue
            self.measured.qpos[self.qadr[name]]=math.radians(degrees)
            self.table.item(name,values=(sid,f'{ref:.1f}',f'{degrees:.1f}',f'{degrees-ref:+.1f}',raw,temperature,state))
            if self.writer and self.frames%5==0:
                self.writer.writerow([now,name,sid,ref,degrees,degrees-ref,raw,temperature,age,self.demo.get()])
        live_color=(.15,.8,.48,1) if fresh else (.5,.5,.5,1)
        if self.demo.get():live_color=(.95,.6,.15,1)
        for data,label,color in ((self.reference,self.ref_image,(.15,.48,.95,1)),(self.measured,self.live_image,live_color)):
            mujoco.mj_forward(self.model,data)
            self.renderer.update_scene(data,camera=self.camera)
            for geom in self.renderer.scene.geoms[:self.renderer.scene.ngeom]:
                if geom.objtype==mujoco.mjtObj.mjOBJ_GEOM and geom.objid>=0 and self.model.geom_bodyid[geom.objid]>0:
                    geom.rgba[:]=color
            photo=ImageTk.PhotoImage(Image.fromarray(self.renderer.render()))
            label.configure(image=photo);label.image=photo
        self.frames+=1
        if self.log and self.frames%20==0:self.log.flush()
        self.root.after(80,self.update)

    def close(self):
        self.stop.set()
        if self.worker:self.worker.join(timeout=.5)
        if self.log:self.log.close()
        self.renderer.close();self.root.destroy()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',action='store_true',help='Open the rear-left recapture panel')
    args=parser.parse_args()
    root=tk.Tk()
    app=CalibrationView(root)
    if args.capture:app.open_capture()
    root.mainloop()


if __name__=='__main__':main()
