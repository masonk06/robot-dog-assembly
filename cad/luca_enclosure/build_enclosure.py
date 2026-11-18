import sys,json,zipfile
from pathlib import Path
sys.path.insert(0,'cad/frame_v10')
import build_frame_v10 as v
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopoDS import TopoDS
b=v.b
out=v.CAD/'luca_enclosure'
v.v6.OUT=out
e=TopExp_Explorer(b.load(v.CAD/'frame_p2s_camera_insert/RoboDog_P2S_Camera_Onshape.step'),TopAbs_SOLID)
ss=[]
while e.More():
 ss.append(TopoDS.Solid(e.Current())); e.Next()
chassis=max(ss,key=b.volume)
parts={}
report={}
for name,x,w,mx in [('Front_Cover',-70,114.8,-62.5),('Rear_Cover',45.2,114.8,152.5)]:
 s=b.box(x,-65,50.3,w,130,33.7)
 s=b.cut(s,b.box(x+(-1 if x>0 else 2),-63,49,w-1,126,33))
 # Open the split end completely below the roof.
 seam=44 if x<0 else 44.5
 s=b.cut(s,b.box(seam,-63,49,2,126,33))
 for y in (-57.5,57.5):
  s=b.fuse(s,b.box(mx-2.4,y-2.4,44.85,4.8,4.8,37.4))
  s=b.cut(s,b.cyl(mx,y,44,1.2,42))
 # Vent slots over electronics, separated from corner and seam hardware.
 for xx in range(int(x+20),int(x+w-15),10):
  s=b.cut(s,b.rounded(xx,-26,81,4,52,5,1.8))
 for y in (-40,40):
  hx=39 if x<0 else 51
  s=b.cut(s,b.cyl(hx,y,81,1.7,5))
 assert v.v6.overlap(s,chassis)<.01
 parts[name]=s
 # Print roof down. Assembled Z=84 maps to print Z=0.
 printshape=v.v6.placed(s,((1,0,0,-x),(0,-1,0,65),(0,0,-1,84)))
 report[name]=v.v6.export_part(name,printshape)
plate=b.rounded(35,-46,84,20,12,2,2)
for x in (39,51):plate=b.cut(plate,b.cyl(x,-40,83,1.7,4))
report['Seam_Plate']=v.v6.export_part('Seam_Plate',v.v6.placed(plate,((1,0,0,-35),(0,1,0,46),(0,0,1,-84))))
parts['Seam_Plate_Left']=plate
parts['Seam_Plate_Right']=v.v6.placed(plate,((1,0,0,0),(0,1,0,80),(0,0,1,0)))
assert v.v6.overlap(parts['Front_Cover'],parts['Rear_Cover'])<.001
# Component clearances, based on current measured case dimensions.
refs={'Pi':b.box(-41.4,-31,37.8,91,62,31.6),'S3':b.box(62,-30.5,41.6,28,61,16),'PDS':b.box(94,-44.25,13,60,88.5,23.1)}
for n,s in parts.items():
 for key,r in refs.items():assert v.v6.overlap(s,r)<.01,(n,key)
v.v6.write_assembly(out/'Luca_Enclosure_Assembled.step',parts)
v.v6.write_assembly(out/'Luca_Enclosure_On_Chassis.step',{'Chassis':chassis,**parts})
(out/'validation.json').write_text(json.dumps(report,indent=2))
(out/'Assembly.txt').write_text('Luca enclosure: two 114.8 x 130 mm halves, 0.4 mm centre seam. Print each STL roof down as supplied, and print two seam plates. Assembled STEP retains chassis coordinates. Cover top Z=84 mm. Vent slots permit airflow; camera and XT60 openings remain below the cover. Attach to the four 5 x 5 mm corner pads centred at X=-62.5 and 152.5, Y=+/-57.5 mm. Pads top Z=44.7493; cover posts start at 44.85. Pads require pilot drilling: start with 1.6 mm for M2 self-tapping screws and test PETG screw fit. Screw passage in cover is 2.4 mm. Roof-to-pad distance is about 39.25 mm; nominal M2 x 42 mm screws provide about 2.75 mm engagement. Verify actual screw length before tightening. Join seam with two plates and four M3 x 8 mm screws plus nuts; fit from inside before installation. Solid and static component clearance checks passed. Wiring, plugs, fan airflow and moving-leg sweeps remain unverified. This is a ventilated top enclosure; the chassis side openings below Z=50 remain open.\n')
with zipfile.ZipFile(out/'Luca_Enclosure_Print_Pack.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in [*out.glob('*.stl'),out/'Assembly.txt']:z.write(p,p.name)
print('All enclosure exports complete')

