#!/usr/bin/env python3
"""aprovacao.py — folha única de aprovação de um lote low-poly.

Monta, em uma imagem só:
  1. os renders originais da IA (fundo magenta);
  2. ANTES x DEPOIS no tamanho nativo do jogo, com goblin para escala;
  3. uma cena ampliada (grama do jogo, prédios + nós + goblins) lado a lado.

Uso: python3 tools/aprovacao.py LOTE [ids...]
Ex.: python3 tools/aprovacao.py 01 house ferraria node_tree node_rock
"""
import os
import random
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'raw')
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')

GRASS = (90, 164, 99, 255)
PANEL = (74, 138, 82, 255)
INK = (247, 242, 220, 255)
W, H = 640, 360

# id do candidato -> (sprite atual, tamanho nativo no jogo)
ASSETS = {
    'house':     ('assets/sprites/buildings/building_house_1.png', 64),
    'ferraria':  ('assets/sprites/buildings/building_ferraria_1.png', 64),
    'node_tree': ('assets/sprites/nodes/node_tree_0.png', 48),
    'node_rock': ('assets/sprites/nodes/node_rock_0.png', 48),
}
# tamanho nativo dos sprites que ainda não têm versão low-poly (para a cena)
NATIVE = {p: n for p, n in ASSETS.values()}
GOBLIN = os.path.join(ROOT, 'assets', 'sprites', 'goblins', 'variant_01_dente_dourado_idle_0.png')


def load(path, native):
    img = Image.open(os.path.join(ROOT, path)).convert('RGBA')
    return img if img.size == (native, native) else img.resize((native, native), Image.LANCZOS)


def grass(w, h):
    img = Image.new('RGBA', (w, h), GRASS)
    px = img.load()
    rnd = random.Random(7)
    for _ in range(w * h // 40):
        x, y = rnd.randrange(w), rnd.randrange(h)
        px[x, y] = rnd.choice([(82, 153, 92, 255), (98, 172, 106, 255), (120, 186, 120, 255)])
    for _ in range(max(8, w * h // 3000)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        px[x, y] = rnd.choice([(232, 106, 106, 255), (232, 208, 106, 255), (217, 138, 232, 255)])
    return img


def scene(x, y, w, h, entries, goblins):
    """Recorte de cena com os sprites ancorados pela base, como no jogo."""
    img = grass(w, h)
    for path, gx, gy, native in entries:
        spr = load(path, native)
        img.alpha_composite(spr, (int(gx - spr.width / 2), int(gy - spr.height)))
    gob = Image.open(GOBLIN).convert('RGBA')
    for gx, gy in goblins:
        img.alpha_composite(gob, (gx, gy - 32))
    return img.crop((x, y, x + w, y + h))


def strip(ids, zoom=2):
    """Cena ANTES (pixel) x DEPOIS (low-poly), ambas ampliadas."""
    old_entries, new_entries = [], []
    spots = [(70, 120), (170, 118), (268, 122), (330, 132), (120, 250), (235, 240)]
    for i, name in enumerate(ids):
        if i >= len(spots):
            break
        path, native = ASSETS[name]
        x, y = spots[i]
        old_entries.append((path, x, y, native))
        new_entries.append((f'art-source/lowpoly-village/candidates/{name}.png', x, y, native))
    gobs = [(42, 168), (215, 172), (300, 188), (150, 268)]
    a = scene(0, 40, 380, 268, old_entries, gobs)
    b = scene(0, 40, 380, 268, new_entries, gobs)
    a = a.resize((a.width * zoom, a.height * zoom), Image.NEAREST)
    b = b.resize((b.width * zoom, b.height * zoom), Image.NEAREST)
    out = Image.new('RGBA', (a.width + b.width + 12, a.height), GRASS)
    out.alpha_composite(a, (0, 0))
    out.alpha_composite(b, (a.width + 12, 0))
    return out


def main():
    args = sys.argv[1:]
    if not args:
        print('uso: python3 tools/aprovacao.py LOTE [ids...]')
        return
    lote, ids = args[0], [a for a in args[1:] if a in ASSETS] or list(ASSETS)

    # ---- linha 1: originais da IA -------------------------------------
    thumbs = []
    for name in ids:
        src = os.path.join(RAW, name + '.png')
        if not os.path.exists(src):
            continue
        img = Image.open(src).convert('RGB')
        img.thumbnail((220, 220), Image.LANCZOS)
        thumbs.append(img)

    # ---- linha 2: antes x depois, tamanho nativo ----------------------
    scale, cell, pad, label = 5, 64 * 5, 14, 40
    cols = len(ids)
    row2 = Image.new('RGBA', (pad + (cell + pad) * cols, label + cell + label + cell + pad), GRASS)
    d = ImageDraw.Draw(row2)
    d.text((pad, 4), 'ANTES (pixel art, no tamanho do jogo)', fill=INK)
    for i, name in enumerate(ids):
        cx = pad + i * (cell + pad)
        d.text((cx, 20), f'{i + 1}. {name}', fill=INK)
        old = load(ASSETS[name][0], ASSETS[name][1])
        big = old.resize((old.width * scale, old.height * scale), Image.NEAREST)
        row2.alpha_composite(big, (cx + (cell - big.width) // 2, label + (cell - big.height) // 2))
    y = label + cell + label
    d.text((pad, y - 18), 'DEPOIS (low-poly IA, no tamanho do jogo, com goblin para escala)', fill=INK)
    gob = Image.open(GOBLIN).convert('RGBA')
    for i, name in enumerate(ids):
        cx = pad + i * (cell + pad)
        d.rectangle([cx, y, cx + cell, y + cell], fill=PANEL)
        p = os.path.join(CAND, name + '.png')
        if os.path.exists(p):
            spr = Image.open(p).convert('RGBA')
            big = spr.resize((spr.width * scale, spr.height * scale), Image.NEAREST)
            row2.alpha_composite(big, (cx + (cell - big.width) // 2, y + (cell - big.height) // 2))
        big = gob.resize((gob.width * scale, gob.height * scale), Image.NEAREST)
        row2.alpha_composite(big, (cx + 4, y + cell - big.height + 4))

    # ---- linha 3: cena -------------------------------------------------
    row3 = strip(ids)
    d3 = ImageDraw.Draw(row3)
    header = Image.new('RGBA', (row3.width, 22), GRASS)
    dh = ImageDraw.Draw(header)
    dh.text((4, 4), 'NA CENA (640x360, ampliado x2)   —   esquerda: arte atual        direita: low-poly',
            fill=INK)
    row3.paste(header, (0, 0))

    # ---- montagem final -----------------------------------------------
    thumb_h = max((t.height for t in thumbs), default=0) + 24
    total_w = max(row2.width, row3.width, sum(t.width + 12 for t in thumbs) + 12)
    footer_h = 24
    sheet = Image.new('RGBA', (total_w, thumb_h + row2.height + row3.height + 20 + footer_h), GRASS)
    ds = ImageDraw.Draw(sheet)
    ds.text((4, 4), f'LOTE {lote} — renders originais da IA (fundo magenta)', fill=INK)
    x = 12
    for t in thumbs:
        sheet.paste(t, (x, 20))
        x += t.width + 12
    sheet.alpha_composite(row2, (0, thumb_h))
    sheet.alpha_composite(row3, (0, thumb_h + row2.height + 8))
    ds.text((4, thumb_h + row2.height + 8 + row3.height + 6),
            'STATUS: aguardando sua aprovação. Nada foi publicado no jogo ainda.',
            fill=INK)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f'aprovacao-{lote}.png')
    sheet.convert('RGB').save(path)
    print(os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
