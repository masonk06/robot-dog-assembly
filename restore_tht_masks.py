"""Restore THT solder-mask openings after a SWIG shared-constant side effect."""
from pathlib import Path
import pcbnew as p
root=Path(__file__).parent/'revision_four_leg'
target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target))
for q in b.GetPads():
    if q.GetAttribute() not in (p.PAD_ATTRIB_PTH,p.PAD_ATTRIB_NPTH):continue
    q.SetLayerSet(p.PAD.PTHMask() if q.GetAttribute()==p.PAD_ATTRIB_PTH else p.PAD.UnplatedHoleMask())
f=next(f for f in b.GetFootprints() if f.GetReference()=='J3')
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(root/'Luca_Review.pretty'),f)
p.SaveBoard(str(target),b)
print('THT masks restored using independent layer-set instances')
