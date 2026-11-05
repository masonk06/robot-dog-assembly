"""Widen existing main tracks where conservative geometric clearance allows.

Uses enclosing pad circles and capsule distances; final KiCad DRC is required.
Does not change routes, net topology, layer transitions, or individual leg fuses.
"""
from pathlib import Path
import math
import pcbnew as p
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));tracks=list(b.GetTracks());pads=list(b.GetPads())
def xy(v):return v.x/1e6,v.y/1e6
def pointseg(q,a,c):
    dx=c[0]-a[0];dy=c[1]-a[1];den=dx*dx+dy*dy
    t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/(den or 1)))
    return math.hypot(q[0]-a[0]-t*dx,q[1]-a[1]-t*dy)
def cross(a,c,q):return (c[0]-a[0])*(q[1]-a[1])-(c[1]-a[1])*(q[0]-a[0])
def segdist(a,c,d,e):
    if cross(a,c,d)*cross(a,c,e)<0 and cross(d,e,a)*cross(d,e,c)<0:return 0
    return min(pointseg(a,d,e),pointseg(c,d,e),pointseg(d,a,c),pointseg(e,a,c))
obstacles=[]
for t in tracks:
    via=isinstance(t,p.PCB_VIA)
    obstacles.append((t,xy(t.GetStart()),xy(t.GetEnd()),(p.F_Cu,p.B_Cu) if via else (t.GetLayer(),),via))
changed={}
for t in tracks:
    name=t.GetNetname()
    if isinstance(t,p.PCB_VIA) or name not in ('/VBAT_RAW','/VBAT_FUSED','/SERVO_V+','GND') or t.GetWidth()<p.FromMM(2.6):continue
    a=xy(t.GetStart());c=xy(t.GetEnd());layer=t.GetLayer();limit=5.
    for other,d,e,layers,via in obstacles:
        if layer not in layers or other.GetNetCode()==t.GetNetCode():continue
        ow=other.GetWidth(layer)/1e6 if via else other.GetWidth()/1e6
        limit=min(limit,2*(segdist(a,c,d,e)-.3)-ow)
    for q in pads:
        if q.GetNetCode()==t.GetNetCode() or not q.IsOnLayer(layer):continue
        size=q.GetSize();radius=math.hypot(size.x/1e6,size.y/1e6)/2
        limit=min(limit,2*(pointseg(xy(q.GetPosition()),a,c)-radius-.3))
    limit=min(limit,2*(min(a[0]-110,c[0]-110,198.5-a[0],198.5-c[0],a[1]-70,c[1]-70,130-a[1],130-c[1])-.5))
    old=t.GetWidth()/1e6
    choice=max([old]+[w for w in (3.,4.,5.) if w<=limit-1e-6])
    if choice>old:
        t.SetWidth(p.FromMM(choice));key=name+' -> '+str(choice)+'mm';changed[key]=changed.get(key,0)+1
p.SaveBoard(str(target),b);print(changed)
