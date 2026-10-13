"""Redraw non-Avaritia equipment icons and fitted opaque overlays.
Preserves every Avaritia asset. Keeps original armor masks as reproducible sources.
"""
from PIL import Image, ImageDraw
from pathlib import Path
import json, shutil
ROOT=Path(__file__).resolve().parents[1]; SPR=ROOT/'assets/sprites'; OVER=SPR/'goblin-gear-overlays'
SRC=ROOT/'art-source/equipment-masks';SRC.mkdir(parents=True,exist_ok=True)
counts={'idle':5,'walk':8,'attack':17,'hurt':17,'death':15}
edge='#292a30';steel='#7d8b96';light='#c9d6db';shade='#4a5765';gold='#c59748';wood='#94653d';cream='#eee2b7'
# Icons are hand-drawn on the same pixel grid, not unrelated generated images.
names=['capacete_ferro','peitoral_ferro','calca_ferro','botas_couro','anel_cobre','anel_rubi','colar_presas','espada_ferro','clava_goblin','escudo_madeira','manoplas_lobo']
paths=[]
for name in names:
 im=Image.new('RGBA',(32,32));d=ImageDraw.Draw(im)
 def poly(p,c):d.polygon(p,fill=c,outline=edge,width=1)
 if name=='capacete_ferro':
  poly([(5,22),(6,12),(11,5),(21,5),(26,12),(27,22),(22,25),(20,15),(12,15),(10,25)],steel)
  poly([(14,6),(18,6),(19,23),(15,26)],shade);d.line((9,12,12,8,14,8),fill=light,width=2)
  d.line((7,23,10,24),fill=gold);d.line((22,24,25,23),fill=gold)
 elif name=='peitoral_ferro':
  poly([(4,8),(11,5),(14,9),(18,9),(21,5),(28,8),(26,15),(23,15),(23,27),(9,27),(9,15),(5,15)],steel)
  poly([(10,12),(16,15),(22,12),(21,24),(16,27),(11,24)],shade)
  d.line((7,9,11,7),fill=light,width=2);d.line((11,13,15,16,21,13),fill=light)
  d.line((10,25,22,25),fill=gold,width=2);d.rectangle((15,24,17,26),fill=light)
 elif name=='calca_ferro':
  poly([(7,5),(25,5),(24,16),(26,27),(17,28),(16,18),(14,28),(6,27),(8,16)],steel)
  d.rectangle((8,6,24,9),fill=shade);d.rectangle((14,6,18,9),fill=gold)
  for x in (9,20):
   d.rectangle((x,14,x+3,19),fill=shade);d.line((x,14,x+3,14),fill=light);d.line((x,22,x+3,22),fill=light)
 elif name=='botas_couro':
  for x,y in [(5,6),(17,9)]:
   poly([(x,y),(x+7,y),(x+6,y+12),(x+10,y+16),(x+10,y+19),(x,y+19)],wood)
   d.line((x+1,y+3,x+6,y+3),fill=gold,width=2);d.line((x+1,y+17,x+8,y+17),fill=shade,width=2)
 elif name.startswith('anel'):
  d.ellipse((6,9,25,28),fill=edge);d.ellipse((8,11,23,26),fill=gold if name=='anel_cobre' else '#af7246');d.ellipse((11,14,20,23),fill=(0,0,0,0))
  if name=='anel_rubi':poly([(11,5),(20,5),(24,10),(16,16),(8,10)],'#bd4854');d.line((12,6,18,6,12,11),fill='#f38f80')
  else:d.arc((8,11,23,26),180,290,fill=cream,width=2)
 elif name=='colar_presas':
  d.arc((5,2,26,24),0,180,fill='#93683e',width=2)
  for x,y in [(8,16),(14,20),(21,16)]:poly([(x,y),(x+4,y-1),(x+1,y+8)],cream)
 elif name=='espada_ferro':
  poly([(20,2),(26,3),(25,9),(12,23),(7,18)],steel)
  d.line((23,5,10,19),fill=light,width=2);d.line((6,17,15,24),fill=gold,width=3)
  d.line((9,21,4,27),fill=edge,width=5);d.line((9,21,4,27),fill=wood,width=3);d.rectangle((2,26,5,29),fill=gold)
 elif name=='clava_goblin':
  d.line((16,15,8,28),fill=edge,width=5);d.line((16,15,8,28),fill=wood,width=3)
  poly([(14,4),(24,6),(26,14),(19,20),(11,15),(10,9)],wood)
  d.line((14,8,22,12),fill=shade,width=3);d.line((13,13,20,17),fill=shade,width=3)
  for p in [(14,6),(24,10),(18,17)]:d.rectangle((p[0],p[1],p[0]+1,p[1]+1),fill=light)
 elif name=='escudo_madeira':
  poly([(4,7),(16,3),(28,7),(26,21),(16,29),(6,21)],steel)
  poly([(7,9),(16,6),(25,9),(23,20),(16,25),(9,20)],wood)
  for x in (12,19):d.line((x,8,x,22),fill='#66482f')
  d.ellipse((12,12,20,20),fill=shade,outline=edge);d.line((14,13,17,13),fill=light)
 elif name=='manoplas_lobo':
  for x,y in [(3,9),(17,5)]:
   poly([(x,y),(x+8,y),(x+10,y+10),(x+7,y+15),(x,y+13),(x-1,y+7)],steel)
   d.rectangle((x,y,x+8,y+3),fill=wood);d.line((x+1,y+5,x+6,y+5),fill=light)
   for k in (0,3,6):poly([(x+k,y+11),(x+k+2,y+11),(x+k+1,y+20)],light)
 path=SPR/('raid' if name=='manoplas_lobo' else 'items')/f'item_{name}.png';im.save(path);paths.append(path)
 ground=Image.new('RGBA',(36,36));ground.alpha_composite(im,(2,2));path=SPR/'raid'/f'drop_{name}.png';ground.save(path);paths.append(path)
