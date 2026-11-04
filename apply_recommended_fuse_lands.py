import pcbnew as p
from pathlib import Path
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target))
for f in b.GetFootprints():
 if f.GetReference() not in ('F2','F5','F7','F8','F9','F10','F11'):continue
 for q in f.Pads():q.SetShape(p.PAD_SHAPE_RECT);q.SetSize(p.VECTOR2I(p.FromMM(1.96),p.FromMM(3.15)))
 f.SetFPID(p.LIB_ID('Luca_Review','Bel_0680H_2410_Recommended'))
 if f.GetReference()=='F2':
  p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(root/'Luca_Review.pretty'),f)
p.SaveBoard(str(target),b)
