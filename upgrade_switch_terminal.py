"""Upgrade only J3; retain its series-loop nets and existing routing."""
from pathlib import Path
import shutil
import pcbnew as p
root=Path(__file__).parent/'revision_four_leg'
pcb=root/'Luca_power_distribution_four_leg.kicad_pcb'
backup=root/'_history'/'before_J3_12AWG_upgrade'
backup.mkdir(exist_ok=True)
for ext in ('kicad_pcb','kicad_sch'):
    src=root/('Luca_power_distribution_four_leg.'+ext)
    if not (backup/src.name).exists():shutil.copy2(src,backup/src.name)
b=p.LoadBoard(str(pcb));old=next(f for f in b.GetFootprints() if f.GetReference()=='J3')
f=p.FOOTPRINT(b);f.SetReference('J3');f.SetValue('Phoenix_1868076_MKDS5_2_7.62')
f.SetFPID(p.LIB_ID('Luca_Review','Phoenix_MKDS5_2_7.62_1868076'))
f.SetLibDescription('Phoenix 1868076; 32A nominal, cULus 30A; flexible wire up to 4mm2; 12AWG switch loop; BOTH PINS POSITIVE')
f.SetPath(old.GetPath())
f.SetAttributes(p.FP_THROUGH_HOLE)
for num,x in (('1',0),('2',7.62)):
    q=p.PAD(f);q.SetNumber(num);q.SetAttribute(p.PAD_ATTRIB_PTH)
    q.SetShape(p.PAD_SHAPE_RECT if num=='1' else p.PAD_SHAPE_CIRCLE)
    q.SetSize(p.VECTOR2I(p.FromMM(3.4),p.FromMM(3.4)))
    q.SetDrillSize(p.VECTOR2I(p.FromMM(1.3),p.FromMM(1.3)))
    q.SetLayerSet(p.PAD.PTHMask())
    q.SetPosition(p.VECTOR2I(p.FromMM(x),0))
    q.SetNet(next(t for t in old.Pads() if t.GetNumber()==num).GetNet())
    f.Add(q)
def rect(layer,x1,y1,x2,y2,width):
    s=p.PCB_SHAPE(f);s.SetShape(p.SHAPE_T_RECT);s.SetLayer(layer)
    s.SetStart(p.VECTOR2I(p.FromMM(x1),p.FromMM(y1)))
    s.SetEnd(p.VECTOR2I(p.FromMM(x2),p.FromMM(y2)));s.SetWidth(p.FromMM(width));f.Add(s)
# Manufacturer side view: pin row is 4.6mm from rear, 7.9mm from wire-entry face.
rect(p.F_Fab,-3.81,-4.6,11.43,7.9,.1)
rect(p.F_SilkS,-3.91,-4.7,11.53,8,.12)
rect(p.F_CrtYd,-4.31,-5.1,11.93,8.4,.05)
f.Reference().SetPosition(p.VECTOR2I(p.FromMM(3.81),p.FromMM(-5.8)))
f.Reference().SetTextSize(p.VECTOR2I(p.FromMM(1),p.FromMM(1)))
f.Value().SetVisible(False)
lib=root/'Luca_Review.pretty'
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib),f)
f.SetPosition(p.VECTOR2I(p.FromMM(122.5),p.FromMM(76.5)))
for q in old.Pads():
    new=next(t for t in f.Pads() if t.GetNumber()==q.GetNumber())
    for t in list(b.GetTracks()):
        if isinstance(t,p.PCB_VIA) or t.GetNetCode()!=q.GetNetCode():continue
        if t.GetStart()==q.GetPosition():t.SetStart(new.GetPosition())
        if t.GetEnd()==q.GetPosition():t.SetEnd(new.GetPosition())
b.Remove(old);b.Add(f)
p.SaveBoard(str(pcb),b)
print('J3 upgraded; routing endpoints moved; DRC required')
