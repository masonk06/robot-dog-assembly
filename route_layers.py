"""Complete connections with four-via layer transitions; engineering only."""
import route_board as r, heapq, math
from pathlib import Path
p=r.p
target=Path(__file__).parent/'revision_four_leg/Luca_power_distribution_four_leg.kicad_pcb'
r.b=p.LoadBoard(str(target));r.pads=list(r.b.GetPads());r.margin=.35
r.xmax=198.5;r.nx=355
r.xx,r.yy=r.np.meshgrid(r.xmin+r.np.arange(r.nx)*r.step,r.ymin+r.np.arange(r.ny)*r.step,indexing='ij')
r.tracks=[]
for t in r.b.GetTracks():
 a=(t.GetStart().x/1e6,t.GetStart().y/1e6);c=(t.GetEnd().x/1e6,t.GetEnd().y/1e6)
 layers=(p.F_Cu,p.B_Cu) if isinstance(t,p.PCB_VIA) else (t.GetLayer(),)
 for l in layers:r.tracks.append((a,c,t.GetNetCode(),t.GetWidth(l)/1e6 if isinstance(t,p.PCB_VIA) else t.GetWidth()/1e6,l))
via_orientation={}
def route3(a,c,n,w,startlayers=(0,2),endlayers=(0,2)):
 masks=[r.make_mask(n,w,l) for l in (0,2)];via=[r.make_mask(n,1.6 if w>=3 else 1.1,l) for l in (0,2)]
 if w>=3:
  escape=(r.xx-a[0])**2+(r.yy-a[1])**2<3**2
  for i,l in enumerate((0,2)):
   narrow=r.make_mask(n,2.6,l);masks[i][escape]=narrow[escape]
 si,ei=r.idx(a),r.idx(c);end={(ei[0],ei[1],l//2) for l in endlayers if not masks[l//2][ei]}
 q=[];cost={};prev={}
 for l in startlayers:
  s=(*si,l//2)
  if not masks[l//2][si]:cost[s]=0;heapq.heappush(q,(0,0,s))
 while q:
  _,g,u=heapq.heappop(q)
  if g!=cost[u]:continue
  if u in end:
   path=[u]
   while u in prev:u=prev[u];path.append(u)
   return list(reversed(path))
  neighbors=[]
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   v=(u[0]+dx,u[1]+dy,u[2])
   if not(0<=v[0]<r.nx and 0<=v[1]<r.ny) or masks[u[2]][v[:2]]:continue
   if dx and dy and (masks[u[2]][u[0]+dx,u[1]] or masks[u[2]][u[0],u[1]+dy]):continue
   neighbors.append((v,math.hypot(dx,dy)))
  offsets=[((4,0),(-4,0)),((0,4),(0,-4))] if w>=3 else [((0,0),)]
  for offsets_option in offsets if not masks[0][u[:2]] and not masks[1][u[:2]] else []:
   if all(0<=u[0]+dx<r.nx and 0<=u[1]+dy<r.ny and not via[0][u[0]+dx,u[1]+dy] and not via[1][u[0]+dx,u[1]+dy] for dx,dy in offsets_option):
    via_orientation[(n,u[0],u[1])]=offsets_option
    neighbors.append(((u[0],u[1],1-u[2]),30));break
  for v,extra in neighbors:
   ng=g+extra
   if ng<cost.get(v,1e99):cost[v]=ng;prev[v]=u;heapq.heappush(q,(ng+math.hypot(v[0]-ei[0],v[1]-ei[1]),ng,v))
 return None
def xy(v):return (r.xmin+v[0]*r.step,r.ymin+v[1]*r.step)
def commit(path,a,c,n,w):
 pts=[(a,path[0][2])]+[(xy(v),v[2]) for v in path]+[(c,path[-1][2])]
 for (aa,l),(cc,ll) in zip(pts,pts[1:]):
  if l==ll:
   width=2.6 if w>=3 and min(math.dist(aa,a),math.dist(cc,a))<3 else w
   r.commit([aa,cc],n,width,2*l)
  else:
   ix,iy=r.idx(aa);offsets=tuple((dx*r.step,dy*r.step) for dx,dy in via_orientation[(n,ix,iy)])
   diameter,drill=(1.6,1.0) if w>=3 else (1.1,.5)
   for dx,dy in offsets:
    v=p.PCB_VIA(r.b);v.SetPosition(p.VECTOR2I(round((aa[0]+dx)*1e6),round((aa[1]+dy)*1e6)));v.SetWidth(p.FromMM(diameter));v.SetDrill(p.FromMM(drill));v.SetLayerPair(0,2);v.SetNetCode(n);r.b.Add(v)
    for layer in (0,2):
     r.commit([aa,(aa[0]+dx,aa[1]+dy)],n,1.2,layer)
     r.tracks.append(((aa[0]+dx,aa[1]+dy),(aa[0]+dx,aa[1]+dy),n,diameter,layer))
def pad(ref,num):return next(q for q in r.pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
unresolved=[]
for name in ['/SERVO_V+','/VBAT_RAW','/VBAT_FUSED','/FL_V+','/FR_V+','/RL_V+','/RR_V+','/SERVO','Net-(J7-Pin_1)','Net-(J10-Pin_1)','Net-(J5-Pin_1)','Net-(J10-Pin_3)','GND']:
 n=r.b.FindNet(name).GetNetCode();pp=[q for q in r.pads if q.GetNetCode()==n]
 pp.sort(key=lambda q:(q.GetAttribute()==p.PAD_ATTRIB_SMD,q.GetParentFootprint().GetReference().startswith('C')))
 if name=='GND':pp.sort(key=lambda q:q.GetParentFootprint().GetReference()!='J1')
 root=pp[0]
 for q in pp[1:]:
  if q.GetParentFootprint().GetReference()=='C2':continue
  r.b.BuildConnectivity();connected=r.b.GetConnectivity().GetConnectedPads(root)
  # Ground is explicitly re-checked with wide paths regardless of thin C2.
  if name!='GND' and any(x.m_Uuid==q.m_Uuid for x in connected):continue
  wide=name in ['GND','/SERVO_V+','/VBAT_RAW','/VBAT_FUSED','/FL_V+','/FR_V+','/RL_V+','/RR_V+']
  w=3 if wide else 1
  a,c=r.xy(q),r.xy(root);sl=tuple(l for l in (0,2) if q.IsOnLayer(l));el=tuple(l for l in (0,2) if root.IsOnLayer(l))
  path=route3(a,c,n,w,sl,el)
  if not path:unresolved.append((name,q.GetParentFootprint().GetReference(),w));print('UNRESOLVED',unresolved[-1],flush=True);continue
  commit(path,a,c,n,w);print('Connected',name,q.GetParentFootprint().GetReference(),w,flush=True)
print('REMAINING',unresolved,flush=True)
p.SaveBoard(str(target),r.b)
