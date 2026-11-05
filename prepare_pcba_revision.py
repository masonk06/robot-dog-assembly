"""Prepare the existing design for a prototype PCBA quote, not powered-use approval."""
from pathlib import Path
import shutil
import pcbnew as p
root=Path(__file__).parent/'revision_four_leg';target=root/'Luca_power_distribution_four_leg.kicad_pcb'
backup=root/'_history'/'before_pcba_quote';backup.mkdir(exist_ok=True)
for ext in ('kicad_pcb','kicad_sch'):
    src=root/('Luca_power_distribution_four_leg.'+ext)
    if not (backup/src.name).exists():shutil.copy2(src,backup/src.name)
b=p.LoadBoard(str(target));lib=Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
footprints=list(b.GetFootprints());tracks=list(b.GetTracks());removed=[]
def replace(ref,library,name,value,x,y,rotation,nets):
    old=next(f for f in footprints if f.GetReference()==ref)
    if str(old.GetFPID().GetLibItemName())==name:return old
    f=p.FootprintLoad(str(lib/(library+'.pretty')),name)
    f.SetReference(ref);f.SetValue(value);f.SetFPID(p.LIB_ID(library,name));f.SetPath(old.GetPath())
    f.SetOrientationDegrees(rotation);f.SetPosition(p.VECTOR2I(p.FromMM(x),p.FromMM(y)))
    for q in f.Pads():
        if q.GetNumber():q.SetNet(b.FindNet(nets[q.GetNumber()]))
    # Preserve physical positive/negative positions even where manufacturer pad
    # numbering changes. Mapping is by net, not by the obsolete pad number.
    for q in old.Pads():
        if not q.GetNumber():continue
        new=next(t for t in f.Pads() if t.GetNumber() and t.GetNetname()==q.GetNetname())
        for t in tracks:
            if isinstance(t,p.PCB_VIA) or t.GetNetCode()!=q.GetNetCode():continue
            if t.GetStart()==q.GetPosition():t.SetStart(new.GetPosition())
            if t.GetEnd()==q.GetPosition():t.SetEnd(new.GetPosition())
    f.Value().SetVisible(False);b.Add(f);f.thisown=False;removed.append(old);footprints.append(f)
    return f
# PCB-mount right-angle XT60: manufacturer/library pad 1 is negative, pad 2
# positive. Rotation keeps positive physically to the left, as before.
j=replace('J1','Connector_AMASS','AMASS_XT60PW-M_1x02_P7.20mm_Horizontal','XT60PW-M',165.1,122,180,{'1':'GND','2':'/VBAT_RAW'})
# Reinforcement tabs need the project's 0.254mm annular ring, not the stock
# footprint's 0.15mm. Main electrical pins retain the manufacturer's drill.
for q in j.Pads():
    if not q.GetNumber():q.SetSize(p.VECTOR2I(p.FromMM(1.2),p.FromMM(2.3)))
j.SetFPID(p.LIB_ID('Luca_Review','AMASS_XT60PW_M_ReinforcedTabs'))
j.Reference().SetPosition(p.VECTOR2I(p.FromMM(163),p.FromMM(118)))
p.PCB_IO_MGR.FindPlugin(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(root/'Luca_Review.pretty'),j)
replace('C2','Capacitor_SMD','C_0805_2012Metric','100nF_50V_X7R',142.75,95.5,0,{'1':'/SERVO_V+','2':'GND'})
values={'C1':'470uF_25V_UPW1E471MPD','F1':'20A_MAIN_0297020.WXNV','F2':'1A_T_0680H1000-05','F5':'1A_T_0680H1000-05','F7':'DNP_PI','J2':'1715721_ADAPTER','J5':'1715721_AUX_5V','J7':'1715747_AUX_BUCK'}
for f in footprints:
    if any(f is old for old in removed):continue
    ref=f.GetReference()
    if ref in values:f.SetValue(values[ref])
    if ref in ('F8','F9','F10','F11'):f.SetValue('5A_T_0680H5000-05')
    if ref in ('F7','J10','J11'):f.SetDNP(True);f.SetExcludedFromPosFiles(True)
for old in removed:b.Remove(old)
p.SaveBoard(str(target),b)
print('Prototype PCBA revision prepared; fresh parity/DRC required')
