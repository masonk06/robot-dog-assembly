import pcbnew as p, math
from pathlib import Path
target=Path(__file__).parent/'revision_four_leg/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));vias=[]
for t in list(b.GetTracks()):
 if isinstance(t,p.PCB_VIA):
  pt=t.GetPosition()
  if any(math.hypot(pt.x-v.GetPosition().x,pt.y-v.GetPosition().y)<(t.GetDrillValue()+v.GetDrillValue())/2+p.FromMM(.26) for v in vias):b.Remove(t)
  else:vias.append(t)
 elif abs(t.GetLength()/1e6-math.hypot(.7,.7))<1e-5 and t.GetWidth()==p.FromMM(3):t.SetWidth(p.FromMM(1.2))
p.SaveBoard(str(target),b)
