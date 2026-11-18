import sys,json,zipfile
from pathlib import Path
sys.path.insert(0,'cad/frame_v10')
import build_frame_v10 as v
b=v.b
OUT=Path('cad/luca_test_stand').resolve()
v.v6.OUT=OUT
# Square telescoping column, two transverse M5 locking bolts.
base=b.rounded(-110,-90,0,220,180,8,10)
tube=b.cut(b.box(-27,-27,7.8,54,54,110.2),b.box(-21.4,-21.4,7.8,42.8,42.8,112))
base=b.fuse(base,tube)
# Four broad ribs increase the bending resistance at the base.
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon,BRepBuilderAPI_MakeFace
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Pnt,gp_Vec
for sign in (-1,1):
 wire=BRepBuilderAPI_MakePolygon()
 for x,z in [(sign*26,7.8),(sign*72,7.8),(sign*26,65)]:
  wire.Add(gp_Pnt(x,-4,z))
 wire.Close()
 rib=BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire.Wire()).Face(),gp_Vec(0,8,0)).Shape()
 base=b.fuse(base,rib)
 rib=v.v6.placed(rib,((0,-1,0,0),(1,0,0,0),(0,0,1,0)))
 base=b.fuse(base,rib)
for z in (58,78):base=b.cut(base,v.x_bore(-28,0,z,5.4,56))
slider=b.cut(b.box(-21,-21,0,42,42,150.2),b.box(-15,-15,-1,30,30,152))
slider=b.fuse(slider,b.rounded(-60,-35,150,120,70,6,5))
for z in (8,28,48,68):slider=b.cut(slider,v.x_bore(-22,0,z,5.4,44))
for x in (-49,43):
 slider=b.cut(slider,b.rounded(x,-18,149,6,36,8,2))
for x in (-96,96):
 for y in (-76,76):
  base=b.cut(base,b.cyl(x,y,-1,3.2,10))
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
report={}
for name,s in [('Stand_Base',base),('Stand_Slider',v.v6.placed(slider,((1,0,0,0),(0,-1,0,0),(0,0,-1,156))))]:
 assert BRepCheck_Analyzer(s).IsValid() and b.count_solids(s)==1
 lo,hi=b.bounds(s)
 size=[round(c-a,3) for a,c in zip(lo,hi)]
 assert max(size)<256
 b.write_step(OUT/f'{name}.step',{name:s})
 BRepMesh_IncrementalMesh(s,.15,False,.25,True)
 assert StlAPI_Writer().Write(s,str(OUT/f'{name}.stl'))
 report[name]=size
for lift in (10,30,50):
 s=v.v6.placed(slider,((1,0,0,0),(0,1,0,0),(0,0,1,lift)))
 assert v.v6.overlap(base,s)<.001
v.v6.write_assembly(OUT/'Luca_Stand_Assembled.step',{'Base':base,'Slider':v.v6.placed(slider,((1,0,0,0),(0,1,0,0),(0,0,1,30)))})
(OUT/'README.txt').write_text('Luca bench stand\nPrint one base and one slider at 100 percent. Slider STL is already oriented with its top pad against the bed. Base prints upright. PETG, 5 walls, 6 top/bottom layers, 30 percent infill are starting settings. Horizontal 5.4 mm holes may need local support or drill cleanup.\nBase 220 x 180 mm. Support heights 166,186,206 mm. Start at 186 mm; verify feet clear through intended motion. Use TWO M5 x 65 mm bolts, four washers and two locking nuts through column holes at 58 and 78 mm. Both bolts must pass through both sides of base and slider. Do not overtighten hollow column.\nPad 120 x 70 mm. Add thin rubber/foam and strap chassis to pad using the two slots. Position the pad against clear chassis underside near the balance point; avoid exposed wiring and screw heads. Keep legs clear of stand and base. Corner holes permit fastening to a bench or larger board. No physical load or tip testing has been performed; first test with robot unpowered and restrain stand before powered leg tests. This is a bench motion stand; walking on the floor and large unsupported swings require separate testing.\n')
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
with zipfile.ZipFile(OUT/'Luca_Stand_Print_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in [*OUT.glob('*.stl'),OUT/'README.txt']:z.write(p,p.name)
print(report)
