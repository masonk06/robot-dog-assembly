"""Independent topology and wide-return checks for the derived PCB revision."""
import pcbnew as p, json, hashlib
from pathlib import Path
from collections import defaultdict
root=Path(__file__).parent/'revision_four_leg'
target=root/'Luca_power_distribution_four_leg.kicad_pcb'
b=p.LoadBoard(str(target));pads=list(b.GetPads())
def pad(ref,num):return next(q for q in pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()==num)
checks={}
checks['J3_series_loop']=pad('J3','1').GetNetname()=='/VBAT_FUSED' and pad('J3','2').GetNetname()=='/SERVO_V+'
checks['J3_upgraded_7_62mm_pitch']=abs((pad('J3','2').GetPosition().x-pad('J3','1').GetPosition().x)/1e6-7.62)<1e-6
checks['J3_manufacturer_1_3mm_drills']=all(pad('J3',k).GetDrillSize().x==p.FromMM(1.3) for k in ('1','2'))
checks['all_THT_mask_openings']=all(q.IsOnLayer(p.F_Mask) and q.IsOnLayer(p.B_Mask) for q in pads if q.GetAttribute()==p.PAD_ATTRIB_PTH)
for i,leg in enumerate(('FL','FR','RL','RR')):
 j='J'+str(12+i);f='F'+str(8+i);name='/'+leg+'_V+'
 members=sorted((q.GetParentFootprint().GetReference(),q.GetNumber()) for q in pads if q.GetNetname()==name)
 checks[leg+'_isolated_fused_positive']=members==sorted([(f,'2'),(j,'2')]) and pad(f,'1').GetNetname()=='/SERVO_V+' and pad(j,'1').GetNetname()=='GND'
 checks[leg+'_connector_polarity']=pad(j,'1').GetPosition().x<pad(j,'2').GetPosition().x and pad(j,'1').GetNetname()=='GND'
 checks[leg+'_recommended_fuse_lands']=all(abs(pad(f,k).GetSize().x/1e6-1.96)<1e-6 and abs(pad(f,k).GetSize().y/1e6-3.15)<1e-6 for k in ('1','2'))
 checks[leg+'_power_tracks_min_3mm']=all(not isinstance(t,p.PCB_VIA) and t.GetWidth()>=p.FromMM(3) for t in b.GetTracks() if t.GetNetname()==name)
checks['adapter_supply_separate']=sorted((q.GetParentFootprint().GetReference(),q.GetNumber()) for q in pads if q.GetNetname()=='/SERVO')==[('F2','2'),('J2','1')]
holes={(round(q.GetPosition().x/1e6,4),round(q.GetPosition().y/1e6,4)) for q in pads if q.GetParentFootprint().GetReference().startswith('H')}
checks['original_mounting_holes_preserved']=holes=={(113.5,74),(113.5,126),(175,73.5),(175,126.5)}
edges=[s for s in b.GetDrawings() if isinstance(s,p.PCB_SHAPE) and s.GetLayer()==p.Edge_Cuts]
checks['approved_outline_88_5_by_60']=len(edges)==1 and abs((edges[0].GetEnd().x-edges[0].GetStart().x)/1e6-88.5)<1e-6 and abs((edges[0].GetEnd().y-edges[0].GetStart().y)/1e6-60)<1e-6
adj=defaultdict(set)
for t in b.GetTracks():
 if t.GetNetname()!='GND':continue
 if isinstance(t,p.PCB_VIA):
  v=t.GetPosition();a=(v.x,v.y,p.F_Cu);c=(v.x,v.y,p.B_Cu)
 elif t.GetWidth()<p.FromMM(2.6):continue
 else:
  a=(t.GetStart().x,t.GetStart().y,t.GetLayer());c=(t.GetEnd().x,t.GetEnd().y,t.GetLayer())
 adj[a].add(c);adj[c].add(a)
for q in pads:
 if q.GetNetname()!='GND':continue
 nodes=[v for v in adj if q.IsOnLayer(v[2]) and q.HitTest(p.VECTOR2I(v[0],v[1]))]
 for v in nodes:adj[v].update(nodes)
q=pad('J1','2');roots=[v for v in adj if q.HitTest(p.VECTOR2I(v[0],v[1]))];todo=roots[:];seen=set()
while todo:
 v=todo.pop()
 if v in seen:continue
 seen.add(v);todo.extend(adj[v]-seen)
ground_results={}
for q in pads:
 ref=q.GetParentFootprint().GetReference()
 if not ref.startswith('J') or q.GetNetname()!='GND':continue
 ground_results[ref+'.'+q.GetNumber()]=any(q.IsOnLayer(v[2]) and q.HitTest(p.VECTOR2I(v[0],v[1])) for v in seen)
checks['all_connector_returns_without_thin_traces']=bool(ground_results) and all(ground_results.values())
result={'status':'ENGINEERING REVIEW - FABRICATION HOLD','checks':checks,'ground_returns_min_track_mm':2.6,'ground_results':ground_results,'pcb_sha256':hashlib.sha256(target.read_bytes()).hexdigest()}
(root/'topology-and-ground-audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
if not all(checks.values()):raise SystemExit(1)
