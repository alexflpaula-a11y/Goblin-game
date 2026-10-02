#!/usr/bin/env python3
"""
Gera os sprites de equipamento do goblin v2.

Para cada peca sao escritos:

  assets/sprites/goblin-gear-overlays/overlay_<pref>_<acao>_<n>.png
      so os pixels que a peca ACRESCENTA ao goblin base (e o que
      js/gear.js empilha para montar qualquer combinacao).

  assets/sprites/<pasta>/<pref>_<acao>_<n>.png
      o goblin ja vestido, usado como atalho quando a peca e unica
      (av_* e ferro_pei).

O overlay nunca e desenhado a mao: ele e a DIFERENCA entre o quadro com a
peca e o mesmo quadro sem ela, entao o encaixe e exato por construcao.

    python3 tools/gen_gear_v2.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

from PIL import Image                 # noqa: E402

import goblin_anim as A               # noqa: E402
import goblin_gear as G               # noqa: E402
import goblin_rig as R                # noqa: E402

OVL = ROOT / 'assets' / 'sprites' / 'goblin-gear-overlays'
SPR = ROOT / 'assets' / 'sprites'
PREVIEW = ROOT / 'art-source' / 'goblins-v2'


def frames_with(layers):
    """Renderiza as 62 poses com as camadas de equipamento aplicadas."""
    out = {}
    for action in A.ACTIONS:
        imgs = []
        for pose in A.POSES[action]():
            gear = G.resolve(layers, pose.get('_sword', 'down'))
            buf = R.compose(pose, gear=gear)
            if pose.get('_flash'):
                A._flash(buf)
            img = R.to_image(buf)
            if action == 'death':
                k = pose['_dead']
                if k >= A.DEATH_LYING:
                    img = A._lay_down(img, A.DEATH_LIFT[k])
                img = A._fade(img, A.DEATH_ALPHA[k])
            imgs.append(img)
        out[action] = imgs
    return out


def diff(dressed, naked):
    """Mantem apenas os pixels em que a peca mudou o goblin."""
    out = Image.new('RGBA', dressed.size, (0, 0, 0, 0))
    dp, np_, op = dressed.load(), naked.load(), out.load()
    for y in range(dressed.height):
        for x in range(dressed.width):
            if dp[x, y] != np_[x, y]:
                op[x, y] = dp[x, y]
    return out


def icon(img, box, size=16):
    x0, y0, x1, y1 = box
    crop = img.crop((x0, y0, x1 + 1, y1 + 1))
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    w, h = crop.size
    scale = min(size / w, size / h, 2)
    if scale < 1:
        crop = crop.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.NEAREST)
    out.alpha_composite(crop, ((size - crop.width) // 2, (size - crop.height) // 2))
    return out


def main():
    OVL.mkdir(parents=True, exist_ok=True)
    base = A.render_all(None)

    written = 0
    dressed_cache = {}
    for prefix, (layers, folder) in G.PIECES.items():
        dressed = frames_with(layers)
        dressed_cache[prefix] = dressed
        for action in A.ACTIONS:
            for i, img in enumerate(dressed[action]):
                d = diff(img, base[action][i])
                R.save_png(d, OVL / f'overlay_{prefix}_{action}_{i}.png')
                written += 1
                if folder:
                    target = SPR / folder
                    target.mkdir(parents=True, exist_ok=True)
                    R.save_png(img, target / f'{prefix}_{action}_{i}.png')
                    written += 1
        print(f'  {prefix:12s} ok')

    for icon_id, (prefix, box) in G.ICONS.items():
        src = dressed_cache[prefix]['idle'][0]
        R.save_png(icon(src, box), SPR / 'avaritia' / f'{icon_id}.png')
        written += 1

    # Folha de conferencia: goblin base + cada peca, em idle.
    order = ['', *G.PIECES]
    sheet = Image.new('RGBA', (32 * len(order), 32), (24, 24, 28, 255))
    for i, prefix in enumerate(order):
        img = base['idle'][0] if not prefix else dressed_cache[prefix]['idle'][0]
        sheet.alpha_composite(img, (i * 32, 0))
    sheet.resize((sheet.width * 6, sheet.height * 6), Image.NEAREST) \
         .save(PREVIEW / 'equipamentos.png')

    print(f'{written} arquivos escritos')


if __name__ == '__main__':
    main()
