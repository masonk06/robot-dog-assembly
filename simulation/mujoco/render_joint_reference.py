"""Render saved simulation joint targets as a fixed-base visual reference."""
import argparse
import csv
from pathlib import Path
import subprocess
import mujoco

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('model', type=Path)
p.add_argument('trajectory', type=Path)
p.add_argument('output', type=Path)
p.add_argument('--ffmpeg', required=True)
args = p.parse_args()
with args.trajectory.open(newline='') as f:
    reader = csv.DictReader(f)
    names = [n for n in reader.fieldnames if n != 'time_seconds']
    rows = list(reader)
model = mujoco.MjModel.from_xml_path(str(args.model))
data = mujoco.MjData(model)
addresses = []
for name in names:
    joint = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
    if joint < 0: raise ValueError(f'Missing joint {name}')
    addresses.append(model.jnt_qposadr[joint])
renderer = mujoco.Renderer(model, width=640, height=480)
camera = mujoco.MjvCamera()
camera.lookat[:] = [0, 0, .08]
camera.distance = .48
camera.azimuth = 135
camera.elevation = -15
process = subprocess.Popen([args.ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo',
                            '-pix_fmt', 'rgb24', '-s', '640x480', '-r', '25', '-i', '-',
                            '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(args.output)],
                           stdin=subprocess.PIPE)
try:
    for frame in range(int(float(rows[-1]['time_seconds']) * 25)):
        row = rows[min(round(frame * 2), len(rows)-1)]
        data.qpos[:] = model.qpos0
        for address, name in zip(addresses, names): data.qpos[address] = float(row[name])
        mujoco.mj_forward(model, data)
        renderer.update_scene(data, camera=camera)
        process.stdin.write(renderer.render().tobytes())
finally:
    process.stdin.close()
    renderer.close()
if process.wait() != 0: raise RuntimeError('ffmpeg failed')
