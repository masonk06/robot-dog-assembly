"""Add a same-net main-fuse-to-J3 connection only if substantially shorter.

Retains all original branches; does not bridge either side of J3 or F1.
Final DRC and topology audit are mandatory.
"""
import route_board as r
from pathlib import Path
import math
p=r.p;root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
r.b=p.LoadBoard(str(target));r.pads=list(r.b.GetPads());r.tracks=[];r.mask_cache.clear();r.margin=.25
r.xmax=198.5;r.nx=355
r.xx,r.yy=r.np.meshgrid(r.xmin+r.np.arange(r.nx)*r.step,r.ymin+r.np.arange(r.ny)*r.step,indexing='ij')
for t in r.b.GetTracks():
    via=isinstance(t,p.PCB_VIA)
    for layer in ((p.F_Cu,p.B_Cu) if via else (t.GetLayer(),)):
        r.tracks.append(((t.GetStart().x/1e6,t.GetStart().y/1e6),(t.GetEnd().x/1e6,t.GetEnd().y/1e6),t.GetNetCode(),t.GetWidth(layer)/1e6 if via else t.GetWidth()/1e6,layer))
def pad(ref,num):return next(q for q in r.pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
a=pad('F1','2');c=pad('J3','1');assert a.GetNetname()==c.GetNetname()=='/VBAT_FUSED'
choices=[]
for width in (3.,2.6):
    for layer in (p.F_Cu,p.B_Cu):
        result=r.route(r.xy(a),r.xy(c),a.GetNetCode(),width,layer)
        if result:
            pts=result[0];length=sum(math.dist(u,v) for u,v in zip(pts,pts[1:]))
            if length<60:choices.append((length/width,length,width,layer,pts))
if choices:
    _,length,width,layer,pts=min(choices)
    r.commit(pts,a.GetNetCode(),width,layer);p.SaveBoard(str(target),r.b)
    print('Added main-fuse-to-J3 same-net route:',round(length,2),'mm;',width,'mm width;',p.LayerName(layer))
else:
    # Reuse the checked multi-layer router's definitions without its completion
    # loop, so only this one authorized same-net connection is considered.
    env={'__file__':str(Path(__file__).parent/'route_layers.py')}
    source=(Path(__file__).parent/'route_layers.py').read_text()
    exec(compile(source.split('\ndef pad(',1)[0],env['__file__'],'exec'),env)
    route=env['route3'](r.xy(a),r.xy(c),a.GetNetCode(),3.)
    if route:
        length=sum(math.hypot(v[0]-u[0],v[1]-u[1])*r.step for u,v in zip(route,route[1:]))
        if length<70:
            env['commit'](route,r.xy(a),r.xy(c),a.GetNetCode(),3.)
            p.SaveBoard(str(target),r.b)
            print('Added two-layer main-fuse-to-J3 route:',round(length,2),'mm; 3mm with paired vias')
        else:print('Two-layer connection remains too long; PCB unchanged')
    else:print('No short connection fits existing copper; PCB unchanged')
