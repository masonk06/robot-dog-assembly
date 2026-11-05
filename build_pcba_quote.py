"""Build a revision-locked prototype fabrication + PCBA quotation package."""
from pathlib import Path
import csv, hashlib, json, shutil, subprocess, zipfile, sys
import pcbnew as p
ROOT=Path(__file__).parent;src=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'revision_four_leg'
one_oz=src.name=='revision_one_oz';tag='RevC_1oz' if one_oz else 'RevB'
out=src/('jlcpcb_pcba_revC_1oz' if one_oz else 'jlcpcb_pcba_revB');out.mkdir(exist_ok=True)
pcb=src/'Luca_power_distribution_four_leg.kicad_pcb';sch=pcb.with_suffix('.kicad_sch')
cli=Path(r'C:\Program Files\KiCad\10.0\bin\kicad-cli.exe')
def run(*args):subprocess.run([str(cli),*map(str,args)],check=True)
run('pcb','drc','--exit-code-violations','--schematic-parity','--output',src/'DRC.txt',pcb)
run('sch','erc','--exit-code-violations','--output',src/'ERC.txt',sch)
gerbers=out/'gerbers';drills=out/'drills';assembly=out/'assembly'
for d in (gerbers,drills,assembly):d.mkdir(exist_ok=True)
run('pcb','export','gerbers','--output',str(gerbers)+'/', '--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask','--check-zones',pcb)
run('pcb','export','drill','--output',str(drills)+'/', '--format','excellon','--drill-origin','absolute','--excellon-units','mm','--excellon-separate-th','--generate-report',pcb)
run('pcb','export','gerbers','--output',str(assembly/'paste')+'/', '--layers','F.Paste' if one_oz else 'F.Paste,B.Paste',pcb)
for side,layers in [('TOP','F.Fab,F.SilkS,Edge.Cuts'),('BOTTOM','B.Fab,B.SilkS,Edge.Cuts')]:
    args=['pcb','export','pdf','--output',assembly/('ASSEMBLY_'+side+'.pdf'),'--layers',layers,'--mode-single','--sketch-pads-on-fab-layers','--crossout-DNP-footprints-on-fab-layers','--black-and-white','--no-property-popups']
    if side=='BOTTOM':args.append('--mirror')
    run(*args,pcb)
run('pcb','export','pos','--output',assembly/'KiCad_ORIGINS_REFERENCE.csv','--format','csv','--units','mm','--exclude-dnp',pcb)
b=p.LoadBoard(str(pcb));fps={f.GetReference():f for f in b.GetFootprints()}
parts=json.loads((src/'pcba_parts.json').read_text());refs={ref for row in parts['parts'] for ref in row['refs']}
expected={ref for ref,f in fps.items() if not ref.startswith('H') and not f.IsDNP()}
assert refs==expected,(refs^expected)
def footprint(f):return str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())
def csvwrite(path,headers,rows):
    with path.open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.writer(stream);writer.writerow(headers);writer.writerows(rows)
bom=[];sourcing=[]
for row in parts['parts']:
    devices=row['refs'];names={footprint(fps[ref]) for ref in devices};assert len(names)==1
    bom.append([row['mpn'],','.join(devices),names.pop(),row['lcsc'],row['manufacturer'],row['mpn'],len(devices),row['comment']])
    sourcing.append([','.join(devices),row['mpn'],row['lcsc'],row['sourcing']])
csvwrite(assembly/'BOM_FULL_QUOTE.csv',['Comment','Designator','Footprint','LCSC Part #','Manufacturer','Manufacturer Part Number','Quantity','Description'],bom)
csvwrite(assembly/'SOURCING_STATUS.csv',['Designator','Manufacturer Part Number','LCSC Part #','Status'],sourcing)
csvwrite(assembly/'DNP.csv',['Designator','Instruction'],[(ref,'DO NOT POPULATE; independent Pi supply') for ref in parts['dnp']])
csvwrite(assembly/'EXTERNAL_PURCHASES.csv',['Item','Manufacturer','Manufacturer Part Number','Quantity','Notes'],[(r['item'],r['manufacturer'],r['mpn'],r['quantity'],r['notes']) for r in parts['external']])
# Centroids use physical fabrication outlines rather than pin-one footprint
# anchors. Mechanical drawings and original anchors accompany the CPL so JLC's
# engineer can verify its library-model origin/rotation, including bottom F5.
placements=[];mapping=[]
for ref in sorted(refs):
    f=fps[ref];shapes=[q for q in f.GraphicalItems() if isinstance(q,p.PCB_SHAPE) and q.GetLayer() in (p.F_Fab,p.B_Fab)]
    assert shapes,ref
    boxes=[q.GetBoundingBox() for q in shapes]
    x=(min(q.GetLeft() for q in boxes)+max(q.GetRight() for q in boxes))/2e6
    y=(min(q.GetTop() for q in boxes)+max(q.GetBottom() for q in boxes))/2e6
    angle=f.GetOrientationDegrees()%360;layer='Bottom' if f.GetLayer()==p.B_Cu else 'Top'
    # Same absolute KiCad origin and upward Y axis as native KiCad position
    # output. The same translation/axis transform is used for every component.
    placements.append([ref,f'{x:.4f}mm',f'{-y:.4f}mm',layer,f'{angle:.1f}'])
    mapping.append([ref,f'{f.GetPosition().x/1e6:.4f}',f'{-f.GetPosition().y/1e6:.4f}',f'{x:.4f}',f'{-y:.4f}',angle,layer])
csvwrite(assembly/'CPL_FULL_QUOTE.csv',['Designator','Mid X','Mid Y','Layer','Rotation'],placements)
csvwrite(assembly/'CENTROID_DATUM_REVIEW.csv',['Designator','KiCad origin X mm','KiCad origin Y up mm','Fab centroid X mm','Fab centroid Y up mm','KiCad CCW rotation','Layer'],mapping)
assert len(placements)==18
fabrication=[q for q in gerbers.iterdir() if q.suffix!='.gbrjob']+[q for q in drills.iterdir() if q.suffix=='.drl']
assert len(fabrication)==9,[q.name for q in fabrication]
with zipfile.ZipFile(out/('Luca_'+tag+'_FAB_PROTOTYPE.zip'),'w',zipfile.ZIP_DEFLATED) as z:
    for q in sorted(fabrication):z.write(q,q.name)
for name in ('DRC.txt','ERC.txt','topology-and-ground-audit.json','power-path-screen.json','pcba_parts.json','FUSE-AND-COPPER-REVIEW.md','OPERATING-CONTEXT.md','HARNESS-SELECTION.md'):
    shutil.copy2(src/name,out/name)
manifest={'release':('REV C - 1OZ' if one_oz else 'REV B')+' - VALIDATION PROTOTYPE / PCBA QUOTE ONLY','copper_oz_per_side':1 if one_oz else 2,'populated_sides':['Top'] if one_oz else ['Top','Bottom'],'pcb_sha256':hashlib.sha256(pcb.read_bytes()).hexdigest(),'schematic_sha256':hashlib.sha256(sch.read_bytes()).hexdigest(),'populated_components':18,'smd_components':7,'through_hole_components':11,'dnp':parts['dnp'],'CPL_status':'Centroids exported; JLC library-model placement/orientation review required before paid order','sourcing_status':'Exact Bel, Keystone and Phoenix parts require sourcing/consignment confirmation; no silent substitutions','fabrication_files':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in sorted(fabrication)}}
(out/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Built',out)
