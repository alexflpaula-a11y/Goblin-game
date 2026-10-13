"""Repair preserved original artwork. Never regenerate or redesign the wolves.
Source PNGs were recovered from commit 72e94b2. Requires Pillow.
"""
import math, shutil
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/sprites/raid'
SRC=ROOT/'art-source/wolves-original'

def original(kind,anim,i):
 return Image.open(SRC/f'{kind}_{anim}_{i}.png').convert('RGBA')

def remove_white_background(im):
 # Flood only exterior white: enclosed teeth and metal highlights stay intact.
 pix=im.load();w,h=im.size;q=deque([(x,y) for x in range(w) for y in (0,h-1)]+[(x,y) for y in range(h) for x in (0,w-1)]);seen=set()
 while q:
  x,y=q.popleft()
  if (x,y) in seen or not (0<=x<w and 0<=y<h):continue
  seen.add((x,y));r,g,b,a=pix[x,y]
  if a and min(r,g,b)<235:continue
  pix[x,y]=(0,0,0,0)
  q.extend(((x-1,y),(x+1,y),(x,y-1),(x,y+1)))
 return im

for p in SRC.glob('*.png'):shutil.copyfile(p,OUT/p.name)
# One anticipation, one contact, one recovery. No unrelated recoils/repeated leaps.
orders={
 'wolf':[0,1,2,2,3,4,5,5,6,7,7,6,1,0,0,0,0],
 'twin_jaw':[0,1,1,2,2,3,3,4,4,5,5,6,6,7,0,0,0],
 'twin_paw':[0,1,1,2,2,3,4,4,5,5,6,6,7,0,0,0,0],
}
for kind,order in orders.items():
 for i,src in enumerate(order):
  im=remove_white_background(original(kind,'attack',src))
  im.save(OUT/f'{kind}_attack_{i}.png',optimize=True)
 # Original actual folding-leg fall, then a stable corpse; no upright squash/rotation.
 for i in range(15):
  pose=min(i,6)
  if kind=='wolf':im=original(kind,'death',pose)
  elif i==0:im=original(kind,'idle',0)
  else:
   im=Image.new('RGBA',(56,36));im.alpha_composite(original('wolf','death',pose),(4,4))
   source=original(kind,'idle',0)
   if kind=='twin_jaw':
    plate=source.crop((36,14,48,20))
    # Keep the original steel muzzle only, not surrounding fur/background.
    for y in range(plate.height):
     for x in range(plate.width):
      r,g,b,a=plate.getpixel((x,y))
      if not (a and (max(r,g,b)-min(r,g,b)<22 or b>=r)):plate.putpixel((x,y),(0,0,0,0))
    cream=[(x,y) for y in range(36) for x in range(30,56) if (lambda c:c[3]>0 and c[0]>145 and c[1]>130 and c[2]<c[0]*.9)(im.getpixel((x,y)))]
    if cream:
     mx=max(x for x,y in cream);my=max(y for x,y in cream)
     im.alpha_composite(plate,(min(44,mx-9),min(30,my-3)))
   else:
    plate=source.crop((30,27,42,36))
    if pose>=4:plate=plate.rotate(75,resample=Image.Resampling.NEAREST,expand=True)
    im.alpha_composite(plate,(34,max(0,36-plate.height)))
  im.save(OUT/f'{kind}_death_{i}.png',optimize=True)

# Articulate separate limbs about their hip, alternating stance and swing.
# Upper silhouette remains EXACTLY the original; no global bob or lower-row shear.
settings={'boar':(44,[0,23,41,58,78,96]),'deer':(54,[0,21,38,47,58,67]),'hare':(40,[0,32,46,63])}
for kind,(cut,edges) in settings.items():
 base=Image.open(ROOT/f'art-source/animals-original/animal_{kind}.png').convert('RGBA')
 w,h=base.size;pad=8;size=(w+pad*2,h+pad*2)
 idle=Image.new('RGBA',size);idle.alpha_composite(base,(pad,pad));idle.save(OUT/f'animal_{kind}.png',optimize=True)
 torso=base.copy();ImageDraw.Draw(torso).rectangle((0,cut,w,h),fill=(0,0,0,0))
 for i in range(8):
  frame=Image.new('RGBA',size)
  for j,(left,right) in enumerate(zip(edges,edges[1:])):
   limb=Image.new('RGBA',size);piece=base.crop((left,cut-3,right,h));limb.alpha_composite(piece,(left+pad,cut-3+pad))
   phase=i/8*math.tau+(j%2)*math.pi
   angle=math.sin(phase)*(28 if kind!='hare' else 35)
   limb=limb.rotate(angle,resample=Image.Resampling.NEAREST,center=((left+right)/2+pad,cut+pad))
   lift=round(max(0,math.cos(phase))*3)
   frame.alpha_composite(limb,(0,-lift))
  frame.alpha_composite(torso,(pad,pad))
  frame.save(OUT/f'animal_{kind}_walk_{i}.png',optimize=True)
