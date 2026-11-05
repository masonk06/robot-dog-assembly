from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).parent;target=ROOT/'revision_one_oz/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));tracks=list(b.GetTracks())
for t in tracks:
    if t.GetNetname()=='Net-(J10-Pin_3)':b.Remove(t)
p.SaveBoard(str(target),b)
env={'__file__':str(ROOT/'route_layers.py')}
source=(ROOT/'route_layers.py').read_text().split('\ndef pad(',1)[0].replace('revision_four_leg/','revision_one_oz/')
exec(compile(source,env['__file__'],'exec'),env);r=env['r']
def pad(ref,num):return next(q for q in r.pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
a=pad('J11','1');c=pad('J10','3')
path=env['route3'](r.xy(a),r.xy(c),a.GetNetCode(),.5)
assert path
env['commit'](path,r.xy(a),r.xy(c),a.GetNetCode(),.5)
p.SaveBoard(str(target),r.b)
