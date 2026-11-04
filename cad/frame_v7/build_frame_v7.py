"""V6 chassis plus detachable Camera Module 3 Wide mast. Units: mm."""
import sys, json, shutil, zipfile
from pathlib import Path
CAD = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CAD/'frame_v6'))
import build_frame_v6 as v6
b = v6.b
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.gp import gp_Ax2, gp_Pnt, gp_Dir
OUT = Path(__file__).resolve().parent
v6.OUT = OUT

def xcyl(x,y,z,r,length):
    return BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(x,y,z),gp_Dir(1,0,0)),r,length).Shape()

def main():
    parts = {n:b.load(CAD/'frame_v6'/f'{n}.step') for n in
             ('Frame_V6','Pi5_Electronics_Deck','Power_Distribution_Sled','Waveshare_Sled')}
    parts['Frame_V7'] = parts.pop('Frame_V6')
    for y in (-12,12):
        parts['Pi5_Electronics_Deck'] = b.cut(parts['Pi5_Electronics_Deck'],b.cyl(-31,y,36,1.7,5))
    # Flat rear face lets the detachable mast print lying on its back.
    mast = b.fuse(b.box(-46,-16,40,18,32,3), b.box(-43,-15,42.8,3,30,52.2))
    # Central opening exposes the rear connector and avoids trapping the FPC.
    mast = b.cut(mast,b.box(-44,-7,62,5,14,30))
    # Adjustable slots: 21 mm horizontal pitch; accept 12.5 mm vertical
    # camera hole pitch in either PCB orientation. Use M2 washers and spacers.
    for y in (-10.5,10.5):
        slot=b.fuse(b.box(-44,y-1.1,70,5,2.2,19),xcyl(-44,y,70,1.1,5))
        slot=b.fuse(slot,xcyl(-44,y,89,1.1,5))
        mast=b.cut(mast,slot)
    for y in (-12,12):
        mast=b.cut(mast,b.cyl(-31,y,39,1.7,5))
    parts['Camera_Mast']=mast
    refs={
        'Pi5_and_Cooler_REFERENCE':b.box(-27.5,-36,46,85,56,28),
        'Battery_75x34x25_REFERENCE':b.box(-22.5,-17,5.8,75,34,25),
        'Waveshare_42x33_REFERENCE':b.box(-6,25,13,42,33,17),
        'Regulator_RESERVED':b.box(-21,29,44,50,28,20),
        'Camera3_Wide_ENVELOPE':b.box(-59.4,-12.5,68,12.4,25,24),
    }
    b.COLORS.update({'Frame_V7':(.40,.49,.57),'Pi5_Electronics_Deck':(.15,.48,.53),
       'Power_Distribution_Sled':(.75,.42,.14),'Camera_Mast':(.85,.52,.18),
       'Pi5_and_Cooler_REFERENCE':(.18,.49,.25),'Regulator_RESERVED':(.37,.48,.76),
       'Camera3_Wide_ENVELOPE':(.2,.25,.22)})
    report={'baseline':'../frame_v6/validation.json','units':'mm','parts':{},'delta_intersections_mm3':{},
        'camera':'Raspberry Pi Camera Module 3 Wide (visible light)',
        'camera_mount':'Forward is -X; four M2 screws, 4 mm spacers and washers; adjustable vertical slots.',
        'limitations':['Camera is a conservative bounding envelope, not vendor detailed CAD.',
          'Static packaging checked; cable bends, lens view, vibration and full leg sweeps need physical verification.',
          'V6 unchanged geometry and checks inherited; generic power electronics reservations remain provisional.']}
    for name in ('Pi5_Electronics_Deck','Camera_Mast'):
        for other,shape in {**parts,**refs}.items():
            if other==name: continue
            volume=v6.overlap(parts[name],shape)
            report['delta_intersections_mm3'][name+' vs '+other]=round(volume,6)
            if volume>.01: raise RuntimeError((name,other,volume))
    print('Camera mast and deck: static packaging clear',flush=True)
    records=json.loads((CAD/'RoboDog_placements.json').read_text())['parts']
    case=b.load(CAD/'revision_sources'/'STS3215_case_fixed.step')
    for r in records:
        if '_servo_' in r['name']:
            vol=v6.overlap(mast,v6.placed(case,r['transform']))
            report['delta_intersections_mm3']['Camera_Mast vs '+r['name']]=round(vol,6)
            if vol>.01: raise RuntimeError((r['name'],vol))
    for name,shape in parts.items():
        report['parts'][name]=v6.export_part(name,shape)
        print('Exported '+name,flush=True)
    for suffix in ('step','stl'):
        shutil.copy2(CAD/'frame_v6'/f'Regulator_Spacer.{suffix}',OUT/f'Regulator_Spacer.{suffix}')
    v6.write_assembly(OUT/'RoboDog_V7_Complete.step',parts)
    v6.write_assembly(OUT/'RoboDog_V7_Equipment_Layout.step',{**parts,**refs})
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    b.render(OUT/'Frame_V7_layout.png',{**parts,**refs},'V7 | removable front camera mast', (35,-145))
    with zipfile.ZipFile(OUT/'RoboDog_V7_Print_Parts.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in [*OUT.glob('*.stl'),OUT/'README.md']:z.write(p,p.name)
    print('V7 complete',flush=True)

if __name__=='__main__':main()
