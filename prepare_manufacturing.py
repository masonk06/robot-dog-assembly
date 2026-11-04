import route_board as r
from pathlib import Path
p=r.p
r.b=p.LoadBoard(str(r.OUT)); r.pads=list(r.b.GetPads())
r.margin=.35
r.tracks=[((t.GetStart().x/1e6,t.GetStart().y/1e6),(t.GetEnd().x/1e6,t.GetEnd().y/1e6),t.GetNetCode(),t.GetWidth()/1e6,t.GetLayer()) for t in r.b.GetTracks()]
start=next(r.xy(q) for q in r.pads if q.GetParentFootprint().GetReference()=='J2' and q.GetNumber()=='2')
candidates=set(pt for a,c,n,w,l in r.tracks if n==2 and w>=3 for pt in (a,c))
found=False
for end in sorted(candidates,key=lambda x:r.math.dist(start,x)):
 for layer in (p.F_Cu,p.B_Cu):
  # Only attach to a same-layer trace endpoint, or a plated ground pad.
  valid=any(n==2 and l==layer and end in (a,c) for a,c,n,w,l in r.tracks) or any(q.GetNetCode()==2 and r.xy(q)==end for q in r.pads)
  if not valid:continue
  result=r.route(start,end,2,3,layer)
  if result and valid:
   r.commit(result[0],2,3,layer); print('Added 3mm J2 ground:',result[0],layer,flush=True); found=True;break
 if found:break
if not found:raise RuntimeError('No wide ground route')
# Hide unassigned mounting-hole reference placeholders, including edge-clipped text.
for f in r.b.GetFootprints():
 if f.GetReference()=='REF**':f.Reference().SetVisible(False)
out=Path(r'C:\Users\mmbec\Downloads\Robot Dog Assembly\manufacturing')
out.mkdir(exist_ok=True)
target=out/'Luca_power_distribution_manufacturing.kicad_pcb'
p.SaveBoard(str(target),r.b)
print(target)
