from pathlib import Path
import json,numpy as np
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Trsf
P=Path(__file__).resolve().parent
records={p['name']:p for p in json.loads((P/'RoboDog_placements.json').read_text())['parts']}
def load(p):
 r=STEPControl_Reader();r.ReadFile(str(p));r.TransferRoots();return r.OneShape()
def vol(s):
 q=GProp_GProps();BRepGProp.VolumeProperties_s(s,q);return abs(q.Mass())
def placed(s,m):
 t=gp_Trsf();t.SetValues(*[m[i][j] for i in range(3) for j in range(4)]);return BRepBuilderAPI_Transform(s,t,True).Shape()
frame=load(P/'solid_sources/FRAME V2.step');case=load(P/'revision_sources/STS3215_case_fixed.step');checks=[]
for leg in ['front_left','front_right','rear_left','rear_right']:
 m=records[leg+'_servo_hip_roll']['transform'];op=BRepAlgoAPI_Common(frame,placed(case,m));op.SetFuzzyValue(.0001);op.Build();v=vol(op.Shape());checks.append(dict(part=leg+'_servo_hip_roll',frame_overlap_mm3=v));print(leg,v,flush=True);(P/'RoboDog_fit_checks.json').write_text(json.dumps(checks,indent=2))
boot=load(P/'solid_sources/boots.step');knee=load(P/'solid_sources/Part Studio 1 - Knee Pitch v2.step');op=BRepAlgoAPI_Common(boot,knee);op.SetFuzzyValue(.0001);op.Build();v=vol(op.Shape());checks.append(dict(part='boot_and_knee_native_fit',overlap_mm3=v));print('Boot/knee native overlap',v,flush=True);(P/'RoboDog_fit_checks.json').write_text(json.dumps(checks,indent=2))