# Preserve the proven silhouettes of armor, but replace the muddy shading with solid steel.
for prefix in ('ferro_cap','ferro_pei','ferro_cal'):
 for anim,n in counts.items():
  for i in range(n):
   p=OVER/f'overlay_{prefix}_{anim}_{i}.png';source=SRC/p.name
   if not source.exists():shutil.copyfile(p,source)
   old=Image.open(source).convert('RGBA');out=Image.new('RGBA',old.size);mask=old.getchannel('A')
   for y in range(32):
    for x in range(32):
     if mask.getpixel((x,y))<100:continue
     top=y==0 or mask.getpixel((x,y-1))<100
     bottom=y==31 or mask.getpixel((x,y+1))<100
     left=x==0 or mask.getpixel((x-1,y))<100
     col=light if top else edge if bottom else shade if left else steel
     out.putpixel((x,y),(*tuple(bytes.fromhex(col[1:])),255))
   out.save(p)
   # Single-piece full sprites must agree with composites.
   if prefix=='ferro_pei':
    full=Image.open(SPR/f'goblins/goblin_{anim}_{i}.png').convert('RGBA');full.alpha_composite(out)
    fullpath=next((ROOT/e['path'] for e in json.loads((ROOT/'assets/manifest.json').read_text())['sprites'] if e['id']==f'ferro_pei_{anim}_{i}'),None)
    if fullpath:full.save(fullpath)
# Fitted hand attachments: small opaque wrist/knuckle plates rather than giant squares.
for anim,n in counts.items():
 for i in range(n):
  base=Image.open(SPR/f'goblins/goblin_{anim}_{i}.png').convert('RGBA')
  pts=[(x,y) for y in range(21,29) for x in range(5,27) if (lambda c:c[3]>128 and c[1]>c[0]*1.2 and c[1]>c[2]*1.05)(base.getpixel((x,y)))]
  if pts:
   leftX=min(x for x,y in pts);rightX=max(x for x,y in pts)
   hands=[max([p for p in pts if p[0]<=leftX+1],key=lambda p:p[1]),max([p for p in pts if p[0]>=rightX-1],key=lambda p:p[1])]
  else:hands=[(10,25),(20,24)]
  for prefix in ('wpn_manoplas','wpn_espada','wpn_clava','wpn_escudo'):
   im=Image.new('RGBA',(32,32));d=ImageDraw.Draw(im);x,y=hands[1]
   if prefix=='wpn_manoplas':
    for x,y in hands:
     d.polygon([(x-1,y-2),(x+1,y-2),(x+2,y),(x+1,y+2),(x-1,y+1)],fill=steel,outline=edge)
     d.line((x-1,y-2,x+1,y-2),fill=wood);d.point((x,y-1),fill=light)
     d.line((x,y+1,x,y+3),fill=light);d.line((x+2,y+1,x+2,y+2),fill=light)
   elif prefix=='wpn_espada':
    d.line((x,y+1,x,y-7),fill=edge,width=3);d.line((x,y-2,x,y-7),fill=steel);d.point((x,y-8),fill=light);d.line((x-2,y-1,x+2,y-1),fill=gold);d.point((x,y+1),fill=wood)
   elif prefix=='wpn_clava':
    d.line((x,y+1,x,y-3),fill=wood);d.polygon([(x-2,y-6),(x,y-8),(x+2,y-6),(x+1,y-2),(x-1,y-2)],fill=wood,outline=edge);d.line((x-1,y-5,x+1,y-5),fill=steel)
   else:
    x,y=hands[0];d.polygon([(x-3,y-4),(x+2,y-4),(x+3,y),(x,y+4),(x-3,y+1)],fill=wood,outline=shade);d.line((x-2,y-3,x+1,y-3),fill=light);d.point((x,y),fill=light)
   p=OVER/f'overlay_{prefix}_{anim}_{i}.png';im.save(p);paths.append(p)
mfile=ROOT/'assets/manifest.json';m=json.loads(mfile.read_text());ids={e['id'] for e in m['sprites']}
for p in paths:
 if p.stem not in ids:m['sprites'].append(dict(id=p.stem,path=str(p.relative_to(ROOT))));ids.add(p.stem)
mfile.write_text(json.dumps(m,indent=2)+'\n')
