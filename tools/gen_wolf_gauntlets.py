"""Opaque pixel overlays aligned to the base goblin in every animation.
Also builds a separate ground sprite. Requires Pillow.
"""
from pathlib import Path
import json
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[1]
SPR = ROOT / 'assets/sprites'
OUT = SPR / 'goblin-gear-overlays'
OUT.mkdir(exist_ok=True)
counts = dict(idle=5, walk=8, attack=17, hurt=17, death=15)
for anim, count in counts.items():
    for frame in range(count):
        base = Image.open(SPR / f'goblins/goblin_{anim}_{frame}.png').convert('RGBA')
        # Hands share the base body's silhouette across physical variations.
        pts = [(x,y) for y in range(20,30) for x in range(32)
               if (lambda c: c[3]>128 and c[1]>c[0]*1.2 and c[1]>c[2]*1.05)(base.getpixel((x,y)))]
        hands = [min(pts,key=lambda p:p[0]),max(pts,key=lambda p:p[0])] if pts else [(11,24),(21,24)]
        im=Image.new('RGBA',(32,32));d=ImageDraw.Draw(im)
        for index,(x,y) in enumerate(hands):
            x=max(2,min(27,x));y=max(2,min(27,y))
            # Solid steel covers the hand, never a translucent tint.
            d.rectangle((x-2,y-1,x+2,y+3),fill='#242a34')
            d.rectangle((x-1,y,x+1,y+2),fill='#909ca9')
            d.line((x-1,y,x+1,y),fill='#e3eff6')
            d.point((x+1,y+2),fill='#f4f5e5')
            for k in range(3):
                d.line((x+k-1,y+3,x+k,y+5),fill='#d3dce2')
        im.save(OUT/f'overlay_wpn_manoplas_{anim}_{frame}.png')
icon=Image.open(SPR/'raid/item_manoplas_lobo.png').convert('RGBA')
icon.thumbnail((28,26),Image.Resampling.NEAREST)
drop=Image.new('RGBA',(36,36));drop.alpha_composite(icon,((36-icon.width)//2,(36-icon.height)//2))
drop.save(SPR/'raid/drop_manoplas_lobo.png')
# Missing resource icon used by the chest row: a small green goblin gem.
gem=Image.new('RGBA',(32,32));d=ImageDraw.Draw(gem)
d.polygon([(16,2),(27,11),(23,25),(16,30),(5,22),(4,10)],fill='#113929')
d.polygon([(16,4),(25,12),(16,27),(6,11)],fill='#52c792')
d.polygon([(16,4),(16,27),(6,11)],fill='#b1ffe0')
gem.save(SPR/'raid/res_goblin_gems.png')
mfile=ROOT/'assets/manifest.json';m=json.loads(mfile.read_text());ids={e['id'] for e in m['sprites']}
paths=list(OUT.glob('overlay_wpn_manoplas_*.png'))+[SPR/'raid/drop_manoplas_lobo.png',SPR/'raid/res_goblin_gems.png']
for p in paths:
    if p.stem not in ids:m['sprites'].append(dict(id=p.stem,path=str(p.relative_to(ROOT))))
mfile.write_text(json.dumps(m,indent=2)+'\n')
