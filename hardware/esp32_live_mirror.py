"""Read-only ESP32 telemetry mirror for the robot-dog simulation.

This program never writes to the serial port beyond opening it with DTR/RTS
disabled. It cannot enable torque, set goals, change IDs, or write EEPROM.
"""
from pathlib import Path
import json
import math
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk

import mujoco
from PIL import Image, ImageTk

from calibration_io import JOINT_IDS
from esp32_zero_io import parse_servo_csv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".servo_tools"))
import serial
from serial.tools import list_ports

TICKS_PER_RADIAN = 4096.0 / (2.0 * math.pi)


class LiveMirror:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("RoboDog live mirror — ESP32 CSV receive-only")
        root.geometry("1260x790")
        self.zeros = json.loads((ROOT / "hardware/calibrations/zero-points-current.json").read_text())
        self.directions = json.loads((ROOT / "hardware/calibrations/manual-physical-directions-20261028.json").read_text())
        self.model = mujoco.MjModel.from_xml_path(str(ROOT / "simulation/mujoco/robot_dog_v2.xml"))
        self.reference = mujoco.MjData(self.model)
        self.live = mujoco.MjData(self.model)
        self.reference_renderer = mujoco.Renderer(self.model, width=560, height=390)
        self.live_renderer = mujoco.Renderer(self.model, width=560, height=390)
        self.camera = mujoco.MjvCamera()
        self.camera.lookat[:] = [0.0, 0.0, 0.065]
        self.camera.distance = 0.52
        self.camera.azimuth = 135
        self.camera.elevation = -15
        self.port = tk.StringVar(value="COM7")
        self.view = tk.StringVar(value="Three-quarter")
        self.status = tk.StringVar(value="Disconnected. Receive-only: the mirror cannot command the robot.")
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        self.latest = {}
        self.qadr = {}
        self.rows = {}
        for name, _ in JOINT_IDS:
            jid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            self.qadr[name] = self.model.jnt_qposadr[jid]
        self.build()
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.tick()

    def build(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="LIVE ROBOT + SIMULATION REFERENCE", font=("Segoe UI", 14, "bold")).pack(side="left")
        ttk.Label(top, text="  COM port:").pack(side="left")
        ttk.Combobox(top, textvariable=self.port, values=[p.device for p in list_ports.comports()], width=8).pack(side="left", padx=5)
        ttk.Button(top, text="Connect CSV 115200", command=self.connect).pack(side="left")
        ttk.Button(top, text="Disconnect", command=self.disconnect).pack(side="left", padx=5)
        ttk.Combobox(top, textvariable=self.view, values=["Three-quarter", "Side", "Front / rear", "Top"], state="readonly", width=14).pack(side="right")
        ttk.Label(self.root, text="Move only by hand with servo torque reported OFF. This app receives CSV telemetry only; it sends no bytes to the ESP32 or servo bus.", foreground="#9a3e10").pack(anchor="w", padx=10)

        images = ttk.Frame(self.root, padding=8)
        images.pack()
        ttk.Label(images, text="SIMULATION REFERENCE — all joints at 0°").grid(row=0, column=0)
        ttk.Label(images, text="LIVE ENCODER MIRROR — model angles from current ticks").grid(row=0, column=1)
        self.reference_image = ttk.Label(images)
        self.reference_image.grid(row=1, column=0, padx=5)
        self.live_image = ttk.Label(images)
        self.live_image.grid(row=1, column=1, padx=5)

        table = ttk.Treeview(self.root, columns=("id", "ticks", "zero", "degrees", "torque", "status"), show="tree headings", height=12)
        table.heading("#0", text="Joint")
        table.column("#0", width=260)
        for key, label, width in [("id", "ID", 55), ("ticks", "Live ticks", 100), ("zero", "Saved zero", 100), ("degrees", "Mirrored °", 110), ("torque", "Torque", 80), ("status", "State", 170)]:
            table.heading(key, text=label)
            table.column(key, width=width, anchor="center")
        for name, sid in JOINT_IDS:
            table.insert("", "end", iid=name, text=name, values=(sid, "—", self.zeros["joints"][name]["neutral_ticks"], "—", "?", "NO DATA"))
        table.pack(fill="x", padx=10)
        self.table = table
        ttk.Label(self.root, textvariable=self.status, wraplength=1220).pack(fill="x", padx=10, pady=6)

    def connect(self):
        if self.worker and self.worker.is_alive():
            return
        self.latest.clear()
        self.stop.clear()
        port = self.port.get()

        def read():
            try:
                bus = serial.Serial(port=None, baudrate=115200, timeout=0.1)
                bus.dtr = False
                bus.rts = False
                bus.port = port
                with bus:
                    bus.reset_input_buffer()
                    self.events.put(("status", f"Listening to {port}; receive-only CSV telemetry."))
                    pending = bytearray()
                    while not self.stop.is_set():
                        pending.extend(bus.read(max(1, min(bus.in_waiting, 512))))
                        while b"\n" in pending:
                            raw, _, rest = pending.partition(b"\n")
                            pending = bytearray(rest)
                            try:
                                reading = parse_servo_csv(raw.decode("ascii", errors="replace").strip())
                                if reading:
                                    self.events.put(("reading", reading))
                            except ValueError:
                                pass
                        if len(pending) > 2048:
                            pending.clear()
            except Exception as error:
                self.events.put(("status", f"Cannot read {port}: {error}. Close Arduino Serial Monitor or another CSV viewer, then reconnect."))

        self.worker = threading.Thread(target=read, daemon=True)
        self.worker.start()

    def disconnect(self):
        self.stop.set()
        self.status.set("Disconnected. No motor command was sent.")

    def mirrored_angle(self, name, reading):
        config = self.directions["joints"][name]
        sign = config.get("model_to_encoder_sign")
        if sign not in (-1, 1):
            return None
        zero = self.zeros["joints"][name]["neutral_ticks"]
        angle = sign * (reading["ticks"] - zero) / TICKS_PER_RADIAN
        joint_id = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
        low, high = self.model.jnt_range[joint_id]
        return max(float(low), min(float(high), angle))

    def render(self, renderer, data):
        self.camera.azimuth, self.camera.elevation = {"Three-quarter": (135, -15), "Side": (90, -8), "Front / rear": (0, -8), "Top": (90, -89)}[self.view.get()]
        renderer.update_scene(data, camera=self.camera)
        return ImageTk.PhotoImage(Image.fromarray(renderer.render()))

    def tick(self):
        while True:
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "reading":
                value["received_at"] = time.monotonic()
                self.latest[value["id"]] = value
            else:
                self.status.set(value)

        self.reference.qpos[:] = self.model.qpos0
        self.live.qpos[:] = self.model.qpos0
        now = time.monotonic()
        live_count = 0
        for name, sid in JOINT_IDS:
            reading = self.latest.get(sid)
            zero = self.zeros["joints"][name]["neutral_ticks"]
            if reading is None:
                values = (sid, "—", zero, "—", "?", "NO DATA")
            else:
                age = now - reading["received_at"]
                angle = self.mirrored_angle(name, reading)
                if age > 2:
                    state = "STALE"
                elif reading["status"]:
                    state = f"SERVO STATUS {reading['status']}"
                elif angle is None:
                    state = "NO VERIFIED SIGN"
                else:
                    state = "LIVE"
                torque = "OFF" if reading["torque"] == 0 else "ON"
                values = (sid, reading["ticks"], zero, "—" if angle is None else f"{math.degrees(angle):+.1f}", torque, state)
                if angle is not None and age <= 2:
                    self.live.qpos[self.qadr[name]] = angle
                    live_count += 1
            self.table.item(name, values=values)
        mujoco.mj_forward(self.model, self.reference)
        mujoco.mj_forward(self.model, self.live)
        self.reference_photo = self.render(self.reference_renderer, self.reference)
        self.live_photo = self.render(self.live_renderer, self.live)
        self.reference_image.configure(image=self.reference_photo)
        self.live_image.configure(image=self.live_photo)
        if live_count:
            self.status.set(f"Mirroring {live_count}/12 fresh joints from ESP32 telemetry. Receive-only; no motor command is available in this program.")
        self.root.after(100, self.tick)

    def close(self):
        self.stop.set()
        if self.worker:
            self.worker.join(timeout=0.5)
        self.reference_renderer.close()
        self.live_renderer.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    LiveMirror(root)
    root.mainloop()


if __name__ == "__main__":
    main()
