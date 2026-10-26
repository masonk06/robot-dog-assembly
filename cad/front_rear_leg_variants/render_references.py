"""Render the two reference STL assemblies for visual verification."""
from pathlib import Path
import re
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

OUT = Path(__file__).resolve().parent

for label in ("Front", "Rear"):
    raw = (OUT / f"{label}_Leg_Orientation_Reference.stl").read_text()
    points = np.array([[float(a), float(b), float(c)] for a,b,c in re.findall(r"vertex\s+([^\s]+)\s+([^\s]+)\s+([^\s]+)", raw)])
    triangles = points.reshape(-1,3,3)
    # A subsample keeps the PNG light while leaving enough triangles to inspect fit.
    triangles = triangles[::max(1, len(triangles)//9000)]
    fig = plt.figure(figsize=(10,8), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(triangles, facecolors="#8496b8", edgecolors="#263347", linewidths=.08))
    points = triangles.reshape(-1,3); lo, hi = points.min(0), points.max(0); center=(lo+hi)/2; span=(hi-lo).max()/2
    ax.set_xlim(center[0]-span, center[0]+span); ax.set_ylim(center[1]-span, center[1]+span); ax.set_zlim(center[2]-span, center[2]+span)
    ax.view_init(elev=18, azim=-55); ax.set_axis_off(); ax.set_title(f"{label} leg installation reference")
    plt.tight_layout(); fig.savefig(OUT / f"{label}_Leg_Orientation_Reference.png", dpi=160); plt.close(fig)
