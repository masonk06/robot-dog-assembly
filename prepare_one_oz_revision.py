"""Derive revision C from revision B, preserving circuit and mounting holes.

Replaces the long shared current routes with short, parallel two-face 6mm
conductors and ground pours. This is a prototype design, not thermal approval.
"""
from pathlib import Path
import hashlib, json, shutil
import pcbnew as p
ROOT=Path(__file__).parent;source=ROOT/'revision_four_leg';out=ROOT/'revision_one_oz'
if (out/'Luca_power_distribution_four_leg.kicad_pcb').exists():raise SystemExit('Revision C already exists; refusing to reset it')
out.mkdir(exist_ok=True)
for ext in ('kicad_pcb','kicad_sch','kicad_pro','kicad_dru'):
    shutil.copy2(source/('Luca_power_distribution_four_leg.'+ext),out)
for name in ('fp-lib-table','pcba_parts.json'):shutil.copy2(source/name,out)
shutil.copytree(source/'Luca_Review.pretty',out/'Luca_Review.pretty',dirs_exist_ok=True)
pcb=out/'Luca_power_distribution_four_leg.kicad_pcb';b=p.LoadBoard(str(pcb))
oldtracks=list(b.GetTracks());fps={f.GetReference():f for f in b.GetFootprints()}
def pos(x,y):return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
fps['F1'].SetPosition(pos(151,110))
fps['J3'].SetPosition(pos(161.5,95))
f=fps['F5']
if f.GetLayer()==p.B_Cu:f.Flip(f.GetPosition(),False)
f.SetOrientationDegrees(0);f.SetPosition(pos(130,78))
f.Reference().SetPosition(pos(130,75.3))
fps['F1'].Reference().SetPosition(pos(155.96,107.3))
fps['J3'].Reference().SetPosition(pos(165.31,89.2))
# The preserved Pi fuse is DNP; it must not receive stencil paste.
for q in fps['F7'].Pads():
    original=q.GetLayerSet();seq=original.Seq();layers=p.LSET()
    for layer in seq:
        if layer not in (p.F_Paste,p.B_Paste):layers.AddLayer(layer)
    q.SetLayerSet(layers)
def track(points,name,width,layer):
    net=b.FindNet(name)
    for a,c in zip(points,points[1:]):
        t=p.PCB_TRACK(b);t.SetStart(pos(*a));t.SetEnd(pos(*c));t.SetWidth(p.FromMM(width));t.SetLayer(layer);t.SetNet(net);b.Add(t)
def via(x,y,name,diameter=1.8,drill=1.):
    v=p.PCB_VIA(b);v.SetPosition(pos(x,y));v.SetWidth(p.FromMM(diameter));v.SetDrill(p.FromMM(drill));v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);v.SetNet(b.FindNet(name));b.Add(v)
for layer in (p.F_Cu,p.B_Cu):
    track([(157.9,122.25),(151,113.4),(151,110)],'/VBAT_RAW',6,layer)
    track([(160.92,113.4),(160.92,110),(161.5,95)],'/VBAT_FUSED',6,layer)
    track([(169.12,87.5),(169.12,95),(169.12,114.5)],'/SERVO_V+',6,layer)
for i,leg in enumerate(('FL','FR','RL','RR')):
    y=87.5+9*i;connector_y=86+9*i;name='/'+leg+'_V+'
    track([(169.12,y),(174.045,y)],'/SERVO_V+',6,p.F_Cu)
    track([(174.045,y),(175.545,y)],'/SERVO_V+',2.6,p.F_Cu)
    track([(180.455,y),(181.955,y)],name,2.6,p.F_Cu)
    track([(181.955,y),(182.5,connector_y+4.5),(191,connector_y+4.5)],name,5,p.F_Cu)
    track([(191,connector_y+4.5),(193,connector_y+4.5),(193,connector_y)],name,4,p.F_Cu)
    # Four parallel 1mm drill transitions per leg connection; both faces of
    # the shared trunk are fed directly from J3's through-hole terminal.
    for x in (168.12,170.12):
        for yy in (y-1,y+1):via(x,yy,'/SERVO_V+')
for x,y in [(120,80),(120,96),(120,111),(132,126),(150,126),(180,75),(180,80),(186,85.5),(186,94.5),(186,103.5),(186,112.5),(177,122),(186,122),(195,126)]:via(x,y,'GND',1.4,.6)
for layer in (p.F_Cu,p.B_Cu):
    z=p.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetZoneName('REV_C_1OZ_GROUND_'+p.LayerName(layer));z.SetLocalClearance(p.FromMM(.3));z.SetMinThickness(p.FromMM(.25));z.SetPadConnection(p.ZONE_CONNECTION_FULL);z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    outline=z.Outline();outline.NewOutline()
    for x,y in [(110.5,70.5),(198,70.5),(198,129.5),(110.5,129.5)]:outline.Append(p.FromMM(x),p.FromMM(y))
    b.Add(z)
for t in b.GetDrawings():
    if isinstance(t,p.PCB_TEXT) and 'LUCA PCBA REV B' in t.GetText():t.SetText('LUCA REV C - 1OZ PROTOTYPE')
# Remove the old routing only after all footprint/pad mutations, avoiding SWIG
# ownership side effects while iterating other board objects.
for t in oldtracks:b.Remove(t)
p.SaveBoard(str(pcb),b)
(out/'DERIVATION.json').write_text(json.dumps({'revision':'C - 1oz validation prototype','derived_from':'revision_four_leg revision B','source_pcb_sha256':hashlib.sha256((source/pcb.name).read_bytes()).hexdigest(),'moved_parts':{'F1':[151,110],'J3':[161.5,95],'F5':[130,78]},'copper_um':35,'populated_assembly_sides':['Top']},indent=2)+'\n')
print('Created',pcb)
