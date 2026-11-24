"""Derive the onboard-converter prototype from the released Rev C project.

Run with KiCad 10's Python. Source release is read only. Local switching loops
are explicitly routed; the remaining distribution links are routed separately.
"""
from pathlib import Path
import copy
import json
import re
import shutil
import uuid
import pcbnew as p

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
SRC = ROOT / 'revision_one_oz'
NAME = 'Luca_power_distribution_four_leg'
LIB = Path(r'C:\Program Files\KiCad\10.0\share\kicad\footprints')
for ext in ('kicad_pro', 'kicad_sch'):
    shutil.copy2(SRC / f'{NAME}.{ext}', OUT / f'{NAME}.{ext}')
shutil.copytree(SRC / 'Luca_Review.pretty', OUT / 'Luca_Review.pretty', dirs_exist_ok=True)
shutil.copy2(SRC / 'fp-lib-table', OUT / 'fp-lib-table')
b = p.LoadBoard(str(SRC / f'{NAME}.kicad_pcb'))

def pt(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))

def net(name):
    found = b.FindNet(name)
    if not found:
        found = p.NETINFO_ITEM(b, name)
        b.Add(found)
    return found

def xy(item):
    v = item.GetPosition()
    return (p.ToMM(v.x), p.ToMM(v.y))

def trace(points, name, width=.3, layer=p.F_Cu):
    for start, end in zip(points, points[1:]):
        if start == end:
            continue
        t = p.PCB_TRACK(b)
        t.SetStart(pt(*start)); t.SetEnd(pt(*end))
        t.SetWidth(p.FromMM(width)); t.SetLayer(layer); t.SetNet(net(name))
        b.Add(t)

def via(x, y, name='GND', diameter=.9, drill=.35):
    v = p.PCB_VIA(b)
    v.SetPosition(pt(x, y)); v.SetWidth(p.FromMM(diameter))
    v.SetDrill(p.FromMM(drill)); v.SetLayerPair(p.F_Cu, p.B_Cu)
    v.SetViaType(p.VIATYPE_THROUGH); v.SetNet(net(name)); b.Add(v)

def text(value, x, y, size=.8):
    t = p.PCB_TEXT(b); t.SetText(value); t.SetPosition(pt(x, y))
    t.SetLayer(p.F_SilkS); t.SetTextSize(pt(size, size))
    t.SetTextThickness(p.FromMM(.12)); b.Add(t)

fps = {f.GetReference(): f for f in b.GetFootprints()}
detached = []
# The external converter interfaces are replaced by U1 and U2.
for ref in ('J7', 'J10'):
    removed = fps.pop(ref)
    b.Remove(removed)
    removed.thisown = False
    detached.append(removed)
removed_nets = {'Net-(J7-Pin_1)', 'Net-(J10-Pin_1)',
                'Net-(J5-Pin_1)', 'Net-(J10-Pin_3)'}
for t in list(b.GetTracks()):
    if t.GetNetname() in removed_nets or (t.GetNetname() == '/VBAT_FUSED' and t.GetWidth() < p.FromMM(3)):
        b.Remove(t)

def rename(old, new):
    for f in b.GetFootprints():
        for pad in f.Pads():
            if pad.GetNetname() == old:
                pad.SetNet(net(new))

rename('Net-(J7-Pin_1)', '/AUX_VIN')
rename('Net-(J10-Pin_1)', '/PI_VIN')
rename('Net-(J5-Pin_1)', '/AUX_5V')
rename('Net-(J10-Pin_3)', '/PI_5V1')

def place_existing(ref, x, y, angle=0):
    f = fps[ref]
    f.SetOrientationDegrees(angle); f.SetPosition(pt(x, y)); f.SetDNP(False)
    f.Reference().SetPosition(pt(x, y-6.5)); f.Value().SetVisible(False)
    return f

