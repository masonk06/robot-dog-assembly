from pathlib import Path
import pcbnew as p
target=Path(__file__).parent/'revision_one_oz/Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));filler=p.ZONE_FILLER(b)
assert filler.Fill(b.Zones()),'Zone fill failed'
p.SaveBoard(str(target),b)
print('Filled ground zones')
