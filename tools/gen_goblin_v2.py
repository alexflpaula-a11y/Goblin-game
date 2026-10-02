#!/usr/bin/env python3
"""
Gera TODOS os sprites de goblin do jogo a partir do rig v2.

    python3 tools/gen_goblin_v2.py            # base + 45 variacoes
    python3 tools/gen_goblin_v2.py --preview  # so monta as folhas de conferencia

Saida (mesmos nomes que o jogo e o manifest ja usam, nada quebra):

    assets/sprites/goblins/goblin_<acao>_<n>.png
    assets/sprites/goblins/variant_<id>_<acao>_<n>.png

Sao 46 x 62 = 2852 quadros de 32x32.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image                      # noqa: E402

import goblin_anim as A                    # noqa: E402
import goblin_rig as R                     # noqa: E402
import goblin_variations as V              # noqa: E402

OUT = ROOT / 'assets' / 'sprites' / 'goblins'
PREVIEW = ROOT / 'art-source' / 'goblins-v2'


def write_set(prefix, variation, out_dir):
    frames = A.render_all(variation)
    n = 0
    for action in A.ACTIONS:
        for i, img in enumerate(frames[action]):
            R.save_png(img, out_dir / f'{prefix}{action}_{i}.png')
            n += 1
    return frames, n


def sheet(frames, scale=4, bg=(24, 24, 28, 255)):
    rows = [frames[a] for a in A.ACTIONS]
    w = max(len(r) for r in rows)
    img = Image.new('RGBA', (32 * w, 32 * len(rows)), bg)
    for j, row in enumerate(rows):
        for i, fr in enumerate(row):
            img.alpha_composite(fr, (i * 32, j * 32))
    return img.resize((img.width * scale, img.height * scale), Image.NEAREST)


def contact_sheet(thumbs, cols=9, scale=3):
    rows = (len(thumbs) + cols - 1) // cols
    cell = 32 * scale
    img = Image.new('RGBA', (cols * cell, rows * cell), (24, 24, 28, 255))
    for k, th in enumerate(thumbs):
        big = th.resize((cell, cell), Image.NEAREST)
        img.alpha_composite(big, ((k % cols) * cell, (k // cols) * cell))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', action='store_true',
                    help='nao escreve em assets/, so gera as folhas de conferencia')
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)
    out_dir = OUT

    total = 0
    thumbs = []

    if args.preview:
        base = A.render_all(None)
    else:
        base, n = write_set('goblin_', None, out_dir)
        total += n
    sheet(base).save(PREVIEW / 'base.png')
    thumbs.append(base['idle'][0])

    for vid in V.ORDER:
        spec = V.build(vid)
        if args.preview:
            frames = A.render_all(spec)
        else:
            frames, n = write_set(f'variant_{vid}_', spec, out_dir)
            total += n
        thumbs.append(frames['idle'][0])

    contact_sheet(thumbs).save(PREVIEW / 'variacoes.png')
    print(f'{total} quadros escritos em {out_dir.relative_to(ROOT)}')
    print(f'previews em {PREVIEW.relative_to(ROOT)}/base.png e /variacoes.png')


if __name__ == '__main__':
    main()
