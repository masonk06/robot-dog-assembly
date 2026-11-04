import pcbnew as p, numpy as np, heapq, math
from pathlib import Path
SRC=Path(r'C:\Users\mmbec\Documents\self_balancing_robot\self_balancing_robot_v2\Luca\Luca_power_distribution\Luca_power_distribution.kicad_pcb')
OUT=SRC.with_name('Luca_power_distribution_routed.kicad_pcb')
b=p.LoadBoard(str(SRC)); pads=list(b.GetPads()); tracks=[]
step=.25; xmin,ymin=110,70; nx,ny=275,241
xx,yy=np.meshgrid(xmin+np.arange(nx)*step,ymin+np.arange(ny)*step,indexing='ij')
def xy(pad): return (pad.GetPosition().x/1e6,pad.GetPosition().y/1e6)
def idx(pt): return (round((pt[0]-xmin)/step),round((pt[1]-ymin)/step))
def distseg(a,c):
 dx,dy=c[0]-a[0],c[1]-a[1]; den=dx*dx+dy*dy
 t=np.clip(((xx-a[0])*dx+(yy-a[1])*dy)/(den or 1),0,1)
 return np.hypot(xx-a[0]-t*dx,yy-a[1]-t*dy)
mask_cache={}
margin=.55
xmax=178.5
def route(a,c,net,w,layer):
 cachekey=(net,w,layer,len(tracks))
 if cachekey in mask_cache:
  blocked=mask_cache[cachekey]
 else:
  blocked=make_mask(net,w,layer)
  mask_cache[cachekey]=blocked
 return search(a,c,blocked)
def make_mask(net,w,layer):
 blocked=(xx<110.55+w/2)|(xx>xmax-.55-w/2)|(yy<70.55+w/2)|(yy>129.45-w/2)
 for pad in pads:
  if pad.GetNetCode()==net: continue
  if pad.GetAttribute()==__import__('pcbnew').PAD_ATTRIB_SMD and not pad.IsOnLayer(layer):continue
  x,y=xy(pad); rad=max(pad.GetSize().x,pad.GetSize().y)/2e6
  if pad.GetShape()==p.PAD_SHAPE_CIRCLE:
   blocked |= np.hypot(xx-x,yy-y)<rad+w/2+margin
  else:
   blocked |= np.hypot(np.maximum(abs(xx-x)-rad,0),np.maximum(abs(yy-y)-rad,0))<w/2+margin
 for ta,tc,tn,tw,tl in tracks:
  if tn!=net and tl==layer: blocked |= distseg(ta,tc)<(tw+w)/2+margin
 return blocked
def search(a,c,blocked):
 start,end=idx(a),idx(c)
 if blocked[start] or blocked[end]: return None
 q=[(0,0,start)]; costs={start:0}; prev={}
 while q:
  _,g,u=heapq.heappop(q)
  if g!=costs[u]: continue
  if u==end:
   path=[u]
   while u!=start: u=prev[u]; path.append(u)
   path.reverse(); pts=[a]+[(xmin+v[0]*step,ymin+v[1]*step) for v in path]+[c]
   clean=[pts[0]]
   for i in range(1,len(pts)-1):
    v0=(pts[i][0]-clean[-1][0],pts[i][1]-clean[-1][1]); v1=(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1])
    if abs(v0[0]*v1[1]-v0[1]*v1[0])>1e-8: clean.append(pts[i])
   clean.append(c); return clean,g
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   v=(u[0]+dx,u[1]+dy)
   if not(0<=v[0]<nx and 0<=v[1]<ny) or blocked[v]: continue
   if dx and dy and (blocked[u[0]+dx,u[1]] or blocked[u[0],u[1]+dy]): continue
   ng=g+math.hypot(dx,dy)
   if ng<costs.get(v,1e99):
    costs[v]=ng; prev[v]=u; heapq.heappush(q,(ng+math.hypot(v[0]-end[0],v[1]-end[1]),ng,v))
 return None
def commit(pts,net,w,layer):
 for a,c in zip(pts,pts[1:]):
  if math.dist(a,c)<1e-6: continue
  t=p.PCB_TRACK(b); t.SetStart(p.VECTOR2I(round(a[0]*1e6),round(a[1]*1e6))); t.SetEnd(p.VECTOR2I(round(c[0]*1e6),round(c[1]*1e6))); t.SetWidth(p.FromMM(w)); t.SetLayer(layer); t.SetNetCode(net); b.Add(t); tracks.append((a,c,net,w,layer))
for net in (() if __name__ != '__main__' else (9,3,6,5,7,4,8,1,2)):
 pp=[q for q in pads if q.GetNetCode()==net]; connected=[pp.pop(0)]
 while pp:
  candidates=sorted((math.dist(xy(a),xy(c))+(1000 if a.GetParentFootprint().GetReference()=='C2' else 0)+(500 if c.GetParentFootprint().GetReference()=='C2' else 0),i,j) for i,a in enumerate(connected) for j,c in enumerate(pp))
  found=None
  for _,i,j in candidates:
   a,c=connected[i],pp[j]; w=3 if net in (9,3,6,5,2) else 1
   if a.GetParentFootprint().GetReference()=='C2' or c.GetParentFootprint().GetReference()=='C2': w=.5
   for layer in (p.F_Cu,p.B_Cu):
    result=route(xy(a),xy(c),net,w,layer)
    if result: found=(result[0],net,w,layer,j); break
   if found: break
  if not found: raise RuntimeError(('No route',net,[q.GetParentFootprint().GetReference() for q in pp]))
  pts,net,w,layer,j=found; commit(pts,net,w,layer); connected.append(pp.pop(j)); print(net,w,layer,len(pts),flush=True)
if __name__ == '__main__':
 p.SaveBoard(str(OUT),b)
 print(OUT)
