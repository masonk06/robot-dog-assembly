"""Plot sampled servo target and measured ticks from a replay JSONL log."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('log', type=Path)
p.add_argument('output', type=Path)
args = p.parse_args()
series = {i: [] for i in (8, 9, 10, 12)}
for line in args.log.read_text().splitlines():
    event = json.loads(line); fields = event['raw'].split(',')
    if fields[0] == 'LIVE' and len(fields) >= 4:
        sid = int(fields[1])
        if sid in series: series[sid].append((event['host_elapsed_s'], int(fields[2]), int(fields[3])))
if any(not values for values in series.values()): raise ValueError('Missing rear-joint telemetry')
img = Image.new('RGB', (1400, 1000), 'white'); draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype('arial.ttf', 20); small = ImageFont.truetype('arial.ttf', 15)
except OSError: font = small = ImageFont.load_default()
draw.text((20, 10), 'Supported gait: sampled target (blue) vs measured position (orange)', fill='black', font=font)
names = {8: 'Rear-left hip pitch', 9: 'Rear-left knee', 10: 'Rear-right hip pitch', 12: 'Rear-right knee'}
for index, (sid, samples) in enumerate(series.items()):
    x0 = 95; x1 = 1350; y0 = 62 + index*230; y1 = y0+175
    tmin = min(v[0] for v in samples); tmax = max(v[0] for v in samples)
    low = min(min(v[1:]) for v in samples)-30; high = max(max(v[1:]) for v in samples)+30
    def point(t, tick): return (x0+(t-tmin)/(tmax-tmin)*(x1-x0), y1-(tick-low)/(high-low)*(y1-y0))
    draw.rectangle((x0,y0,x1,y1),outline='#777777')
    for j in range(5):
        y=y0+(y1-y0)*j/4; value=high-(high-low)*j/4
        draw.line((x0,y,x1,y),fill='#e5e5e5'); draw.text((24,y-8),f'{value:.0f}',fill='#444',font=small)
    for t in range(int(tmin)+1,int(tmax)+1,2):
        x=point(t,low)[0]; draw.line((x,y0,x,y1),fill='#eeeeee');draw.text((x-8,y1+3),str(t),fill='#444',font=small)
    for pos,color in ((2,'#2465b1'),(1,'#d46a22')):
        draw.line([point(row[0],row[pos]) for row in samples],fill=color,width=3)
    draw.text((x0+5,y0+4),f'{names[sid]} (ID {sid})',fill='black',font=font)
draw.text((1100,975),'time: seconds',fill='#444',font=small)
args.output.parent.mkdir(parents=True, exist_ok=True);img.save(args.output)
print(args.output)
