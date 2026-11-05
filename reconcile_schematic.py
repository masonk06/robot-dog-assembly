"""Run reconciliation in a fresh KiCad Python process after board mutation."""
import pcbnew as p, json, re, uuid, copy, sys
from pathlib import Path
ROOT=Path(__file__).parent
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'revision_four_leg'
LIB=Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
SCHEM=Path(r'C:\Users\mmbec\Documents\self_balancing_robot\self_balancing_robot_v2\Luca\Luca_power_distribution\Luca_power_distribution.kicad_sch')
if (OUT/'Luca_power_distribution_four_leg.kicad_sch').exists():SCHEM=OUT/'Luca_power_distribution_four_leg.kicad_sch'
pcb=OUT/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(pcb))
source=(ROOT/'extend_four_leg.py').read_text(encoding='utf-8')
exec(compile(source.split('# Small S-expression reader',1)[1].split('\n',1)[1],str(ROOT/'extend_four_leg.py'),'exec'))
