import pcbnew as p
import sys
from collections import defaultdict
path=r'C:\Users\mmbec\Documents\self_balancing_robot\self_balancing_robot_v2\Luca\Luca_power_distribution\Luca_power_distribution_routed.kicad_pcb'
if len(sys.argv)>1:path=sys.argv[1]
b=p.LoadBoard(path)
print('Zones:',len(list(b.Zones())))
for f in b.GetFootprints():
 if f.GetReference() in ('J1','J3','F1','F2','F5','F7'):
  print(f.GetReference(),f.GetValue(),[(q.GetNumber(),q.GetNetname()) for q in f.Pads() if q.GetNumber()])
# Test whether all ground connector pads remain connected after removing sub-1mm tracks.
ts=[t for t in b.GetTracks() if t.GetNetname()=='GND' and t.GetWidth()>=p.FromMM(1)]
adj=defaultdict(set)
def key(v): return (v.x,v.y)
for t in ts:
 a,c=key(t.GetStart()),key(t.GetEnd()); adj[a].add(c);adj[c].add(a)
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()!='GND':continue
  center=key(q.GetPosition()); nodes=[]
  for v in list(adj):
   if q.HitTest(p.VECTOR2I(*v)):nodes.append(v)
  for v in nodes:adj[center].add(v);adj[v].add(center)
seen=set(); components=[]
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()!='GND' or f.GetReference()=='C2':continue
  v=key(q.GetPosition())
  if v in seen:continue
  todo=[v]; comp=set()
  while todo:
   u=todo.pop()
   if u in comp:continue
   comp.add(u);todo.extend(adj[u]-comp)
  seen |= comp
  names=[f'{ff.GetReference()}.{qq.GetNumber()}' for ff in b.GetFootprints() for qq in ff.Pads() if qq.GetNetname()=='GND' and key(qq.GetPosition()) in comp]
  components.append(names)
print('GND components using >=1mm traces:',components)
