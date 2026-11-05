"""Validate quote-file consistency and bundle the revision without re-exporting CAD."""
from pathlib import Path
import csv, hashlib, json, shutil, zipfile
root=Path(__file__).parent/'revision_four_leg';out=root/'jlcpcb_pcba_revB'
manifest=json.loads((out/'RELEASE-MANIFEST.json').read_text())
pcb=root/'Luca_power_distribution_four_leg.kicad_pcb';sch=pcb.with_suffix('.kicad_sch')
assert hashlib.sha256(pcb.read_bytes()).hexdigest()==manifest['pcb_sha256']
assert hashlib.sha256(sch.read_bytes()).hexdigest()==manifest['schematic_sha256']
audit=json.loads((root/'topology-and-ground-audit.json').read_text())
assert audit['pcb_sha256']==manifest['pcb_sha256'] and all(audit['checks'].values())
parts=json.loads((root/'pcba_parts.json').read_text())
expected={ref for r in parts['parts'] for ref in r['refs']}
with (out/'assembly/CPL_FULL_QUOTE.csv').open(encoding='utf-8-sig') as stream:cpl=list(csv.DictReader(stream))
with (out/'assembly/BOM_FULL_QUOTE.csv').open(encoding='utf-8-sig') as stream:bom=list(csv.DictReader(stream))
assert len(cpl)==len(expected)==18
assert {r['Designator'] for r in cpl}==expected
assert {v for r in bom for v in r['Designator'].split(',')}==expected
assert not expected.intersection(parts['dnp'])
assert [r['Designator'] for r in cpl if r['Layer']=='Bottom']==['F5']
with zipfile.ZipFile(out/'Luca_RevB_FAB_PROTOTYPE.zip') as z:
    assert len(z.namelist())==9
    for name,digest in manifest['fabrication_files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
for name in ('DRC.txt','ERC.txt','topology-and-ground-audit.json','power-path-screen.json','pcba_parts.json','FUSE-AND-COPPER-REVIEW.md','OPERATING-CONTEXT.md','HARNESS-SELECTION.md','README.md'):
    shutil.copy2(root/name,out/name)
source=out/'source';source.mkdir(exist_ok=True)
for ext in ('kicad_pcb','kicad_sch','kicad_pro','kicad_dru'):shutil.copy2(root/('Luca_power_distribution_four_leg.'+ext),source)
shutil.copy2(root/'fp-lib-table',source)
shutil.copytree(root/'Luca_Review.pretty',source/'Luca_Review.pretty',dirs_exist_ok=True)
refs=out/'manufacturer_references';refs.mkdir(exist_ok=True)
for name in ('Bel_0680H.pdf','Phoenix_1868076_plan.jpg','AMASS_XT60PW-M.pdf','AMASS_XT60PW-M-drawing.png'):
    shutil.copy2(root/'manufacturer_references'/name,refs/name)
with (out/'assembly/EXTERNAL_PURCHASES.csv').open('w',newline='',encoding='utf-8-sig') as stream:
    writer=csv.writer(stream);writer.writerow(['Item','Manufacturer','Manufacturer Part Number','Quantity','Notes'])
    writer.writerows((r['item'],r['manufacturer'],r['mpn'],r['quantity'],r['notes']) for r in parts['external'])
manifest['package_validation']='Passed: source/audit hashes, 9 fabrication files, 18 BOM/CPL refs, F5-only bottom population, DNP exclusion'
(out/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
bundle=root/'Luca_PCBA_RevB_PROTOTYPE_QUOTE.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as z:
    for q in sorted(out.rglob('*')):
        if q.is_file():z.write(q,q.relative_to(out))
print('Validated and bundled:',bundle)
