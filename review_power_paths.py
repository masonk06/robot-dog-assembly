"""Reproducible centerline-path resistance screen; not a thermal simulation."""
import pcbnew as p, math, heapq, json, hashlib, sys
from pathlib import Path
from collections import defaultdict
root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).parent/'revision_four_leg'
one_oz=root.name=='revision_one_oz';copper_mm=.035 if one_oz else .070
target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));pads=list(b.GetPads())
def pad(ref,num):return next(q for q in pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
def node(v,l):return (v.x,v.y,l)
graphs={}
def graph(name):
    if name in graphs:return graphs[name]
    g=defaultdict(list)
    def edge(a,c,r,length,width):g[a].append((c,r,length,width));g[c].append((a,r,length,width))
    for t in b.GetTracks():
        if t.GetNetname()!=name:continue
        if isinstance(t,p.PCB_VIA):edge(node(t.GetPosition(),p.F_Cu),node(t.GetPosition(),p.B_Cu),0,0,None)
        else:
            length=t.GetLength()/1e6;width=t.GetWidth()/1e6
            edge(node(t.GetStart(),t.GetLayer()),node(t.GetEnd(),t.GetLayer()),.01724*length/(width*copper_mm),length,width)
    nodes=list(g)
    # Explicit new buses contain long segments with T-junctions at their
    # interiors; include these centerline junctions in the path model.
    for t in b.GetTracks():
        if t.GetNetname()!=name or isinstance(t,p.PCB_VIA):continue
        a=node(t.GetStart(),t.GetLayer());c=node(t.GetEnd(),t.GetLayer())
        dx=c[0]-a[0];dy=c[1]-a[1];den=dx*dx+dy*dy
        if not den:continue
        for v in nodes:
            if v[2]!=a[2] or v in (a,c):continue
            vx=v[0]-a[0];vy=v[1]-a[1];dot=vx*dx+vy*dy
            if vx*dy-vy*dx!=0 or not 0<dot<den:continue
            length=math.hypot(dx,dy)/1e6;width=t.GetWidth()/1e6;fraction=dot/den
            resistance=.01724*length/(width*copper_mm)
            edge(a,v,resistance*fraction,length*fraction,width)
            edge(v,c,resistance*(1-fraction),length*(1-fraction),width)
    for q in pads:
        if q.GetNetname()!=name:continue
        terminal=('pad',q.GetParentFootprint().GetReference(),q.GetNumber())
        for v in nodes:
            if q.IsOnLayer(v[2]) and q.HitTest(p.VECTOR2I(v[0],v[1])):edge(terminal,v,0,0,None)
    graphs[name]=g;return g
def path(ref1,num1,ref2,num2):
    a=pad(ref1,num1);c=pad(ref2,num2);assert a.GetNetname()==c.GetNetname()
    g=graph(a.GetNetname());start=('pad',ref1,num1);end=('pad',ref2,num2)
    distances={start:0};previous={};counter=0;todo=[(0,counter,start)]
    while todo:
        d,_,u=heapq.heappop(todo)
        if d!=distances[u]:continue
        if u==end:break
        for v,r,length,width in g[u]:
            if d+r<distances.get(v,math.inf):
                distances[v]=d+r;previous[v]=(u,length,width);counter+=1;heapq.heappush(todo,(d+r,counter,v))
    if end not in distances:return {'net':a.GetNetname(),'connected_in_centerline_model':False}
    u=end;length=0;widths=[]
    while u!=start:
        u,ll,ww=previous[u];length+=ll
        if ww is not None and ll>0:widths.append(ww)
    return {'net':a.GetNetname(),'from':ref1+'.'+num1,'to':ref2+'.'+num2,'track_length_mm':round(length,3),'minimum_track_width_mm':min(widths),'track_resistance_milliohm_20C':round(distances[end],3)}
paths=[path('J1','2','F1','1'),path('F1','2','J3','1')]
for i,leg in enumerate(('FL','FR','RL','RR')):
    f='F'+str(8+i);j='J'+str(12+i)
    requests=[('J3','2',f,'1'),(f,'2',j,'2')]
    if not one_oz:requests.append((j,'1','J1','1'))
    for args in requests:paths.append(dict(leg=leg,**path(*args)))
result={'pcb_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'copper_um':copper_mm*1000,'model':f'Shortest resistance along explicit track centerlines; {copper_mm:.3f}mm copper, 20C. Pad spreading, via barrels, solder, fuse, contacts and harness excluded. Parallel touching copper not merged except endpoints/pads. Ground-zone sheet resistance excluded. Screening only; not a current or temperature approval.','paths':paths}
(root/'power-path-screen.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
