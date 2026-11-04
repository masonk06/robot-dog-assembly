import route_board as r
from pathlib import Path
p=r.p
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
r.b=p.LoadBoard(str(target));r.pads=list(r.b.GetPads());r.tracks=[];r.mask_cache.clear();r.margin=.45
r.xmax=198.5;r.nx=355
r.xx,r.yy=r.np.meshgrid(r.xmin+r.np.arange(r.nx)*r.step,r.ymin+r.np.arange(r.ny)*r.step,indexing='ij')
for t in list(r.b.GetTracks()):r.b.Remove(t)
legs=[r.b.FindNet('/'+leg+'_V+').GetNetCode() for leg in ('FL','FR','RL','RR')]
names=['/VBAT_RAW','/VBAT_FUSED','/SERVO','/SERVO_V+','Net-(J7-Pin_1)','Net-(J10-Pin_1)','Net-(J5-Pin_1)','Net-(J10-Pin_3)','GND']
codes={name:r.b.FindNet(name).GetNetCode() for name in names}
order=legs+[codes[name] for name in names]
wide=legs+[codes[name] for name in ['/VBAT_RAW','/VBAT_FUSED','/SERVO','/SERVO_V+','GND']]
missing=[]
for n in order:
 pp=[q for q in r.pads if q.GetNetCode()==n]
 if not pp:continue
 pp.sort(key=lambda q:(q.GetAttribute()==p.PAD_ATTRIB_SMD,q.GetParentFootprint().GetReference().startswith('C')))
 name=r.b.FindNet(n).GetNetname()
 if name in ('/SERVO_V+','/VBAT_FUSED'):pp.sort(key=lambda q:q.GetParentFootprint().GetReference()!='J3')
 if name in ('/VBAT_RAW','GND'):pp.sort(key=lambda q:q.GetParentFootprint().GetReference()!='J1')
 connected=[pp.pop(0)]
 while pp:
  choices=sorted((r.math.dist(r.xy(a),r.xy(c))+(500 if c.GetParentFootprint().GetReference()=='C2' else 0),i,j) for i,a in enumerate(connected) for j,c in enumerate(pp) if a.GetParentFootprint().GetReference()!='C2')
  found=None
  for _,i,j in choices:
   a,c=connected[i],pp[j];w=3 if n in wide else 1
   # Keep wide supply trunks off B.Cu. Bottom SMD input pads receive a local
   # via transition in the second routing stage instead of a long B.Cu trunk.
   if n in wide and name!='GND' and any(q.GetAttribute()==p.PAD_ATTRIB_SMD and q.IsOnLayer(p.B_Cu) for q in (a,c)):continue
   if a.GetParentFootprint().GetReference()=='C2' or c.GetParentFootprint().GetReference()=='C2':w=.5
   candidate_layers=(p.B_Cu,p.F_Cu) if name=='GND' else (p.F_Cu,)
   if a.GetAttribute()==p.PAD_ATTRIB_SMD and a.IsOnLayer(p.B_Cu) or c.GetAttribute()==p.PAD_ATTRIB_SMD and c.IsOnLayer(p.B_Cu):candidate_layers=(p.B_Cu,)
   for layer in candidate_layers:
    if not a.IsOnLayer(layer) or not c.IsOnLayer(layer):continue
    result=r.route(r.xy(a),r.xy(c),n,w,layer)
    if result:found=(result[0],w,layer,j);break
   if found:break
  if not found:
   missing.append((n,[(q.GetParentFootprint().GetReference(),q.GetNumber()) for q in pp]));break
  pts,w,layer,j=found;r.commit(pts,n,w,layer);connected.append(pp.pop(j));print('routed',n,w,layer,flush=True)
p.SaveBoard(str(target),r.b)
print('UNFINISHED',missing,flush=True)
