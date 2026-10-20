#!/usr/bin/env python3
"""validar_encaixe.py — folha visual de encaixe no chão.

Para cada estrutura desenha, lado a lado, a arte antiga e a nova no tamanho
nativo, com a LINHA DO CHÃO marcada. Se a base sair da linha, o sprite flutua
ou afunda no jogo. Também mostra os nós (árvore/pedra) na âncora deles.

Uso: python3 tools/validar_encaixe.py
"""
import os
import subprocess
from io import BytesIO

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview', 'validacao-encaixe.png')
BASE_REV = 'e565e0b'
Z = 3
PAD = 12
LABEL = 22

BUILDINGS = [
    ('building_house_1', 64), ('building_ferraria_1', 64), ('building_altar_1', 64),
    ('building_armazem_1', 64), ('building_bazar_1', 64), ('building_cozinha_1', 64),
    ('building_estabulo_1', 64), ('building_fazenda_1', 64), ('building_mercado_1', 64),
    ('building_porto_1', 64), ('building_quartel_1', 64), ('building_questboard_1', 64),
    ('node_tree_0', 48), ('node_rock_0', 48),
]


def old_sprite(rel):
    data = subprocess.check_output(['git', 'show', f'{BASE_REV}:assets/sprites/{rel}'], cwd=ROOT)
    return Image.open(BytesIO(data)).convert('RGBA')


def cell(sheet, d, img, x, y, native, anchor_gap, title, ground):
    """Desenha o sprite e a linha do chão na posição real do jogo."""
    w = h = native * Z
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=(60, 90, 65, 255))
    big = img.resize((w, h), Image.NEAREST)
    sheet.alpha_composite(big, (x, y))
    # linha do chão: onde a base do conteúdo deve cair
    gy = y + h - anchor_gap * Z
    d.line([x - 4, gy, x + w + 4, gy], fill=(255, 60, 60, 255), width=1)
    d.text((x, y - 14), title, fill=(250, 245, 220, 255))
    if ground:
        pass


def main():
    cols = 4
    rows = (len(BUILDINGS) + cols - 1) // cols
    cw = 64 * Z + PAD * 2
    ch = 64 * Z + LABEL + PAD + 26
    sheet = Image.new('RGBA', (cols * cw + PAD, 46 + rows * ch + 10), (90, 164, 99, 255))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 8), 'ENCAIXE NO CHÃO — arte antiga x nova, tamanho nativo, ampliado x3', fill=(250, 245, 220, 255))
    d.text((PAD, 24), 'Linha vermelha = base do conteúdo da ARTE ANTIGA. O sprite novo precisa apoiar na mesma linha.', fill=(250, 245, 220, 255))

    for i, (name, native) in enumerate(BUILDINGS):
        rel = ('nodes' if name.startswith('node_') else 'buildings') + '/' + name + '.png'
        old = old_sprite(rel)
        new = Image.open(os.path.join(ROOT, 'assets', 'sprites', rel)).convert('RGBA')
        # folga inferior da arte antiga (a referência)
        bb = old.split()[3].getbbox()
        gap_old = native - bb[3]
        col, row = i % cols, i // cols
        x = PAD + col * cw
        y = 46 + row * ch + LABEL
        # lado a lado dentro da célula: antigo em cima, novo embaixo não cabe;
        # então antigo à esquerda e novo à direita, ambos na mesma linha
        half = (64 * Z) // 2
        shrink = 0.5
        for j, (img, tag) in enumerate(((old, 'antigo'), (new, 'novo'))):
            im = img.resize((int(native * Z * shrink), int(native * Z * shrink)), Image.NEAREST)
            px = x + j * (half + 4)
            py = y + (64 * Z) - im.height - int(gap_old * Z * shrink)
            d.rectangle([px, y, px + half - 1, y + 64 * Z - 1], outline=(60, 90, 65, 255))
            sheet.alpha_composite(im, (px, py))
            gy = y + 64 * Z - int(gap_old * Z * shrink)
            d.line([px - 2, gy, px + half + 2, gy], fill=(255, 60, 60, 255), width=1)
            d.text((px + 2, y + 2), tag, fill=(240, 235, 210, 255))
        d.text((x, y - 16), name.replace('building_', '').replace('_1', ''), fill=(250, 245, 220, 255))

    sheet.convert('RGB').save(OUT)
    print(os.path.relpath(OUT, ROOT))


if __name__ == '__main__':
    main()
