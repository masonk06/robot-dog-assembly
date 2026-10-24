from pathlib import Path
import json
from OCP.StlAPI import StlAPI_Reader
from OCP.TopoDS import TopoDS_Shape,TopoDS
from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing,BRepBuilderAPI_MakeSolid
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.STEPControl import STEPControl_Writer,STEPControl_AsIs
P=Path(__file__).resolve().parent;S=P/'revision_sources';O=P/'solid_sources';O.mkdir(exist_ok=True);checks=[]
for f in S.glob('*.stl'):
 s=TopoDS_Shape();assert StlAPI_Reader().Read(s,str(f));sew=BRepBuilderAPI_Sewing(.0001);sew.Add(s);sew.Perform();s=BRepBuilderAPI_MakeSolid(TopoDS.Shell(sew.SewedShape())).Solid();assert BRepCheck_Analyzer(s).IsValid(),f.name;u=ShapeUpgrade_UnifySameDomain(s,True,True,False);u.Build();s=u.Shape();assert BRepCheck_Analyzer(s).IsValid();w=STEPControl_Writer();w.Transfer(s,STEPControl_AsIs);w.Write(str(O/(f.stem+'.step')));checks.append(dict(source=f.name,valid_solid=True,conversion='Faceted solid; original STL unchanged'));print('Converted',f.name,flush=True)
(P/'solid_conversion.json').write_text(json.dumps(checks,indent=2))
