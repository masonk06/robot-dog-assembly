"""Complete only low-current leaves around the new explicit power buses."""
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).parent;target=ROOT/'revision_one_oz/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));fps={f.GetReference():f for f in b.GetFootprints()}
def pos(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
fps['J7'].SetPosition(pos(133.84,103))
fps['C2'].SetPosition(pos(142.75,95))
fps['J10'].SetPosition(pos(127.5,118.6725));fps['J11'].SetPosition(pos(115,117.5))
for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA) and t.GetNetname()=='/SERVO_V+' and t.GetPosition().y==p.FromMM(95.5):t.SetPosition(pos(t.GetPosition().x/1e6,94))
f=fps['F7'];f.SetFPID(p.LIB_ID('Luca_Review','Bel_0680H_2410_DNP_NoPaste'))
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(target.parent/'Luca_Review.pretty'),f)
p.SaveBoard(str(target),b)
# Run router definitions in a fresh board instance; no default completion loop.
env={'__file__':str(ROOT/'route_layers.py')}
source=(ROOT/'route_layers.py').read_text().split('\ndef pad(',1)[0].replace('revision_four_leg/','revision_one_oz/')
exec(compile(source,env['__file__'],'exec'),env)
r=env['r'];b=r.b
def pad(ref,num):return next(q for q in r.pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
connections=[('C1','1','J3','2',2.),('F2','1','J3','2',1.),('F5','1','F2','1',1.),('C2','1','F2','1',.5),('F2','2','J2','1',1.),('F5','2','J7','1',1.),('J7','3','J5','1',1.),('F7','1','F1','2',.5),('F7','2','J10','1',.5),('J10','3','J11','1',.5)]
for ref,num,other,onum,width in connections:
    a=pad(ref,num);c=pad(other,onum);assert a.GetNetname()==c.GetNetname()
    path=env['route3'](r.xy(a),r.xy(c),a.GetNetCode(),width,tuple(l for l in (0,2) if a.IsOnLayer(l)),tuple(l for l in (0,2) if c.IsOnLayer(l)))
    if not path:raise RuntimeError(('No route',ref,other,width))
    env['commit'](path,r.xy(a),r.xy(c),a.GetNetCode(),width)
    print('Connected',ref,num,'to',other,onum,width,flush=True)
# Connect the small decoupler's ground to both pours without a long thin return.
q=pad('C2','2');v=p.PCB_VIA(b);v.SetPosition(q.GetPosition());v.SetWidth(p.FromMM(1.1));v.SetDrill(p.FromMM(.5));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(q.GetNet());b.Add(v)
p.SaveBoard(str(target),b)
print('Low-current connections complete')