place_existing('J5', 99, 94).SetValue('ESP32_5V_OUT')
place_existing('J11', 101, 122).SetValue('PI_5V1_OUT')
old = fps['F7']
f = p.FootprintLoad(str(OUT / 'Luca_Review.pretty'), 'Bel_0680H_2410_Recommended')
f.SetReference('F7'); f.SetValue('5A_T_0680H5000-05')
f.SetFPID(p.LIB_ID('Luca_Review', 'Bel_0680H_2410_Recommended'))
f.SetPosition(pt(120, 115)); f.SetDNP(False)
for pad in f.Pads():
    pad.SetNet(net('/VBAT_FUSED' if pad.GetNumber() == '2' else '/PI_VIN'))
b.Remove(old); b.Add(f); fps['F7'] = f
f.Reference().SetPosition(pt(120,112.2)); f.Value().SetVisible(False)
for edge in b.GetDrawings():
    if isinstance(edge, p.PCB_SHAPE) and edge.GetLayer() == p.Edge_Cuts:
        start = edge.GetStart(); start.x = p.FromMM(80); edge.SetStart(start)
    if isinstance(edge, p.PCB_TEXT) and 'LUCA REV C' in edge.GetText():
        edge.SetText('LUCA REV D - ONBOARD 5V'); edge.SetPosition(pt(143,128))
# Expand the existing ground zones into the added converter area.
for z in b.Zones():
    outline = z.Outline(); outline.Clear(); outline.NewOutline()
    for x, y in [(80.5,70.5),(198,70.5),(198,129.5),(80.5,129.5)]:
        outline.Append(p.FromMM(x),p.FromMM(y))
    z.SetZoneName('REV_D_GROUND_'+p.LayerName(z.GetLayer()))

parts = json.loads((SRC/'pcba_parts.json').read_text())
parts['revision'] = 'D - onboard AUX 5V / Pi 5.1V converters; prototype'
parts['dnp'] = []
for row in parts['parts']:
    row['refs'] = [r for r in row['refs'] if r not in ('J7','J10')]
parts['parts'] = [row for row in parts['parts'] if row['refs']]
next(row for row in parts['parts'] if 'F8' in row['refs'])['refs'].append('F7')
next(row for row in parts['parts'] if 'J5' in row['refs'])['refs'].append('J11')
parts['external'] = [row for row in parts['external'] if row['item'] != 'External AUX buck']
new = {}

def component(ref, value, footprint, x, y, pins, mpn, manufacturer, angle=0, lcsc='', source=''):
    lib, name = footprint.split(':')
    library = OUT/'Luca_Review.pretty' if lib == 'Luca_Review' else LIB/(lib+'.pretty')
    f = p.FootprintLoad(str(library), name)
    if not f:
        raise RuntimeError(footprint)
    f.SetReference(ref); f.SetValue(value); f.SetFPID(p.LIB_ID(lib,name))
    f.SetOrientationDegrees(angle); f.SetPosition(pt(x,y)); f.SetDNP(False)
    for pad in f.Pads():
        if pad.GetNumber() in pins and pins[pad.GetNumber()]:
            pad.SetNet(net(pins[pad.GetNumber()]))
    f.Reference().SetPosition(pt(x,y-2.8)); f.Reference().SetTextSize(pt(.7,.7))
    f.Reference().SetTextThickness(p.FromMM(.12)); f.Value().SetVisible(False)
    b.Add(f); fps[ref] = f; new[ref] = pins
    match = next((r for r in parts['parts'] if r['mpn'] == mpn), None)
    if match:
        match['refs'].append(ref)
    else:
        parts['parts'].append({'refs':[ref], 'manufacturer':manufacturer, 'mpn':mpn,
            'comment':value, 'lcsc':lcsc, 'source':source,
            'sourcing':'Exact part specified; JLC stock/matching requires confirmation'})
    return f

