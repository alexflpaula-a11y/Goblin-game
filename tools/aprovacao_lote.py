#!/usr/bin/env python3
"""aprovacao_lote.py — folha de aprovação de um lote de prédios (antes x depois).

Para cada id monta um par lado a lado: a pixel art atual (esquerda) e o
render low-poly novo no tamanho nativo do jogo (direita), ampliado x4.
Abaixo de cada par fica a silhueta nova em 64x64 sobre a grama, para
conferir como ela aparece no meio de outras construções.

Uso: python3 tools/aprovacao_lote.py 02 altar armazem bar ...
"""
import os
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
RAW = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'raw')
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')

GRASS = (90, 164, 99, 255)
PANEL = (74, 138, 82, 255)
INK = (247, 242, 220, 255)

S = 4                      # ampliação
SPR = 64 * S               # sprite ampliado
PAD = 14
LABEL = 20
ROW_H = SPR + LABEL + PAD + 64 + PAD   # par + miniatura 1:1
COL_W = SPR * 2 + PAD * 3

# id do candidato -> sprite atual no jogo
CURRENT = {
    'house': 'building_house_1', 'ferraria': 'building_ferraria_1',
    'altar': 'building_altar_1', 'armazem': 'building_armazem_1',
    'bar': 'building_bazar_1', 'cozinha': 'building_cozinha_1',
    'estabulo': 'building_estabulo_1', 'fazenda': 'building_fazenda_1',
    'mercado': 'building_mercado_1', 'porto': 'building_porto_1',
    'quartel': 'building_quartel_1', 'questboard': 'building_questboard_1',
}


def main():
    args = sys.argv[1:]
    if not args:
        print('uso: python3 tools/aprovacao_lote.py LOTE ids...')
        return
    lote, ids = args[0], args[1:]
    cols = 2
    rows = (len(ids) + cols - 1) // cols
    w = PAD + cols * (COL_W + PAD)
    h = 54 + rows * ROW_H + 30
    sheet = Image.new('RGBA', (w, h), GRASS)
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 8), f'LOTE {lote} — pixel art atual  x  low-poly novo (64x64, ampliado x4)', fill=INK)
    d.text((PAD, 24), 'Cada par: esquerda = arte no jogo hoje, direita = render novo. Abaixo, o novo em tamanho real.', fill=INK)

    for i, name in enumerate(ids):
        col, row = i % cols, i // cols
        x = PAD + col * (COL_W + PAD)
        y = 54 + row * ROW_H
        d.text((x, y), f'{i + 1}. {name}', fill=INK)
        old_path = os.path.join(ROOT, 'assets', 'sprites', 'buildings', CURRENT[name] + '.png')
        new_path = os.path.join(CAND, name + '.png')
        old = Image.open(old_path).convert('RGBA')
        new = Image.open(new_path).convert('RGBA')
        oy = y + LABEL
        px_l, px_r = x, x + SPR + PAD
        d.rectangle([px_l, oy, px_l + SPR - 1, oy + SPR - 1], fill=PANEL)
        d.rectangle([px_r, oy, px_r + SPR - 1, oy + SPR - 1], fill=PANEL)
        sheet.alpha_composite(old.resize((SPR, SPR), Image.NEAREST), (px_l, oy))
        sheet.alpha_composite(new.resize((SPR, SPR), Image.NEAREST), (px_r, oy))
        # miniatura 1:1 sobre a grama, como aparece na vila
        ty = oy + SPR + PAD // 2
        d.rectangle([px_r, ty, px_r + 64 - 1, ty + 64 - 1], fill=PANEL)
        sheet.alpha_composite(new, (px_r, ty))

    d.text((PAD, h - 22),
           'Status: aguardando sua aprovação. Nada foi publicado no jogo ainda.',
           fill=INK)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f'aprovacao-{lote}.png')
    sheet.convert('RGB').save(path)
    print(os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
