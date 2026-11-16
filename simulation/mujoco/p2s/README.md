# Luca P2S chassis gait preview

Current geometry preview: 230 x 179.8 mm chassis, rear assemblies translated
+60 mm in CAD X, front hip-pitch hinges corrected +30 mm to match the
servo output-disc centers. CAD units are mm; front is negative X, Z is up.
Original model and trained checkpoints remain unchanged.

## Windows laptop setup

```powershell
git clone https://github.com/masonk06/robot-dog-assembly.git
cd robot-dog-assembly
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe simulation\mujoco\view_dog_walk.py --model simulation\mujoco\p2s\robot_dog_p2s.xml --viewer --lift-mm 10 --stride-mm 15
```

If already cloned, run `git pull` from that checkout first.
The preview holds the base fixed and repeats a scripted 10-second cycle.
It does not connect to hardware or execute a learned policy. Close the viewer
window to stop it. To inspect only the model, use:

```powershell
.\.venv\Scripts\python.exe -m mujoco.viewer --mjcf=simulation\mujoco\p2s\robot_dog_p2s.xml
```

## Current limitations and next work

- Original provisional mass/inertia values remain (total 1.923 kg).
  The user's new 1.546 kg measurement still needs its component inclusion list.
- Installed electronics and final mass distribution are not yet represented.
- Recalculate gait inverse kinematics for the corrected front hinges before
  using this gait as a training reference. The present preview is for visual review.
- Verify attachment alignment, collision proxies, joint limits and dynamics
  before evaluating or transferring a trained policy.

`validation.json` records chassis bounds and zero-pose foot shifts.
Rebuild with `python simulation/mujoco/build_p2s_preview.py`.
Source chassis: `cad/frame_p2s_camera_insert/Chassis.stl`.
The assembly STEP in that folder provides CAD context; newer standalone trays
supersede historical trays embedded in the assembly.
