"""Derive a four-leg engineering revision from the existing routed board.
No manufacturing release or fuse approval is implied by this script.
"""
import sys, json, re, uuid, copy
from pathlib import Path
import pcbnew as p
ROOT=Path(__file__).parent
OUT=ROOT/'revision_four_leg'; OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'manufacturing/Luca_power_distribution_manufacturing.kicad_pcb'
SCHEM=Path(r'C:\Users\mmbec\Documents\self_balancing_robot\self_balancing_robot_v2\Luca\Luca_power_distribution\Luca_power_distribution.kicad_sch')
LIB=Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
b=p.LoadBoard(str(SOURCE)); original_ids={f.GetReference():f.m_Uuid.AsString() for f in b.GetFootprints()}
for edge in b.GetDrawings():
 if isinstance(edge,p.PCB_SHAPE) and edge.GetLayer()==p.Edge_Cuts and edge.GetShape()==p.SHAPE_T_RECT:
  end=edge.GetEnd();end.x=p.FromMM(198.5);edge.SetEnd(end)
def mm(x):return p.FromMM(x)
def pos(x,y):return p.VECTOR2I(mm(x),mm(y))
def net(name):
 n=b.FindNet(name)
 if not n:n=p.NETINFO_ITEM(b,name);b.Add(n)
 return n
def fuse(ref,x,y,n1,n2,value):
 old=next((f for f in b.GetFootprints() if f.GetReference()==ref),None)
 f=p.FOOTPRINT(b);f.SetReference(ref);f.SetValue(value);f.SetFPID(p.LIB_ID('Luca_Review','Bel_0680H_2410_Recommended'))
 if old:b.Remove(old)
 f.SetPosition(pos(x,y));f.SetAttributes(p.FP_SMD)
 # Bel 0680H February 2025, page 4: 1.96 x 3.15mm lands, 2.95mm gap.
 for num,dx,nn in [('1',-2.455,n1),('2',2.455,n2)]:
  q=p.PAD(f);q.SetNumber(num);q.SetAttribute(p.PAD_ATTRIB_SMD);q.SetShape(p.PAD_SHAPE_RECT)
  layers=p.LSET()
  for layer in (p.F_Cu,p.F_Paste,p.F_Mask):layers.AddLayer(layer)
  q.SetSize(pos(1.96,3.15));q.SetPosition(pos(x+dx,y));q.SetLayerSet(layers);q.SetNet(net(nn));f.Add(q)
 for layer,w,h in [(p.F_Fab,6.1,2.54),(p.F_CrtYd,8.2,4.0)]:
  s=p.PCB_SHAPE(f);s.SetShape(p.SHAPE_T_RECT);s.SetStart(pos(x-w/2,y-h/2));s.SetEnd(pos(x+w/2,y+h/2));s.SetLayer(layer);s.SetWidth(mm(.05 if layer==p.F_CrtYd else .1));f.Add(s)
 f.Reference().SetPosition(pos(x,y-2.7));f.Reference().SetTextSize(pos(.8,.8));f.Value().SetVisible(False);b.Add(f);f.thisown=False;return f
def label(text,x,y):
 t=p.PCB_TEXT(b);t.SetText(text);t.SetPosition(pos(x,y));t.SetTextSize(pos(.8,.8));t.SetTextThickness(mm(.12));t.SetLayer(p.F_SilkS);b.Add(t)
