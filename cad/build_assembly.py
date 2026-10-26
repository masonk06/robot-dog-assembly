from pathlib import Path
import struct, json, zipfile
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"source"
# Layout assumptions in nominal millimetres. STL files do not encode units.
HIP_X=75.0
HIP_Y=85.0
BRACKET_TOP_Z=50.0
KNEE_Z_ADJUST=35.0
ANCHOR=np.array([-57.361923,44.1,74.545677])
def read(p):
 b=p.read_bytes(); n=struct.unpack_from("<I",b,80)[0]
 assert len(b)==84+50*n
 return np.ndarray(n,dtype=np.dtype([("normal","<f4",3),("v","<f4",(3,3)),("attr","<u2")]),buffer=b,offset=84)["v"].copy().astype(float)
def write(p,v):
 normals=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]); lengths=np.linalg.norm(normals,axis=1); normals/=np.where(lengths>0,lengths,1)[:,None]
 data=np.zeros(len(v),dtype=np.dtype([("normal","<f4",3),("v","<f4",(3,3)),("attr","<u2")]))
 data["normal"]=normals;data["v"]=v
 p.write_bytes(b"Robot dog conceptual layout; units assumed mm".ljust(80,b" ")+struct.pack("<I",len(v))+data.tobytes())
parts=[];records=[]
out=ROOT/"positioned_parts";out.mkdir(exist_ok=True)
def add(name,v,color,meta):
 write(out/(name+".stl"),v);parts.append((name,v,color));records.append(dict(name=name,**meta))
for source,name,color in [("Part Studio 3 - Part 2.stl","frame","#425568"),("Part Studio 3 - Top Cover Body.stl","top_cover","#99aabd")]:
 add(name,read(SOURCE/source),color,dict(source=source,transform=np.eye(4).tolist()))
for name,sx,sy,angle in [("front_left",1,1,0),("front_right",1,-1,180),("rear_left",-1,1,0),("rear_right",-1,-1,180)]:
 # Rotate the complete source leg 180 degrees for the opposite side; no mirrored meshes.
 a=np.deg2rad(angle);r=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
 target=np.array([sx*HIP_X,sy*HIP_Y,BRACKET_TOP_Z])
 for short,file,color in [("hip_roll","Hip Roll V3","#d99a3c"),("hip_pitch_L","Hip Pitch L","#5799bd"),("hip_pitch_R","Hip Pitch R","#5799bd"),("knee_v2","Knee Pitch v2","#657b89")]:
  source="Part Studio 1 - "+file+".stl"; adjustment=np.array([0,0,KNEE_Z_ADJUST if short=="knee_v2" else 0])
  t=target-r@ANCHOR+r@adjustment;matrix=np.eye(4);matrix[:3,:3]=r;matrix[:3,3]=t
  add(name+"_"+short,read(SOURCE/source)@r.T+t,color,dict(source=source,transform=matrix.tolist()))
write(ROOT/"robot_dog_layout.stl",np.concatenate([p[1] for p in parts]))
# OBJ keeps named objects and per-part colours for CAD/mesh import.
with (ROOT/"robot_dog_layout.obj").open("w") as f,(ROOT/"robot_dog_layout.mtl").open("w") as m:
 f.write("# Concept layout; assumed millimetres\nmtllib robot_dog_layout.mtl\n");offset=1
 for name,v,color in parts:
  rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];m.write("newmtl "+name+"\nKd "+" ".join(map(str,rgb))+"\n")
  f.write("o "+name+"\nusemtl "+name+"\n")
  for point in v.reshape(-1,3):f.write("v %.6f %.6f %.6f\n"%tuple(point))
  for j in range(len(v)):f.write("f %d %d %d\n"%(offset+3*j,offset+3*j+1,offset+3*j+2))
  offset+=len(v)*3
(ROOT/"placements.json").write_text(json.dumps(dict(status="Concept layout; mechanical fit unverified",units="assumed mm",parts=records),indent=2))
fig=plt.figure(figsize=(13,7));allv=np.concatenate([p[1] for p in parts]);lo=allv.min(axis=(0,1));hi=allv.max(axis=(0,1));c=(lo+hi)/2;rad=max(hi-lo)/2*1.08
for i,(elev,azim,title) in enumerate([(22,-48,"Four-leg layout"),(90,-90,"Top view")]):
 ax=fig.add_subplot(1,2,i+1,projection="3d")
 for name,v,color in parts:ax.add_collection3d(Poly3DCollection(v,facecolor=color,edgecolor="none",linewidth=0))
 ax.set(xlim=(c[0]-rad,c[0]+rad),ylim=(c[1]-rad,c[1]+rad),zlim=(c[2]-rad,c[2]+rad),xlabel="X (assumed mm)",ylabel="Y",zlabel="Z",title=title);ax.set_box_aspect((1,1,1));ax.view_init(elev,azim)
fig.suptitle("Robot dog ? concept assembly using knee V2\nMounts, motor spacing and motion clearance require verification")
fig.tight_layout();fig.savefig(ROOT/"assembly_preview.png",dpi=150);plt.close(fig)
assert len(parts)==18
assert all(np.isfinite(v).all() for _,v,_ in parts)
print("Exported 18 separate parts, combined STL, named OBJ, transforms and preview.")