# TI RPA0010A, datasheet land pattern p29. The duplicated pad 8 shapes form
# one VIN land. Pad 9 and pad 6 use segmented paste per manufacturer p30.
module = p.FOOTPRINT(b); module.SetReference('U**'); module.SetValue('TPS56637RPAR')
module.SetFPID(p.LIB_ID('Luca_Review','TI_RPA0010A_TPS56637'))
module.SetAttributes(p.FP_SMD)
def land(number, x, y, w, h, paste=True):
    q = p.PAD(module); q.SetNumber(number); q.SetAttribute(p.PAD_ATTRIB_SMD)
    q.SetShape(p.PAD_SHAPE_ROUNDRECT); q.SetRoundRectRadiusRatio(min(.05/min(w,h),.25))
    q.SetPosition(pt(x,y)); q.SetSize(pt(w,h))
    layers=p.LSET()
    for layer in ([p.F_Paste] if number == '' else [p.F_Cu,p.F_Mask]+([p.F_Paste] if paste else [])):
        layers.AddLayer(layer)
    q.SetLayerSet(layers); module.Add(q)
for i in range(4):
    land(str(i+1),-1.4,-.75+i*.5,.6,.25)
land('10',-.93,-1.4,.25,.6)
land('5',-.93,1.4,.25,.6)
land('7',.87,1.4,.25,.6)
land('9',-.21,-.65,.4,2.1,False)
land('',-.21,-1.225,.4,.95)
land('',-.21,-.075,.4,.95)
land('6',.37,.85,.25,1.7,False)
land('',.37,.425,.25,.75)
land('',.37,1.375,.25,.75)
land('8',.95,-.65,.4,2.1)
for y in (-.75,-.25,.25):
    land('8',1.4,y,.6,.25)
for layer, half, width in ((p.F_Fab,1.5,.1),(p.F_CrtYd,2,.05)):
    s=p.PCB_SHAPE(module); s.SetShape(p.SHAPE_T_RECT)
    s.SetStart(pt(-half,-half)); s.SetEnd(pt(half,half)); s.SetLayer(layer)
    s.SetWidth(p.FromMM(width)); module.Add(s)
module.Reference().SetPosition(pt(0,-2.5))
p.FootprintSave(str(OUT/'Luca_Review.pretty'),module)

cap1210='Capacitor_SMD:C_1210_3225Metric'
cap0603='Capacitor_SMD:C_0603_1608Metric'
res0603='Resistor_SMD:R_0603_1608Metric'
ti_url='https://www.ti.com/lit/ds/symlink/tps56637.pdf'
diodes_url='https://www.diodes.com/assets/Datasheets/AP63200-AP63201-AP63203-AP63205.pdf'
component('U1','AP63205WU-7', 'Package_TO_SOT_SMD:TSOT-23-6',91,83,
    {'1':'/AUX_5V','2':'/AUX_VIN','3':'/AUX_VIN','4':'GND','5':'/AUX_SW','6':'/AUX_BOOT'},
    'AP63205WU-7','Diodes Incorporated',lcsc='C2071056',source=diodes_url)
component('L1','4.7uH','Inductor_SMD:L_Bourns_SRP5030T',98,83,
    {'1':'/AUX_SW','2':'/AUX_5V'},'SRP5030T-4R7M','Bourns',lcsc='C2045677',
    source='https://www.bourns.com/docs/Product-Datasheets/SRP5030T.pdf')
def ceramic(ref,value,x,y,n1,n2,mpn,footprint=cap1210,angle=270,lcsc=''):
    return component(ref,value,footprint,x,y,{'1':n1,'2':n2},mpn,
                     'Murata' if mpn.startswith('GRM') else 'Samsung Electro-Mechanics',angle,lcsc)
ceramic('C3','10uF 50V X7R',87,87,'/AUX_VIN','GND','GRM32ER71H106KA12L')
ceramic('C4','100nF 50V X7R',91,86.4,'/AUX_VIN','GND','GRM188R71H104KA93D',cap0603,0)
ceramic('C5','100nF 50V X7R',93.5,80.5,'/AUX_BOOT','/AUX_SW','GRM188R71H104KA93D',cap0603,270)
for ref,x in [('C6',104),('C7',108)]:
    ceramic(ref,'22uF 25V X7R',x,84,'/AUX_5V','GND','GRM32ER71E226KE15L',lcsc='C21397')