# Retain battery input, main fuse, switch loop and existing aux/Pi interfaces.
# Replacing the three bulky branch holders creates local room for the leg bank.
fuse('F2',143.5,86,'/SERVO_V+','/SERVO','5A_T_PROVISIONAL_ADAPTER')
f5=fuse('F5',140,110,'/SERVO_V+','Net-(J7-Pin_1)','5A_T_PROVISIONAL_AUX');f5.Flip(f5.GetPosition(),False)
f7=fuse('F7',140,124,'/VBAT_FUSED','Net-(J10-Pin_1)','5A_T_PROVISIONAL_PI');f7.Flip(f7.GetPosition(),False)
for i,leg in enumerate(('FL','FR','RL','RR')):
 y=86+i*9
 fuse('F'+str(8+i),178,y+1.5,'/SERVO_V+',f'/{leg}_V+','0680H5000-05_PROVISIONAL')
 f=p.FootprintLoad(str(LIB/'Connector_AMASS.pretty'),'AMASS_XT30UPB-M_1x02_P5.0mm_Vertical')
 f.SetReference('J'+str(12+i));f.SetValue('XT30UPB-M_'+leg);f.SetPosition(pos(188,y));f.SetFPID(p.LIB_ID('Connector_AMASS','AMASS_XT30UPB-M_1x02_P5.0mm_Vertical'))
 for q in f.Pads():q.SetNet(net(f'/{leg}_V+' if q.GetNumber()=='2' else 'GND'))
 f.Reference().SetPosition(pos(190.5,y-3.3));f.Value().SetVisible(False);b.Add(f);f.thisown=False
 label(leg+' GND   +',190.5,y+3.3)
for f in b.GetFootprints():
 if f.GetReference()=='F1':f.SetValue('MAIN_FUSE_TBD_NOT_5A')
# Preserve geometrical source and its outline; reroute only in derived revision.
for t in list(b.GetTracks()):b.Remove(t);t.thisown=True
label('ENGINEERING REV - FUSES TBD',144,128)
pcb=OUT/'Luca_power_distribution_four_leg.kicad_pcb'
p.SaveBoard(str(pcb),b)
print(pcb,flush=True)
sys.exit(0)

# Small S-expression reader preserves the original schematic root/library and
# reuses original symbol UUIDs wherever the same component remains on the PCB.
class Atom(str):pass
def parse(text):
 toks=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+|[()]',text);i=0
 def one():
  nonlocal i
  t=toks[i];i+=1
  if t=='(':
   a=[]
   while toks[i]!=')':a.append(one())
   i+=1;return a
  return json.loads(t) if t.startswith('"') else Atom(t)
 return one()
def dump(a,depth=0):
 if not isinstance(a,list):return str(a) if isinstance(a,Atom) else json.dumps(a,ensure_ascii=False)
 if not any(isinstance(x,list) for x in a):return '('+' '.join(dump(x) for x in a)+')'
 return '('+dump(a[0])+''.join(('\n'+'\t'*(depth+1) if isinstance(x,list) else ' ')+dump(x,depth+1) for x in a[1:])+')'
def child(a,k):return next((x for x in a if isinstance(x,list) and x and x[0]==k),None)
def children(a,k):return [x for x in a if isinstance(x,list) and x and x[0]==k]
def A(x):return Atom(str(x))
def uid():return str(uuid.uuid4())
sch=parse(SCHEM.read_text(encoding='utf-8'));rootid=child(sch,'uuid')[1]
oldsyms={child(s,'property')[2]:s for s in []}
for s in children(sch,'symbol'):
 ref=next(x[2] for x in children(s,'property') if x[1]=='Reference');oldsyms[ref]=s
libs=child(sch,'lib_symbols')
needed={'Device:Fuse','Device:C','Device:C_Polarized','Connector_Generic:Conn_01x02','Connector_Generic:Conn_01x04','Mechanical:MountingHole'}
for libid in needed:
 if any(s[1]==libid for s in children(libs,'symbol')):continue
 group,name=libid.split(':');lib=parse((LIB.parent/'symbols'/f'{group}.kicad_sym').read_text(encoding='utf-8'))
 s=copy.deepcopy(next(s for s in children(lib,'symbol') if s[1]==name));s[1]=libid;libs.append(s)
# Reconcile the saved obsolete four-leg/reverse-FET schematic to the authorized
# current PCB before adding four new legs. Existing root UUID is retained.
keep={'version','generator','generator_version','uuid','paper','lib_symbols','embedded_fonts'}
sch=[x for x in sch if not isinstance(x,list) or x[0] in keep]
fonts=[A('effects'),[A('font'),[A('size'),A(1.27),A(1.27)]]]
def prop(name,val,x,y,hide=False):
 a=[A('property'),name,val,[A('at'),A(x),A(y),A(0)],copy.deepcopy(fonts)]
 if hide:a[-1].append([A('hide'),A('yes')])
 return a
