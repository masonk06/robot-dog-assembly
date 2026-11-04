import pcbnew as p
from pathlib import Path
target=Path(__file__).parent/'revision_four_leg/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target))
f=next(f for f in b.GetFootprints() if f.GetReference()=='J2')
f.Reference().SetPosition(p.VECTOR2I(p.FromMM(115.5),p.FromMM(91)))
tracks=list(b.GetTracks())
for t in tracks:
    if t.GetNetname()=='/SERVO':b.Remove(t)
p.SaveBoard(str(target),b)
