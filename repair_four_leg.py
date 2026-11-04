import route_board as r
from pathlib import Path
from collections import defaultdict
p=r.p
target=Path(__file__).parent/'revision_four_leg/Luca_power_distribution_four_leg.kicad_pcb'
r.b=p.LoadBoard(str(target));r.pads=list(r.b.GetPads());r.margin=.35
r.tracks=[((t.GetStart().x/1e6,t.GetStart().y/1e6),(t.GetEnd().x/1e6,t.GetEnd().y/1e6),t.GetNetCode(),t.GetWidth()/1e6,t.GetLayer()) for t in r.b.GetTracks()]
def pad(ref,num):return next(q for q in r.pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
a,c=pad('F2','2'),pad('J2','1');n=a.GetNetCode()
result=r.route(r.xy(a),r.xy(c),n,2,p.F_Cu)
if result:r.commit(result[0],n,2,p.F_Cu);print('Adapter routed at 2mm',flush=True)
else:print('Adapter 2mm route unavailable',flush=True)
# Audit copper graph with ALL narrow tracks removed; bridge isolated ground
# connector islands to the >=3mm main return network, never through C2.
ground=pad('J1','2').GetNetCode()
for iteration in range(15):
 adj=defaultdict(set)
 for a,c,n,w,l in r.tracks:
  if n==ground and w>=3:adj[(a,l)].add((c,l));adj[(c,l)].add((a,l))
 for q in r.pads:
  if q.GetNetCode()!=ground:continue
  nodes=[v for v in list(adj) if q.IsOnLayer(v[1]) and q.HitTest(p.VECTOR2I(round(v[0][0]*1e6),round(v[0][1]*1e6)))]
  for v in nodes:adj[v].update(nodes)
 root=(r.xy(pad('J1','2')),p.F_Cu);todo=[root];seen=set()
 while todo:
  v=todo.pop()
  if v in seen:continue
  seen.add(v);todo.extend(adj[v]-seen)
 pp=[q for q in r.pads if q.GetNetCode()==ground and not q.GetParentFootprint().GetReference().startswith('C') and not any(q.HitTest(p.VECTOR2I(round(v[0][0]*1e6),round(v[0][1]*1e6))) for v in seen)]
 if not pp:print('All connector grounds have >=3mm paths',flush=True);break
 found=False
 for q in pp:
  for end,layer in sorted(seen,key=lambda v:r.math.dist(r.xy(q),v[0])):
   result=r.route(r.xy(q),end,ground,3,layer)
   if result:r.commit(result[0],ground,3,layer);print('Ground repaired',q.GetParentFootprint().GetReference(),flush=True);found=True;break
  if found:break
 if not found:print('UNRESOLVED ground connectors',[q.GetParentFootprint().GetReference() for q in pp],flush=True);break
p.SaveBoard(str(target),r.b)
