"""Independent net, bus, population, and broad ground-corridor checks."""
from pathlib import Path
import pcbnew as p, math, json, hashlib, re
from collections import deque
root=Path(__file__).parent/'revision_one_oz';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));pads=list(b.GetPads());fps={f.GetReference():f for f in b.GetFootprints()}
def pad(ref,num):return next(q for q in pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
checks={}
native=target.read_text()
checks['native_stackup_35um_both_faces']=all(re.search(r'\(layer "'+layer+r'"\s+\(type "copper"\)\s+\(thickness 0\.035\)',native) for layer in ('F.Cu','B.Cu'))
edges=[s for s in b.GetDrawings() if isinstance(s,p.PCB_SHAPE) and s.GetLayer()==p.Edge_Cuts]
checks['outline_88_5_by_60']=len(edges)==1 and abs((edges[0].GetEnd().x-edges[0].GetStart().x)/1e6-88.5)<1e-6 and abs((edges[0].GetEnd().y-edges[0].GetStart().y)/1e6-60)<1e-6
baseline=json.loads((root.parent/'revision_four_leg/pin_manifest.json').read_text())
checks['all_circuit_pin_nets_preserved']=all({q.GetNumber():q.GetNetname() for q in fps[r['ref']].Pads() if q.GetNumber()}==r['pins'] for r in baseline)
checks['J3_series_loop']=pad('J3','1').GetNetname()=='/VBAT_FUSED' and pad('J3','2').GetNetname()=='/SERVO_V+'
checks['battery_connector_polarity']=pad('J1','1').GetNetname()=='GND' and pad('J1','2').GetNetname()=='/VBAT_RAW'
checks['all_populated_parts_top']=all(f.GetLayer()==p.F_Cu for ref,f in fps.items() if not ref.startswith('H') and not f.IsDNP())
checks['Pi_parts_DNP']=all(fps[r].IsDNP() for r in ('F7','J10','J11'))
for i,leg in enumerate(('FL','FR','RL','RR')):
    f='F'+str(8+i);j='J'+str(12+i);name='/'+leg+'_V+'
    checks[leg+'_separately_fused']=sorted((q.GetParentFootprint().GetReference(),q.GetNumber()) for q in pads if q.GetNetname()==name)==[(f,'2'),(j,'2')]
    checks[leg+'_5A_fuse']=fps[f].GetValue()=='5A_T_0680H5000-05'
    traces=[t for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()==name]
    checks[leg+'_wide_output_with_short_escape']=bool(traces) and all(t.GetWidth()>=p.FromMM(4) or (t.GetWidth()>=p.FromMM(2.6) and t.GetLength()<=p.FromMM(1.51)) for t in traces)
for name in ('/VBAT_RAW','/VBAT_FUSED'):
    faces={}
    for layer in (p.F_Cu,p.B_Cu):
        faces[layer]={tuple(sorted(((t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)))) for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()==name and t.GetLayer()==layer and t.GetWidth()>=p.FromMM(6)}
    checks[name+'_duplicated_6mm_bus']=bool(faces[p.F_Cu]) and faces[p.F_Cu]==faces[p.B_Cu]
stitches=[t for t in b.GetTracks() if isinstance(t,p.PCB_VIA) and t.GetNetname()=='/SERVO_V+' and t.GetDrillValue()>=p.FromMM(1)]
checks['16_large_servo_trunk_stitches']=len(stitches)==16
trunk={layer:{tuple(sorted(((t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)))) for t in b.GetTracks() if not isinstance(t,p.PCB_VIA) and t.GetNetname()=='/SERVO_V+' and t.GetLayer()==layer and t.GetWidth()>=p.FromMM(6) and t.GetStart().x==p.FromMM(169.12) and t.GetEnd().x==p.FromMM(169.12)} for layer in (p.F_Cu,p.B_Cu)}
checks['servo_trunk_duplicated_6mm']=bool(trunk[p.F_Cu]) and trunk[p.F_Cu]==trunk[p.B_Cu]
holes={(round(q.GetPosition().x/1e6,4),round(q.GetPosition().y/1e6,4)) for q in pads if q.GetParentFootprint().GetReference().startswith('H')}
checks['original_mounting_holes_preserved']=holes=={(113.5,74),(113.5,126),(175,73.5),(175,126.5)}
zones=[z for z in b.Zones() if z.GetNetname()=='GND' and not z.GetIsRuleArea()]
checks['filled_ground_both_faces']=all(any(z.GetLayer()==layer and z.HasFilledPolysForLayer(layer) for z in zones) for layer in (p.F_Cu,p.B_Cu))
# A sampled 6mm-diameter clear ground corridor is screened on B.Cu between
# battery return and each leg. This checks broad geometry, not sheet-current
# distribution, pad annuli, plating, or temperature. Grid is 0.5mm; circle is
# sampled every 15 degrees. It is explicitly not a field solver.
zone=next(z for z in zones if z.GetLayer()==p.B_Cu)
offsets=[(0,0)]+[(3*math.cos(math.radians(a)),3*math.sin(math.radians(a))) for a in range(0,360,15)]
def clear(x,y):return all(zone.HitTestFilledArea(p.B_Cu,p.VECTOR2I(p.FromMM(x+dx),p.FromMM(y+dy))) for dx,dy in offsets)
free={(i,j) for i in range(66) for j in range(100) if clear(162+i*.5,79+j*.5)}
start=(round((165.1-162)/.5),round((122.25-79)/.5));seen=set();todo=deque([start])
while todo:
    u=todo.popleft()
    if u in seen or u not in free:continue
    seen.add(u)
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):todo.append((u[0]+dx,u[1]+dy))
returns={}
for ref in ('J12','J13','J14','J15'):
    q=pad(ref,'1');key=(round((q.GetPosition().x/1e6-162)/.5),round((q.GetPosition().y/1e6-79)/.5));returns[ref]=key in seen
checks['6mm_sampled_ground_corridor_to_each_leg']=all(returns.values())
result={'status':'REV C 1OZ VALIDATION PROTOTYPE / PCBA QUOTE','pcb_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'checks':checks,'ground_corridor_screen':{'grid_mm':.5,'sampled_diameter_mm':6,'circle_sample_degrees':15,'results':returns,'limitations':'Geometry sampling only; excludes holes/pad annuli, detailed sheet-current sharing, plating and thermal behavior.'}}
(root/'topology-and-ground-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
assert all(checks.values()),'One-ounce geometry/topology audit failed'
