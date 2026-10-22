#!/usr/bin/env python3
"""comparativo.py — folha de aprovação: ANTES (pixel art) x DEPOIS (low-poly).

Desenha cada estrutura no tamanho real do jogo (64x64) sobre a grama, com um
goblin idle ao lado para escala, e amplia x5 sem interpolação.

Uso: python3 tools/comparativo.py [house ferraria node_tree node_rock]
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')

GRASS = (90, 164, 99, 255)
PANEL = (74, 138, 82, 255)
INK = (245, 240, 220, 255)

# id do candidato -> sprite atual no jogo
PAIRS = {
    'house':     'assets/sprites/buildings/building_house_1.png',
    'ferraria':  'assets/sprites/buildings/building_ferraria_1.png',
    'node_tree': 'assets/sprites/nodes/node_tree_0.png',
    'node_rock': 'assets/sprites/nodes/node_rock_0.png',
}
GOBLIN = os.path.join(ROOT, 'assets', 'sprites', 'goblins', 'variant_01_dente_dourado_idle_0.png')

SCALE = 5
CELL = 64 * SCALE
PAD = 18
LABEL_H = 26


def paste_fit(sheet, img, cx, cy, native=64):
    """Cola o sprite no tamanho NATIVO do jogo e amplia x5 (NEAREST)."""
    fit = img.resize((native, native), Image.LANCZOS) if img.size != (native, native) else img
    big = fit.resize((fit.width * SCALE, fit.height * SCALE), Image.NEAREST)
    sheet.alpha_composite(big, (cx + (CELL - big.width) // 2, cy + (CELL - big.height) // 2))


def main():
    only = sys.argv[1:] or list(PAIRS)
    w = (CELL + PAD) * 4 + PAD
    h = (LABEL_H + CELL + PAD) + (LABEL_H + CELL + PAD * 2) + 44
    sheet = Image.new('RGBA', (w, h), GRASS)
    d = ImageDraw.Draw(sheet)

    y0 = LABEL_H
    header = ['ANTES (pixel art)'] * 1
    for i, name in enumerate(only):
        cx = PAD + i * (CELL + PAD)
        d.text((cx + 4, 6), f'{i + 1}. {name}', fill=INK)
        old = Image.open(os.path.join(ROOT, PAIRS[name])).convert('RGBA')
        paste_fit(sheet, old, cx, y0)

    y1 = y0 + CELL + PAD + LABEL_H
    d.text((4, y0 + CELL + PAD + 6), 'DEPOIS (low-poly IA)  +  goblin para escala', fill=INK)
    gob = Image.open(GOBLIN).convert('RGBA')
    for i, name in enumerate(only):
        cx = PAD + i * (CELL + PAD)
        d.rectangle([cx, y1, cx + CELL, y1 + CELL], fill=PANEL)
        p = os.path.join(CAND, name + '.png')
        if os.path.exists(p):
            native = 48 if name.startswith('node_') else 64
        paste_fit(sheet, Image.open(p).convert('RGBA'), cx, y1, native)
        # goblin no canto, mesma escala (32 px -> 160 px)
        big = gob.resize((gob.width * SCALE, gob.height * SCALE), Image.NEAREST)
        sheet.alpha_composite(big, (cx + 4, y1 + CELL - big.height + 6))

    footer = 'Tamanho real: 64x64 (prédios) e 32x32 (goblin) - ampliado x5 para conferencia'
    d.text((4, h - 24), footer, fill=INK)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'antes-depois.png')
    sheet.save(path)
    print(os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
