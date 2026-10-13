"""Derive short recoil/collapse tracks from each twin's armored base.
These procedural tracks preserve armor until dedicated hand-drawn frames replace them.
Requires Pillow. Never regenerate the character for individual poses.
"""
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/sprites/raid'
for kind in ('jaw', 'paw'):
    base = Image.open(ROOT / f'art-source/war-twins/{kind}.png').convert('RGBA')
    # Keep the paw armor in every idle frame (the generated first cell lacked it).
    if kind == 'paw':
        base.save(OUT / 'twin_paw_idle_0.png')
    for anim, count in [('hurt', 17), ('death', 15)]:
        for i in range(count):
            t = i / (count - 1)
            frame = Image.new('RGBA', base.size)
            if anim == 'hurt':
                recoil = max(0, 1 - t * 1.8)
                spr = base.resize((54, 36), Image.Resampling.NEAREST)
                frame.alpha_composite(spr, (-round(2 * recoil), -round(2 * recoil)))
            else:
                # Knees buckle, shoulders sink; final silhouette stays prone.
                collapse = min(1, t * 1.5)
                height = round(36 - 17 * collapse)
                spr = base.resize((56, height), Image.Resampling.NEAREST)
                frame.alpha_composite(spr, (0, 36 - height))
            frame.save(OUT / f'twin_{kind}_{anim}_{i}.png', optimize=True)