component('U2','TPS56637RPAR','Luca_Review:TI_RPA0010A_TPS56637',94,109,
    {'1':'','2':'/PI_FB','3':'/PI_AGND','4':'','5':'','6':'/PI_SW','7':'/PI_BOOT','8':'/PI_VIN','9':'GND','10':''},
    'TPS56637RPAR','Texas Instruments',90,'C841386',ti_url)
component('L2','3.3uH','Inductor_SMD:L_Vishay_IHLP-3232',101.2,108.6,
    {'1':'/PI_SW','2':'/PI_5V1'},'IHLP3232DZER3R3M11','Vishay',source=ti_url)
for ref,x in [('C8',88),('C9',84)]:
    ceramic(ref,'10uF 50V X7R',x,106,'/PI_VIN','GND','GRM32ER71H106KA12L')
ceramic('C10','100nF 50V X7R',90.5,109,'/PI_VIN','GND','GRM188R71H104KA93D',cap0603,270)
ceramic('C11','100nF 50V X7R',96.3,105.8,'/PI_BOOT','/PI_SW','GRM188R71H104KA93D',cap0603,0)
for ref,x in [('C12',109),('C13',113)]:
    ceramic(ref,'22uF 25V X7R',x,108,'/PI_5V1','GND','GRM32ER71E226KE15L',lcsc='C21397')
component('R1','75k 0.1%',res0603,92.8,113.2,{'1':'/PI_5V1','2':'/PI_FB'},'RT0603BRD0775KL','Yageo')
component('R2','10k 0.1%',res0603,95,113.2,{'1':'/PI_FB','2':'/PI_AGND'},'RT0603BRD0710KL','Yageo')
component('R3','0R AGND STAR',res0603,96,115.5,{'1':'/PI_AGND','2':'GND'},'RC0603JR-070RL','Yageo')

def pad(ref, number):
    return next(q for q in fps[ref].Pads() if q.GetNumber()==str(number))
def wire(ref1,num1,ref2,num2,middle=(),width=.3,layer=p.F_Cu):
    a=pad(ref1,num1); c=pad(ref2,num2)
    assert a.GetNetname()==c.GetNetname(),(ref1,num1,ref2,num2)
    trace([xy(a),*middle,xy(c)],a.GetNetname(),width,layer)
def ground(ref,number,x,y,width=.6):
    a=pad(ref,number); assert a.GetNetname()=='GND'
    trace([xy(a),(x,y)],'GND',width); via(x,y)

# AUX converter local hot loop, bootstrap and output bank.
wire('U1',3,'C3',1,[(89.7,85.35)],.7)
wire('U1',3,'U1',2,width=.5)
wire('U1',3,'C4',1,[(89.7,86.4)],.4)
wire('U1',4,'C4',2,[(92.3,85.9)],.6)
ground('U1',4,94,85.2)
ground('C3',2,87,90)
ground('C4',2,93.5,86.4)
wire('U1',5,'L1',1,width=.8)
wire('U1',6,'C5',1,[(92.3,79.675)],.25)
wire('C5',2,'L1',1,[(95.1,81.325)],.4)
wire('L1',2,'C6',1,[(102,82.35)],1.8)
wire('C6',1,'C7',1,width=2)
for ref in ('C6','C7'):
    x,y=xy(pad(ref,2)); ground(ref,2,x,y+1.5,1)
wire('U1',1,'C7',1,[(88.5,82.05),(88.5,77.5),(110,77.5),(110,82.35)],.3)
for x in (110,111.5):
    via(x,82.35,'/AUX_5V',1.5,.8)
trace([xy(pad('C7',1)),(111.5,82.35)],'/AUX_5V',1.8)
trace([(110,82.35),(110,90),(99,94)],'/AUX_5V',1.8,p.B_Cu)

# Pi converter, matching TI's separation of the power and feedback loops.
wire('C8',1,'C9',1,width=2.5)
trace([xy(pad('U2',8)),(91,108.05),(91,104.35),xy(pad('C8',1))],'/PI_VIN',.8)
wire('C10',1,'U2',8,[(91,108.175)],.4)
wire('U2',9,'C10',2,[(91,109.21),(91,109.825)],.4)
ground('C10',2,90.5,111,.6)
for ref in ('C8','C9'):
    x,y=xy(pad(ref,2)); ground(ref,2,x,y+1.2,1.2)
