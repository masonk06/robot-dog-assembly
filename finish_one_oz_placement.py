import pcbnew as p
from pathlib import Path
target=Path(__file__).parent/'revision_one_oz/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));tracks=list(b.GetTracks());fps={f.GetReference():f for f in b.GetFootprints()}
for ref,x,y in [('J11',115,116.5),('J7',133.84,102.5),('C2',142.75,94.25)]:
    f=fps[ref];positions={q.m_Uuid.AsString():q.GetPosition() for q in f.Pads()}
    f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
    for q in f.Pads():
        old=positions[q.m_Uuid.AsString()]
        for t in tracks:
            if t.GetNetCode()!=q.GetNetCode():continue
            if isinstance(t,p.PCB_VIA):
                if t.GetPosition()==old:t.SetPosition(q.GetPosition())
            else:
                if t.GetStart()==old:t.SetStart(q.GetPosition())
                if t.GetEnd()==old:t.SetEnd(q.GetPosition())
p.SaveBoard(str(target),b)
