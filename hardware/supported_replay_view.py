"""Operator-started two-joint supported replay with target/encoder visualization."""
import argparse
import json
import queue
from pathlib import Path
import threading
import time
import tkinter as tk
from tkinter import ttk
from calibration_view import CalibrationView,ROOT,serial
from supported_replay import load_plan,snapshot,preflight,execute,NAMES,IDS


class SupportedReplayView(CalibrationView):
    def __init__(self,root,folder):
        self.folder=Path(folder)
        self.report,self.plan,self.neutral,self.limits=load_plan(folder)
        self.command_raw={sid:int(zero) for sid,zero in zip(IDS,self.neutral)}
        self.commands=queue.Queue();self.stop_motion=threading.Event()
        self.busy=False;self.start_pending=False;self.release_unconfirmed=False
        self.supported=tk.BooleanVar(master=root,value=False)
        super().__init__(root)
        for name,sid,zero in zip(NAMES,IDS,self.neutral):self.mapping[name]['zero']=int(zero)
        mode='FULL-AMPLITUDE REAR-LEFT' if self.report.get('full_amplitude_supported_rear_left') else 'SUPPORTED REPLAY'
        self.root.title(f"REV 2 • {mode} • max {self.report.get('maximum_model_excursion_degrees',3):.1f}° / {self.plan[-1,0]:.2f}s • IDs 8/9")
        self.connect_button.configure(text='Connect / preflight')
        self.table.configure(height=4)
        for name in self.names:
            if name not in NAMES:self.table.detach(name)
        def relabel(widget):
            for child in widget.winfo_children():
                if isinstance(child,ttk.Label):
                    text=str(child.cget('text'))
                    if text=='READ ONLY • no torque or position writes':child.configure(text='POWERED TEST • IDs 8/9 only',foreground='#a24c00')
                    elif text=='Live robot + simulated reference':child.configure(text='Supported rear-left replay')
                    elif text=='Reference controls below move this model only.':child.configure(text='Left: actual command targets • right: measured encoders')
                    elif text.startswith('Move a joint on the supported physical robot'):
                        child.configure(text='Supported, feet clear. Only IDs 8 and 9 can be powered. Use physical power cutoff if communication is lost. STOP releases those two servos; it does not return the leg automatically.')
                if isinstance(child,(ttk.Scale,ttk.Checkbutton,ttk.Combobox)):
                    child.configure(state='disabled')
                if isinstance(child,ttk.Button) and str(child.cget('text')) in (
                    'Re-record rear-left limits','Apply display mapping','Use current reading as display zero','Reference neutral'):
                    child.configure(state='disabled')
                relabel(child)
        relabel(root)
        self.ports.configure(state='readonly')
        controls=ttk.Frame(root,padding=10);controls.pack(fill='x')
        ttk.Checkbutton(controls,text='Robot is secured, feet clear, hands clear, power cutoff accessible',variable=self.supported).pack(side='left')
        label=f"START {self.plan[-1,0]:.2f} s / {self.report.get('maximum_model_excursion_degrees',3):.1f}° test"
        self.start_button=ttk.Button(controls,text=label,command=self.start_test)
        self.start_button.pack(side='left',padx=8)
        ttk.Button(controls,text='STOP / release IDs 8 & 9',command=self.emergency_stop).pack(side='left')
        self.status.set('Connect for read-only preflight first. START is required. Temperature is displayed/logged; the software temperature abort is disabled.')

    def reference_angles(self):
        result={name:0. for name in self.names}
        for name,sid,zero,sign in zip(NAMES,IDS,self.neutral,(1,-1)):
            result[name]=sign*(self.command_raw[sid]-zero)*360/4096
        return result

    def connect(self):
        if self.worker and self.worker.is_alive():return
        self.stop.clear();self.stop_motion.clear()
        port=self.port.get()
        def publish(name,reading,target=None):
            if target is not None:
                self.command_raw[IDS[NAMES.index(name)]]=target
            self.events.put((name,reading,None))
        def work():
            try:
                with serial.Serial(port,1_000_000,timeout=.005,write_timeout=.2) as bus:
                    self.bus=bus
                    while not self.stop.is_set():
                        try:command=self.commands.get_nowait()
                        except queue.Empty:command=None
                        if command=='start':
                            self.start_pending=False;self.busy=True
                            path=ROOT/'runs'/'sim2real-hardware'/f'{time.strftime("%Y%m%d-%H%M%S")}.csv'
                            try:
                                result=execute(bus,self.folder,self.stop_motion,publish,path)
                                self.events.put(('',None,f'Completed; IDs 8/9 released. Log: {result["log"]}'))
                            except Exception as error:
                                self.release_unconfirmed='physical cutoff' in str(error)
                                self.events.put(('',None,f'Test stopped: {error}. Check the leg before another attempt.'))
                            finally:self.busy=False
                        try:
                            readings=snapshot(bus)
                            for name,r in readings.items():publish(name,r)
                        except Exception as error:self.events.put(('',None,f'Preflight/telemetry: {error}'))
                        self.stop.wait(.08)
            except Exception as error:self.events.put(('',None,f'Connection: {error}'))
            finally:self.bus=None
        self.worker=threading.Thread(target=work,daemon=True);self.worker.start()
        self.status.set(f'Reading IDs 8/9 on {port}. Start checks neutral {self.neutral.tolist()} and torque OFF. Temperature is monitored, without a software abort.')

    def start_test(self):
        if not self.supported.get():self.status.set('Confirm the supported setup checkbox before starting.');return
        if self.busy or self.start_pending or not self.bus:self.status.set('Connect first, or wait for the current test to finish.');return
        if self.release_unconfirmed:self.status.set('Torque release was unconfirmed. Use the physical cutoff and inspect before proceeding.');return
        try:
            readings={name:self.telemetry[name] for name in NAMES}
            preflight(readings,self.neutral)
        except (ValueError,KeyError) as error:self.status.set(f'Not ready: {error}');return
        self.stop_motion.clear();self.start_pending=True;self.commands.put('start')
        self.status.set('Start requested. Live preflight is repeated before enabling only IDs 8 and 9.')

    def emergency_stop(self):
        self.stop_motion.set()
        # Prevent a queued-but-not-started request from activating after STOP.
        while True:
            try:self.commands.get_nowait()
            except queue.Empty:break
        self.start_pending=False
        self.status.set('STOP requested. Selected servos will be released; use physical cutoff if needed.')

    def disconnect(self):
        self.emergency_stop();self.stop.set()

    def close(self):
        self.emergency_stop();self.stop.set()
        def finish():
            if self.worker and self.worker.is_alive():self.root.after(100,finish);return
            if self.release_unconfirmed:
                self.status.set('Release could not be confirmed. Switch servo power OFF using the physical cutoff before closing.')
                self.release_unconfirmed=False
                return
            if self.log:self.log.close()
            self.renderer.close();self.root.destroy()
        finish()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'hardware'/'replay_plans'/'rear-left-3deg')
    args=parser.parse_args()
    root=tk.Tk();app=SupportedReplayView(root,args.plan);root.mainloop()
