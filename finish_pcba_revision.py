import pcbnew as p
from pathlib import Path
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));footprints=list(b.GetFootprints());tracks=list(b.GetTracks())
j=next(f for f in footprints if f.GetReference()=='J1')
positions={q.GetNumber():q.GetPosition() for q in j.Pads() if q.GetNumber()}
j.SetPosition(p.VECTOR2I(p.FromMM(165.1),p.FromMM(122.25)))
for q in j.Pads():
    if not q.GetNumber():continue
    for t in tracks:
        if isinstance(t,p.PCB_VIA) or t.GetNetCode()!=q.GetNetCode():continue
        if t.GetStart()==positions[q.GetNumber()]:t.SetStart(q.GetPosition())
        if t.GetEnd()==positions[q.GetNumber()]:t.SetEnd(q.GetPosition())
for t in tracks:
    if isinstance(t,p.PCB_VIA):continue
    if t.GetNetname()=='GND' and t.GetLayer()==p.B_Cu and t.GetStart().y==p.FromMM(118.5) and t.GetEnd().y==p.FromMM(118.5):t.SetWidth(p.FromMM(3))
# The connector deliberately overhangs the lower board edge; the full body is
# shown on fabrication/assembly layers, with no off-board silkscreen.
for item in j.GraphicalItems():
    if item.GetLayer()==p.F_SilkS:item.SetLayer(p.F_Fab)
j.Reference().SetPosition(p.VECTOR2I(p.FromMM(163),p.FromMM(118)))
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(root/'Luca_Review.pretty'),j)
c=next(f for f in footprints if f.GetReference()=='C2');q=next(q for q in c.Pads() if q.GetNetname()=='GND')
v=p.PCB_VIA(b);v.SetPosition(q.GetPosition());v.SetWidth(p.FromMM(1.1));v.SetDrill(p.FromMM(.5));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(q.GetNet());b.Add(v)
for text in b.GetDrawings():
    if isinstance(text,p.PCB_TEXT) and 'ENGINEERING REV' in text.GetText():text.SetText('LUCA PCBA REV B - PROTOTYPE')
p.SaveBoard(str(target),b)
print('J1 edge clearance and C2 ground transition adjusted; DRC required')