for i,f in enumerate(sorted([f for f in b.GetFootprints() if f.GetReference()=='REF**'],key=lambda f:(f.GetPosition().x,f.GetPosition().y))):f.SetReference('H'+str(i+1))
footprints=sorted(list(b.GetFootprints()),key=lambda f:(f.GetReference()[0],int(re.search(r'\d+',f.GetReference())[0])))
records=[]
for index,f in enumerate(footprints):
 ref=f.GetReference();value=f.GetValue();count=len([q for q in f.Pads() if q.GetNumber()]);libid='Mechanical:MountingHole' if ref.startswith('H') else 'Device:Fuse' if ref.startswith('F') else ('Device:C_Polarized' if ref=='C1' else 'Device:C') if ref.startswith('C') else 'Connector_Generic:Conn_01x04' if count==4 else 'Connector_Generic:Conn_01x02'
 # Grid of explicit labeled components: all net names are visible and unique.
 x=35.56+(index%5)*50.8;y=30.48+(index//5)*31.75
 sid=child(oldsyms[ref],'uuid')[1] if ref in oldsyms else uid()
 fpid=str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())
 sym=[A('symbol'),[A('lib_id'),libid],[A('at'),A(x),A(y),A(0)],[A('unit'),A(1)],[A('in_bom'),A('yes')],[A('on_board'),A('yes')],[A('dnp'),A('yes' if f.IsDNP() else 'no')],[A('uuid'),sid],prop('Reference',ref,x+4,y-6),prop('Value',value,x+4,y-3),prop('Footprint',fpid,x,y,True),prop('Datasheet','',x,y,True)]
 if ref.startswith('H'):child(sym,'in_bom')[1]=A('no')
 if f.HasField('Description'):sym.append(prop('Description',f.GetFieldText('Description'),x,y,True))
 pins=[]
 def walk(a):
  if not isinstance(a,list):return
  if a and a[0]=='pin':pins.append(a)
  else:
   for t in a:walk(t)
 definition=next(s for s in children(libs,'symbol') if s[1]==libid);walk(definition)
 npins={q.GetNumber():q.GetNetname() for q in f.Pads() if q.GetNumber()}
 for pin in pins:
  number=child(pin,'number')[1];at=child(pin,'at');px=x+float(at[1]);py=y-float(at[2]);nn=npins[number]
  kind='label' if nn.startswith('/') else 'global_label'
  lab=[A(kind),nn[1:] if nn.startswith('/') else nn,[A('at'),A(px),A(py),A(0)],copy.deepcopy(fonts),[A('uuid'),uid()]]
  if kind=='global_label':lab.insert(2,[A('shape'),A('input')])
  sch.append(lab)
  sym.append([A('pin'),number,[A('uuid'),uid()]])
 sym.append([A('instances'),[A('project'),'Luca_power_distribution_four_leg',[A('path'),'/'+rootid,[A('reference'),ref],[A('unit'),A(1)]]]])
 path=p.KIID_PATH();path.push_back(p.KIID(rootid));path.push_back(p.KIID(sid))
 sch.append(sym);f.SetPath(path);records.append({'ref':ref,'value':value,'pins':npins,'footprint':fpid,'dnp':f.IsDNP()})
sch.append([A('text'),'REV B - VALIDATION PROTOTYPE / PCBA QUOTE\nJ3 = SERIES SWITCH LOOP; J12-J15 = 5A LEG POWER\nF2/F5 = 1A. F7/J10/J11 DNP. Adapter V+ must not join leg positives.',[A('at'),A(145),A(193),A(0)],copy.deepcopy(fonts),[A('uuid'),uid()]])
(OUT/'Luca_power_distribution_four_leg.kicad_sch').write_text(dump(sch)+'\n',encoding='utf-8')
p.SaveBoard(str(pcb),b)
(OUT/'pin_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(pcb,flush=True)
