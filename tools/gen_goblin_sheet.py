#!/usr/bin/env python3
"""
Folha de conferencia do goblin: animacoes, variacoes e equipamentos num PNG.

    python3 tools/gen_goblin_sheet.py
    -> art-source/goblins-v2/conferencia.png
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image, ImageDraw     # noqa: E402

import goblin_anim as A              # noqa: E402
import goblin_gear as G              # noqa: E402
import goblin_variations as V        # noqa: E402
import gen_gear_v2 as GG             # noqa: E402
import goblin_rig as R               # noqa: E402

CELL = R.SIZE
COLS = 17
SCALE = 4
BG = (22, 22, 26, 255)
INK = (168, 172, 182)
TITLE = (236, 232, 214)


def main():
    base = A.render_all(None)
    gear = {p: GG.frames_with(layers)['idle'][0]
            for p, (layers, _) in G.PIECES.items()}
    var = [(vid, A.render_action('idle', V.build(vid))[0]) for vid in V.ORDER]

    var_rows = (len(var) + COLS - 1) // COLS
    gear_rows = (len(gear) + 1 + COLS - 1) // COLS
    head = 16
    h = (head + CELL * 5) + (head + CELL * var_rows) + (head + CELL * gear_rows) + 8
    img = Image.new('RGBA', (CELL * COLS, h), BG)

    y = 0
    d = ImageDraw.Draw(img)

    d.text((2, y + 4), 'animacoes  idle 5 / walk 8 / attack 17 / hurt 17 / death 15',
           fill=TITLE)
    y += head
    for action in A.ACTIONS:
        for i, f in enumerate(base[action]):
            img.alpha_composite(f, (i * CELL, y))
        d.text((CELL * COLS - 44, y + 12), action[:5], fill=INK)
        y += CELL

    d.text((2, y + 4), 'as 45 variacoes (idle 0)', fill=TITLE)
    y += head
    for k, (_vid, f) in enumerate(var):
        img.alpha_composite(f, ((k % COLS) * CELL, y + (k // COLS) * CELL))
    y += CELL * var_rows

    d.text((2, y + 4), 'equipamentos: ' + ' '.join(gear), fill=TITLE)
    y += head
    cells = [base['idle'][0]] + list(gear.values())
    for k, f in enumerate(cells):
        img.alpha_composite(f, ((k % COLS) * CELL, y + (k // COLS) * CELL))

    out = img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)
    dst = ROOT / 'art-source' / 'goblins-v2' / 'conferencia.png'
    out.save(dst)
    print('OK ->', dst.relative_to(ROOT), out.size)


if __name__ == '__main__':
    main()
