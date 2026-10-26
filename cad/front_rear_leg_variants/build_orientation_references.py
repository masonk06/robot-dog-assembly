"""Create front/rear installation-reference assemblies from RoboDog V2.

These files are deliberately *not* printable part variants.  They use the
unchanged supplied print geometry and the exact saved V2 placement transforms
for one front-left and one rear-left leg, normalized to their hip-roll axes.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.STEPControl import STEPControl_Reader, STEPControl_Writer, STEPControl_AsIs
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Compound
from OCP.gp import gp_Trsf

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
PLACEMENTS = json.loads((ROOT / "RoboDog_placements.json").read_text())
PART = {part["name"]: part for part in PLACEMENTS["parts"]}
SOLIDS = ROOT / "solid_sources"
PRINTS = ["hip_roll", "hip_pitch_L", "hip_pitch_R", "knee_v2", "boot"]

def shape_from_step(path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)).name != "IFSelect_RetDone":
        raise RuntimeError(f"Could not read {path}")
    reader.TransferRoots()
    return reader.OneShape()

def transform_shape(shape, matrix):
    trsf = gp_Trsf()
    trsf.SetValues(*[float(x) for x in matrix[:3, :].flatten()])
    return BRepBuilderAPI_Transform(shape, trsf, True).Shape()

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def build_reference(label, leg):
    axis = np.asarray(PART[f"{leg}_servo_hip_roll"]["axis_point"], dtype=float)
    compound = TopoDS_Compound()
    builder = BRep_Builder(); builder.MakeCompound(compound)
    member_data = []
    for suffix in PRINTS:
        key = f"{leg}_{suffix}"
        part = PART[key]
        matrix = np.asarray(part["transform"], dtype=float).copy()
        matrix[:3, 3] -= axis
        source_step = SOLIDS / (Path(part["source"]).stem + ".step")
        shape = transform_shape(shape_from_step(source_step), matrix)
        builder.Add(compound, shape)
        source_stl = ROOT / "revision_sources" / part["source"]
        member_data.append({
            "component": suffix,
            "source_stl": part["source"],
            "source_sha256": sha256(source_stl),
            "reference_transform_mm": matrix.round(9).tolist(),
        })
    step_path = OUT / f"{label}_Leg_Orientation_Reference.step"
    writer = STEPControl_Writer(); writer.Transfer(compound, STEPControl_AsIs); writer.Write(str(step_path))
    stl_path = OUT / f"{label}_Leg_Orientation_Reference.stl"
    BRepMesh_IncrementalMesh(compound, 0.1, False, 0.5, True)
    stl_writer = StlAPI_Writer(); stl_writer.Write(compound, str(stl_path))
    return {"label": label, "source_leg": leg, "reference_origin": "hip-roll servo output axis", "hip_roll_axis_frame_mm": axis.tolist(), "members": member_data, "step": step_path.name, "stl": stl_path.name}

front = build_reference("Front", "front_left")
rear = build_reference("Rear", "rear_left")
summary = {
    "frame": "FRAME V2.stl",
    "front_definition": "-X", "left_definition": "-Y",
    "conclusion": "No front-only or rear-only printed mesh exists. Front and rear use the identical five printed source files; the difference is installation orientation and location on FRAME V2.",
    "per_leg_print_quantity": {"Hip Roll V3": 1, "Hip Pitch L": 1, "Hip Pitch R": 1, "Knee Pitch v2": 1, "TPU 95 boot": 1},
    "robot_print_quantity": {"Hip Roll V3": 4, "Hip Pitch L": 4, "Hip Pitch R": 4, "Knee Pitch v2": 4, "TPU 95 boot": 4},
    "front_reference": front,
    "rear_reference": rear,
}
(OUT / "orientation_reference_manifest.json").write_text(json.dumps(summary, indent=2))
print(json.dumps(summary, indent=2))
