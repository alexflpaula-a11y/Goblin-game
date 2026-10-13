"""Consistent pixel skeleton for wolves; gait animation for existing animal art.
All frames have fixed canvas, baseline, palette and attachment anchors.
Requires Pillow. No resampling between independently generated wolf drawings.
"""
import math,json
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'assets/sprites/raid'
COUNTS={'idle':5,'walk':8,'attack':17,'hurt':17,'death':15}
C={'edge':'#211e1a','fur':'#797461','dark':'#514d41','light':'#a09a80','cream':'#d9d0a4','metal':'#7d8992','shine':'#d1dce1'}
def wolf(anim,i,n,kind):
 im=Image.new('RGBA',(56,36));d=ImageDraw.Draw(im);t=i/max(1,n-1)
 phase=i/n*math.tau
 bob=round(math.sin(phase)) if anim in ('walk','idle') else 0
 crouch=round(2*math.sin(t*math.pi)) if anim=='attack' else 0
 fall=min(1,t*1.6) if anim=='death' else 0
 recoil=round(-2*math.sin(t*math.pi)) if anim=='hurt' else 0
 oy=bob+crouch+round(fall*6); ox=recoil
 def poly(points,color):d.polygon([(x+ox,y+oy) for x,y in points],fill=color,outline=C['edge'])
 def line(points,color,width=1):d.line([(x+ox,y+oy) for x,y in points],fill=color,width=width)
 # Tail and far legs.
 poly([(16,18),(8,20),(2,17),(4,23),(10,25),(18,22)],C['fur'])
 for k,x in enumerate([20,37,15,33]):
  swing=round(math.sin(phase+(k%2)*math.pi)*3) if anim=='walk' else 0
  if anim=='attack':swing=round(math.sin(t*math.pi)*3)*(1 if k%2 else -1)
  footY=32-oy-round(max(0,math.sin(phase+k))*2) if anim=='walk' else 32-oy
  if fall: footY=32-oy; swing=round(fall*5)
  lift=round(7*math.sin(t*math.pi)) if kind=='twin_paw' and anim=='attack' and k>=2 else 0
  poly([(x,21),(x+4,21),(x+3+swing,footY-2-lift),(x+6+swing,footY-1-lift),(x+6+swing,footY+1-lift),(x+swing,footY+1-lift)],C['dark'] if k<2 else C['fur'])
  if kind=='twin_paw':
   fx=x+swing;fy=footY-3-lift
   poly([(fx,fy),(fx+4,fy-1),(fx+7,fy+2),(fx+6,fy+4),(fx,fy+4)],C['metal'])
   line([(fx+1,fy),(fx+4,fy)],C['shine'])
   for claw in (1,3,5):line([(fx+claw,fy+3),(fx+claw+1,fy+5)],C['shine'])
 poly([(12,16),(19,13),(30,13),(36,9),(43,12),(43,21),(35,25),(24,25),(16,23),(13,26)],C['fur'])
 line([(18,15),(29,15),(34,12)],C['light'])
 poly([(34,16),(40,15),(41,22),(37,27),(32,24)],C['cream'])
 # Shared head silhouette never changes breed across animations.
 headY=round(2*math.sin(t*math.pi)) if anim=='attack' else 0
 if fall: headY+=round(fall*3)
 oy+=headY
 poly([(32,12),(32,3),(37,7),(42,6),(45,2),(46,12),(49,16),(54,18),(53,22),(44,23),(39,21),(36,17)],C['fur'])
 line([(34,6),(34,10)],C['cream'],2)
 poly([(41,15),(45,15),(48,18),(53,18),(52,22),(45,23),(40,20)],C['cream'])
 line([(51,17),(54,18),(54,20)],C['edge'],2)
 if anim!='death' or t<0.5:
  line([(43,12),(46,12)],C['edge'],2);line([(44,12),(45,12)],'#f3d658')
 else:line([(43,13),(46,14)],C['edge'])
 mouth=round(3*math.sin(t*math.pi)) if anim=='attack' and kind!='twin_paw' else 0
 if mouth:
  poly([(45,21),(52,21),(51,23+mouth),(44,23+mouth)],'#6f3431')
  line([(48,22),(48,23)],'#fff1cd')
 if kind=='twin_jaw':
  poly([(42,20),(47,21),(53,21),(51,25+mouth),(44,24+mouth),(41,22)],C['metal'])
  line([(44,21),(50,22)],C['shine']);line([(43,9),(45,14)],'#914b3b')
  for x in (44,48,51):line([(x,22+mouth),(x,23+mouth)],C['shine'])
 elif kind=='twin_paw':
  line([(45,9),(42,16)],'#ac6953');line([(43,11),(45,13)],'#e2b096')
 return im
for kind in ('wolf','twin_jaw','twin_paw'):
 for anim,n in COUNTS.items():
  for i in range(n):
   im=wolf(anim,i,n,kind)
   if kind=='wolf':im=im.resize((48,32),Image.Resampling.NEAREST)
   im.save(OUT/f'{kind}_{anim}_{i}.png',optimize=True)
# Keep the original animals' art, move their legs in an alternating eight-frame gait.
for kind in ('boar','deer','hare'):
 base=Image.open(OUT/f'animal_{kind}.png').convert('RGBA')
 base.thumbnail((48,48),Image.Resampling.NEAREST)
 base.save(OUT/f'animal_{kind}.png',optimize=True)
 w,h=base.size;split=round(h*0.70)
 for i in range(8):
  frame=Image.new('RGBA',(w,h));phase=i/8*math.tau
  for y in range(h):
   for x in range(w):
    pixel=base.getpixel((x,y))
    if not pixel[3]:continue
    dx=round(math.sin(phase+(0 if x<w/2 else math.pi))*2*(y-split)/max(1,h-split)) if y>=split else 0
    yy=y+(round(math.sin(phase)*1) if y<split else 0)
    if 0<=x+dx<w and 0<=yy<h:frame.putpixel((x+dx,yy),pixel)
  frame.save(OUT/f'animal_{kind}_walk_{i}.png',optimize=True)
for name in ('bg_den','bg_den_twins'):
 p=OUT/f'{name}.png';im=Image.open(p).convert('RGB');im.resize((640,360),Image.Resampling.NEAREST).save(p,optimize=True)
# Meat is distinct from farm food, but keeps the established meat icon style.
manifest=ROOT/'assets/manifest.json';m=json.loads(manifest.read_text());ids={x['id'] for x in m['sprites']}
food=next(x for x in m['sprites'] if x['id']=='res_food')
Image.open(ROOT/food['path']).save(OUT/'res_meat.png')
for p in OUT.glob('*.png'):
 if p.stem not in ids:m['sprites'].append({'id':p.stem,'path':str(p.relative_to(ROOT))})
manifest.write_text(json.dumps(m,indent=2)+'\n')
