import pcbnew as p, wx, sys
from pathlib import Path
root=Path(__file__).parent
input_path=Path(sys.argv[1]) if len(sys.argv)>1 else root/'Luca_power_distribution_manufacturing.kicad_pcb'
root=input_path.parent
b=p.LoadBoard(str(input_path))
board_width=round(b.GetBoardEdgesBoundingBox().GetWidth()/1e6,1)
app=wx.App(False); bmp=wx.Bitmap(max(1100,round(board_width*14+140)),1000);dc=wx.MemoryDC(bmp)
dc.SetBackground(wx.Brush('#182530'));dc.Clear()
scale=14
def pt(v):return (round(70+(v.x/1e6-110)*scale),round(70+(v.y/1e6-70)*scale))
for layer,color in ((p.B_Cu,'#5588c6'),(p.F_Cu,'#d85353')):
 for t in b.GetTracks():
  if isinstance(t,p.PCB_VIA):continue
  if t.GetLayer()!=layer:continue
  dc.SetPen(wx.Pen(color,max(1,round(t.GetWidth()/1e6*scale))))
  dc.DrawLine(*pt(t.GetStart()),*pt(t.GetEnd()))
dc.SetPen(wx.Pen('#eeeeee',1));dc.SetBrush(wx.TRANSPARENT_BRUSH)
dc.DrawRectangle(70,70,round(board_width*scale),round(60*scale))
for t in b.GetTracks():
 if not isinstance(t,p.PCB_VIA):continue
 x,y=pt(t.GetPosition());d=round(t.GetWidth(p.F_Cu)/1e6*scale)
 dc.SetPen(wx.Pen('#bba568',1));dc.SetBrush(wx.Brush('#182530'));dc.DrawEllipse(x-d//2,y-d//2,d,d)
dc.SetFont(wx.Font(10,wx.FONTFAMILY_SWISS,wx.FONTSTYLE_NORMAL,wx.FONTWEIGHT_NORMAL));dc.SetTextForeground('#ffffff')
for f in b.GetFootprints():
 if f.GetReference()!='REF**':
  x,y=pt(f.GetPosition());dc.DrawText(f.GetReference(),x-10,y-35)
 for q in f.Pads():
  x,y=pt(q.GetPosition());sx=round(q.GetSize().x/1e6*scale);sy=round(q.GetSize().y/1e6*scale)
  dc.SetPen(wx.Pen('#eeeeaa',1));dc.SetBrush(wx.Brush('#bba568'))
  dc.DrawEllipse(x-sx//2,y-sy//2,sx,sy)
  d=round(q.GetDrillSize().x/1e6*scale);dc.SetBrush(wx.Brush('#182530'));dc.DrawEllipse(x-d//2,y-d//2,d,d)
dc.SelectObject(wx.NullBitmap);bmp.SaveFile(str(root/'layout-preview.png'),wx.BITMAP_TYPE_PNG)
