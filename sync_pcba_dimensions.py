"""Apply the AMASS 2025V0 drawing supplied for LCSC C98732."""
import pcbnew as p
from pathlib import Path
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));j=next(f for f in b.GetFootprints() if f.GetReference()=='J1')
for q in j.Pads():
    if q.GetNumber():
        q.SetDrillSize(p.VECTOR2I(p.FromMM(2.9),p.FromMM(2.9)));q.SetSize(p.VECTOR2I(p.FromMM(4.4),p.FromMM(4.4)))
    else:
        q.SetDrillSize(p.VECTOR2I(p.FromMM(.8),p.FromMM(1.9)));q.SetSize(p.VECTOR2I(p.FromMM(1.4),p.FromMM(2.5)))
j.SetLibDescription('AMASS XT60PW-M; C98732 2025V0 drawing model XT60PW-M30.G.Y.T; 2.9mm holes; 0.8x1.9mm slots; reinforced annular rings. Pad1 negative, pad2 positive.')
for t in b.GetTracks():
    if isinstance(t,p.PCB_VIA):continue
    if t.GetNetname()=='GND' and t.GetLayer()==p.B_Cu and t.GetStart().y==p.FromMM(118.5) and t.GetEnd().y==p.FromMM(118.5):t.SetWidth(p.FromMM(2.6))
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(root/'Luca_Review.pretty'),j)
p.SaveBoard(str(target),b)
print('J1 drawing dimensions synchronized')