trace([xy(pad('U2',9)),(91.8,109.21),(91.8,110.4)],'GND',.4)
via(91.8,110.4)
wire('U2',6,'L2',1,width=.8)
wire('U2',7,'C11',1,[(95.4,105.8)],.2)
wire('C11',2,'L2',1,[(97.125,108.63)],.5)
wire('L2',2,'C12',1,[(106,106.35)],3)
wire('C12',1,'C13',1,width=3)
for ref in ('C12','C13'):
    x,y=xy(pad(ref,2))
    for dx in (-.6,.6):
        ground(ref,2,x+dx,y+1.5,1)
wire('U2',2,'R1',2,[(93.75,112)],.2)
wire('R1',2,'R2',1,width=.25)
wire('U2',3,'R2',2,[(94.25,111.8),(95.825,111.8)],.2)
wire('R2',2,'R3',1,[(95.825,114.5)],.3)
ground('R3',2,97.5,115.5)
trace([xy(pad('R1',1)),(90,113.2),(90,114)],'/PI_5V1',.25)
via(90,114,'/PI_5V1')
trace([(90,114),(90,117.5),(111,117.5),(115.5,113),(115.5,104)],'/PI_5V1',.3,p.B_Cu)
via(115.5,104,'/PI_5V1')
trace([(115.5,104),xy(pad('C13',1))],'/PI_5V1',.4)
for x in (109,110.6,112.2,113.8):
    via(x,103,'/PI_5V1',1.5,.8)
trace([(109,103),(113.8,103)],'/PI_5V1',3)
trace([(109,103),xy(pad('C12',1))],'/PI_5V1',3)
trace([(111,103),(111,112),(101,122)],'/PI_5V1',4,p.B_Cu)
for x,y in [(82,96),(94,98),(96,73),(84,114),(88,120),(108,114),(116,101),(116,121)]:
    via(x,y,'GND',1.4,.6)
text('ESP32 5V +   GND',101.5,100.5)
text('PI 5.1V +   GND',103.5,128.2)
text('5V AUX BUCK',95,73.5)
text('5.1V PI BUCK',95,101)
text('FUSED+  SWITCHED+',165,104.8,.7)

# Rules retain the distribution minimum and permit only the new converter
# circuitry to use the fine traces required by its IC pads.
(OUT/f'{NAME}.kicad_dru').write_text('''(version 1)
(rule "Distribution clearance" (constraint clearance (min 0.2mm)))
(rule "Distribution width" (constraint track_width (min 0.5mm)))
(rule "Converter signal width" (condition "A.NetName == '/PI_FB' || A.NetName == '/PI_AGND' || A.NetName == '/PI_BOOT' || A.NetName == '/PI_5V1' || A.NetName == '/AUX_BOOT' || A.NetName == '/AUX_5V' || A.NetName == '/AUX_SW' || A.NetName == '/PI_VIN' || A.NetName == '/AUX_VIN' || A.NetName == 'GND'") (constraint track_width (min 0.2mm)))
(rule "TI fine pitch pads" (condition "A.memberOfFootprint('U2') && B.memberOfFootprint('U2')") (constraint clearance (min 0.15mm)))
(rule "Drill" (constraint hole_size (min 0.3mm)))
(rule "Annular ring" (constraint annular_width (min 0.254mm)))
(rule "Copper edge" (constraint edge_clearance (min 0.5mm)))
''',encoding='utf-8')
p.SaveBoard(str(OUT/f'{NAME}.kicad_pcb'),b)
(OUT/'pcba_parts.json').write_text(json.dumps(parts,indent=2)+'\n',encoding='utf-8')
(OUT/'converter_pins.json').write_text(json.dumps(new,indent=2)+'\n',encoding='utf-8')
print('Created Rev D PCB with two onboard converters')
