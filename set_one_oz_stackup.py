"""Record 35um copper on both faces in the native PCB stackup metadata."""
from pathlib import Path
root=Path(__file__).parent/'revision_one_oz';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
text=target.read_text()
if '\n\t\t(stackup\n' not in text:
    stack='''		(stackup
			(layer "F.SilkS" (type "Top Silk Screen"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen"))
			(copper_finish "HASL lead-free")
			(dielectric_constraints no)
		)
'''
    assert text.count('\t(setup\n')==1
    target.write_text(text.replace('\t(setup\n','\t(setup\n'+stack,1))
print('Native stackup: 35um / 1oz each side, nominal 1.6mm board')
