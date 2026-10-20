#!/usr/bin/env python3
"""cena_vila.py — simulação de cena com os sprites REAIS, no tamanho do jogo.

Não é screenshot do jogo: é uma composição sobre a cor da grama do world.js
para conferir coerência entre as estruturas publicadas, todas em 1:1 na
resolução lógica 640x360 (ampliada x2 no fim).
"""
import os
import random

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')
GRASS = (90, 164, 99, 255)
ZOOM = 2
W, H = 640, 360


def grass():
    img = Image.new('RGBA', (W, H), GRASS)
    px = img.load()
    rnd = random.Random(11)
    for _ in range(W * H // 45):
        x, y = rnd.randrange(W), rnd.randrange(H)
        px[x, y] = rnd.choice([(82, 153, 92, 255), (98, 172, 106, 255), (120, 186, 120, 255)])
    return img


def main():
    img = grass()
    B = lambda n: os.path.join(ROOT, 'assets', 'sprites', 'buildings', n + '.png')
    N = lambda n: os.path.join(ROOT, 'assets', 'sprites', 'nodes', n + '.png')
    G = lambda n: os.path.join(ROOT, 'assets', 'sprites', 'goblins', n + '.png')

    def put(path, x, y, w=64, h=64):
        spr = Image.open(path).convert('RGBA')
        if spr.size != (w, h):
            spr = spr.resize((w, h), Image.LANCZOS)
        img.alpha_composite(spr, (int(x - w / 2), int(y - h)))

    # fileira de trás
    back = ['building_house_1', 'building_armazem_1', 'building_fazenda_1',
            'building_serraria_1', 'building_quartel_1', 'building_house_1']
    for i, b in enumerate(back):
        put(B(b), 70 + i * 92, 150)
    # fileira da frente
    front = ['building_ferraria_1', 'building_cozinha_1', 'building_mercado_1',
             'building_bazar_1', 'building_estabulo_1']
    for i, b in enumerate(front):
        put(B(b), 118 + i * 100, 268)
    put(B('building_questboard_1'), 34, 262)
    put(B('building_altar_1'), 600, 262)
    # recursos
    for (x, y) in [(30, 190), (620, 176), (250, 336), (520, 340)]:
        put(N('node_tree_0'), x, y, 48, 48)
    for (x, y) in [(96, 336), (410, 200)]:
        put(N('node_rock_0'), x, y, 48, 48)
    # goblins para escala
    for (x, y) in [(150, 300), (330, 300), (470, 296), (560, 236)]:
        put(G('variant_01_dente_dourado_idle_0'), x, y, 32, 32)

    big = img.resize((W * ZOOM, H * ZOOM), Image.NEAREST)
    d = ImageDraw.Draw(big)
    d.rectangle([0, 0, big.width, 18], fill=(40, 60, 45, 255))
    d.text((6, 4), 'SIMULAÇÃO (não é screenshot): sprites reais em 1:1 sobre a cor da grama, ampliado x2', fill=(240, 240, 220, 255))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, 'cena-vila.png')
    big.convert('RGB').save(path)
    print(os.path.relpath(path, ROOT))


if __name__ == '__main__':
    main()
