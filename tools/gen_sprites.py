#!/usr/bin/env python3
"""
gen_sprites.py — Pixel art 32x32 das estruturas e itens que faltavam.

Segue o estilo da arte que já existia no projeto (casa, painel de missões):
  • 32x32, fundo transparente, contorno escuro automático
  • paleta reduzida de madeira/pedra/verde
  • "linha do chão" na altura y=28 (o mundo desenha o sprite 2x, ancorado pelos pés)

Uso:  python3 tools/gen_sprites.py
"""
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD_DIR = os.path.join(ROOT, 'assets/sprites/buildings')
ITEM_DIR = os.path.join(ROOT, 'assets/sprites/items')

# ---------------- paleta (mesma da arte existente) ----------------
OUT = (34, 26, 18)
WOOD = (169, 113, 61)
WOOD_D = (110, 70, 38)
WOOD_X = (74, 48, 24)
WOOD_L = (200, 150, 95)
GRN = (62, 142, 78)
GRN_L = (79, 165, 98)
GRN_D = (47, 107, 60)
STRAW = (232, 210, 147)
STRAW_D = (198, 172, 110)
GOLD = (232, 178, 58)
STONE = (125, 130, 145)
STONE_L = (154, 160, 173)
STONE_D = (106, 111, 125)
RED = (184, 69, 46)
RED_D = (140, 47, 31)
FIRE = (232, 120, 40)
FIRE_L = (250, 200, 90)
WATER = (29, 92, 143)
WATER_L = (58, 130, 180)
PURPLE = (167, 139, 250)
PURPLE_D = (110, 85, 190)
DARK = (24, 18, 14)
BONE = (230, 225, 210)
SMOKE = (176, 176, 186)

S = 32


# ---------------- primitivas ----------------
def blank():
    return [[None] * S for _ in range(S)]


def px(g, x, y, c):
    if 0 <= x < S and 0 <= y < S:
        g[y][x] = c


def rect(g, x0, y0, x1, y1, c):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(g, x, y, c)


def hline(g, x0, x1, y, c):
    rect(g, x0, y, x1, y, c)


def vline(g, x, y0, y1, c):
    rect(g, x, y0, x, y1, c)


def tri_roof(g, cx, top_y, half_w, height, c, c_shade=None):
    """Telhado triangular: bico em (cx, top_y), base larga embaixo."""
    for i in range(height):
        y = top_y + i
        w = int(half_w * (i + 1) / height)
        rect(g, cx - w, y, cx + w, y, c)
        if c_shade and i > height * 0.55:
            rect(g, cx + max(0, w - 2), y, cx + w, y, c_shade)


def trapez_roof(g, y0, y1, x_top0, x_top1, x_bot0, x_bot1, c, c_shade=None):
    """Telhado trapezoidal, interpolando as bordas de cima para baixo."""
    n = y1 - y0
    for i in range(n + 1):
        t = i / max(1, n)
        a = round(x_top0 + (x_bot0 - x_top0) * t)
        b = round(x_top1 + (x_bot1 - x_top1) * t)
        rect(g, a, y0 + i, b, y0 + i, c)
        if c_shade:
            rect(g, b - 1, y0 + i, b, y0 + i, c_shade)


# Máscaras feitas à mão para raios pequenos: a fórmula do círculo
# em 1–2 px vira uma cruz feia, então desenhamos o blob na unha.
SMALL_DISC = {
    1: [(0, 0), (1, 0), (0, 1), (1, 1)],
    2: [(x, y) for x in range(-1, 3) for y in range(-1, 3)
        if not (x in (-1, 2) and y in (-1, 2))],
}


def disc(g, cx, cy, r, c):
    if r in SMALL_DISC:
        for dx, dy in SMALL_DISC[r]:
            px(g, cx + dx, cy + dy, c)
        return
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + 1:
                px(g, x, y, c)


def ring(g, cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            d = (x - cx) ** 2 + (y - cy) ** 2
            if (r - 1) ** 2 < d <= r * r:
                px(g, x, y, c)


def outline(g, c=OUT):
    """Contorno escuro em volta de tudo que foi desenhado."""
    src = [row[:] for row in g]
    for y in range(S):
        for x in range(S):
            if src[y][x] is not None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < S and 0 <= ny < S and src[ny][nx] is not None and src[ny][nx] != c:
                    g[y][x] = c
                    break


def save(g, path):
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    pxs = im.load()
    for y in range(S):
        for x in range(S):
            c = g[y][x]
            if c is not None:
                pxs[x, y] = (c[0], c[1], c[2], 255)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    return path


# ---------------- estruturas ----------------
def serraria():
    """Serraria: galpão de tábuas, serra circular e toras empilhadas."""
    g = blank()
    trapez_roof(g, 6, 12, 12, 19, 5, 26, WOOD_X, WOOD_D)   # telhado de tábuas
    rect(g, 7, 13, 24, 27, WOOD)                            # parede
    for x in range(7, 25, 4):                               # ripas verticais
        vline(g, x, 13, 27, WOOD_D)
    hline(g, 7, 24, 20, WOOD_D)
    # serra circular
    disc(g, 12, 19, 4, STONE_L)
    ring(g, 12, 19, 4, STONE_D)
    for dx, dy in ((0, -5), (0, 5), (-5, 0), (5, 0), (-4, -4), (4, 4), (-4, 4), (4, -4)):
        px(g, 12 + dx, 19 + dy, STONE_D)
    px(g, 12, 19, WOOD_X)
    # toras empilhadas à direita
    for i, (bx, by) in enumerate(((19, 25), (23, 25), (21, 22))):
        disc(g, bx, by, 2, WOOD_D)
        px(g, bx, by, WOOD_L)
    hline(g, 6, 25, 28, WOOD_X)                             # base
    outline(g)
    return g


def fazenda():
    """Fazenda: celeiro pequeno de telhado de palha e canteiros plantados."""
    g = blank()
    tri_roof(g, 13, 5, 8, 7, STRAW, STRAW_D)
    rect(g, 6, 12, 20, 24, WOOD)
    vline(g, 10, 12, 24, WOOD_D)
    vline(g, 16, 12, 24, WOOD_D)
    rect(g, 11, 17, 15, 24, WOOD_X)                         # porta
    px(g, 14, 21, GOLD)
    # canteiros à direita: leiras de terra com brotos
    rect(g, 22, 22, 29, 27, WOOD_D)
    for y in (23, 25, 27):
        hline(g, 22, 29, y, WOOD_X)
    for bx in (24, 27):
        vline(g, bx, 18, 21, GRN_D)
        px(g, bx - 1, 19, GRN)
        px(g, bx + 1, 20, GRN)
        px(g, bx, 17, GRN_L)
    hline(g, 5, 29, 28, WOOD_X)
    outline(g)
    return g


def cozinha():
    """Cozinha: base de pedra, chaminé fumegando e caldeirão."""
    g = blank()
    trapez_roof(g, 6, 11, 11, 20, 5, 26, RED_D, RED)
    rect(g, 7, 12, 24, 27, STONE)
    for y in range(13, 28, 3):                              # fiadas de pedra
        hline(g, 7, 24, y, STONE_D)
    rect(g, 20, 3, 23, 11, STONE_D)                         # chaminé
    rect(g, 20, 3, 23, 4, STONE_L)
    for i, (sx, sy, r) in enumerate(((21, 1, 1), (23, 0, 1))):  # fumaça
        disc(g, sx, sy, r, SMOKE)
    # janela quente
    rect(g, 9, 16, 13, 20, WOOD_X)
    rect(g, 10, 17, 12, 19, FIRE)
    px(g, 11, 18, FIRE_L)
    # caldeirão
    disc(g, 18, 23, 3, DARK)
    hline(g, 15, 21, 20, STONE_D)
    px(g, 17, 22, GRN_L)
    px(g, 19, 23, GRN_L)
    hline(g, 6, 25, 28, STONE_D)
    outline(g)
    return g


def mercado():
    """Mercado: barraca com toldo listrado, balcão e mercadorias."""
    g = blank()
    # toldo listrado
    for i, x in enumerate(range(4, 28, 3)):
        c = RED if i % 2 == 0 else STRAW
        rect(g, x, 8, x + 2, 13, c)
    hline(g, 4, 27, 13, WOOD_X)
    # postes
    vline(g, 5, 14, 27, WOOD_D)
    vline(g, 26, 14, 27, WOOD_D)
    # balcão
    rect(g, 6, 19, 25, 22, WOOD)
    hline(g, 6, 25, 22, WOOD_D)
    rect(g, 6, 23, 25, 27, WOOD_D)
    for x in range(8, 26, 4):                                # ripas do balcão
        vline(g, x, 23, 27, WOOD_X)
    # mercadorias sobre o balcão: saco, maçãs e moedas
    rect(g, 8, 16, 12, 19, STRAW)                            # saco de grãos
    hline(g, 8, 12, 16, STRAW_D)
    px(g, 10, 15, WOOD_D)
    disc(g, 16, 17, 1, RED)                                  # maçãs
    disc(g, 19, 17, 1, RED)
    px(g, 16, 15, GRN_D)
    rect(g, 22, 17, 24, 19, GOLD)                            # moedas
    hline(g, 22, 24, 17, FIRE_L)
    hline(g, 4, 27, 28, WOOD_X)
    outline(g)
    return g


def mina():
    """Mina: encosta de pedra com entrada escorada e vagonete."""
    g = blank()
    # morro
    for i, y in enumerate(range(8, 28)):
        w = 4 + i
        rect(g, 16 - w // 2 - 2, y, 16 + w // 2 + 2, y, STONE)
    for x, y in ((10, 14), (21, 17), (13, 22), (24, 23), (8, 20)):
        disc(g, x, y, 1, STONE_D)
    hline(g, 4, 28, 12, STONE_L)
    # entrada
    rect(g, 12, 18, 20, 27, DARK)
    for i in range(4):                                       # arco
        px(g, 12 + i, 17 - (1 if i > 1 else 0), DARK)
        px(g, 20 - i, 17 - (1 if i > 1 else 0), DARK)
    rect(g, 13, 16, 19, 17, DARK)
    # escoras de madeira
    vline(g, 11, 17, 27, WOOD_D)
    vline(g, 21, 17, 27, WOOD_D)
    rect(g, 10, 15, 22, 16, WOOD)
    # vagonete
    rect(g, 23, 24, 28, 26, WOOD_X)
    px(g, 24, 23, STONE_L)
    px(g, 26, 23, STONE_L)
    disc(g, 24, 27, 1, DARK)
    disc(g, 27, 27, 1, DARK)
    hline(g, 4, 29, 28, STONE_D)
    outline(g)
    return g


def estabulo():
    """Estábulo: celeiro largo com porta em arco e cerca."""
    g = blank()
    trapez_roof(g, 5, 11, 10, 21, 4, 27, RED_D, RED)
    hline(g, 4, 27, 11, WOOD_X)
    rect(g, 6, 12, 25, 27, WOOD)
    vline(g, 6, 12, 27, WOOD_D)
    vline(g, 25, 12, 27, WOOD_D)
    # porta em arco (celeiro)
    rect(g, 12, 17, 19, 27, WOOD_X)
    rect(g, 13, 15, 18, 16, WOOD_X)
    px(g, 12, 16, WOOD_X)
    px(g, 19, 16, WOOD_X)
    vline(g, 15, 17, 27, WOOD_D)                             # fresta central
    # feno na janelinha
    rect(g, 14, 12, 17, 14, STRAW)
    # cercas laterais
    for bx in (8, 23):
        vline(g, bx, 22, 27, WOOD_L)
    hline(g, 7, 9, 24, WOOD_L)
    hline(g, 22, 24, 24, WOOD_L)
    hline(g, 4, 27, 28, WOOD_X)
    outline(g)
    return g


def ferraria():
    """Ferraria: forja de pedra acesa, chaminé e bigorna."""
    g = blank()
    trapez_roof(g, 6, 11, 12, 20, 5, 26, WOOD_X, WOOD_D)
    rect(g, 7, 12, 24, 27, STONE)
    for y in range(14, 28, 3):
        hline(g, 7, 24, y, STONE_D)
    rect(g, 8, 2, 12, 11, STONE_D)                           # chaminé
    rect(g, 8, 2, 12, 3, STONE_L)
    disc(g, 10, 0, 1, FIRE)
    # boca da forja
    rect(g, 14, 17, 22, 24, DARK)
    rect(g, 15, 20, 21, 23, FIRE)
    rect(g, 16, 21, 20, 23, FIRE_L)
    # bigorna
    rect(g, 8, 22, 13, 24, STONE_L)
    rect(g, 9, 24, 12, 26, STONE_D)
    px(g, 8, 21, STONE_L)
    hline(g, 6, 25, 28, STONE_D)
    outline(g)
    return g


def altar():
    """Altar: pedras eretas, laje com runas e brilho mágico."""
    g = blank()
    # pilares
    for bx in (7, 22):
        rect(g, bx, 10, bx + 3, 27, STONE)
        rect(g, bx, 10, bx + 3, 11, STONE_L)
        px(g, bx + 1, 16, STONE_D)
        px(g, bx + 2, 21, STONE_D)
    # lintel
    rect(g, 6, 7, 26, 10, STONE_L)
    hline(g, 6, 26, 10, STONE_D)
    # laje central
    rect(g, 11, 20, 20, 24, STONE)
    rect(g, 10, 24, 21, 27, STONE_D)
    # runas brilhando
    for rx in (13, 16, 19):
        vline(g, rx, 21, 23, PURPLE)
        px(g, rx, 22, PURPLE)
    disc(g, 16, 15, 3, PURPLE_D)
    disc(g, 16, 15, 2, PURPLE)
    px(g, 16, 14, BONE)
    hline(g, 5, 27, 28, STONE_D)
    outline(g)
    return g


def bazar():
    """Bazar: tenda de pano listrado com tapete e mercadorias."""
    g = blank()
    tri_roof(g, 16, 4, 12, 9, PURPLE_D)
    for i in range(4, 13):                                   # listras do pano
        if i % 2 == 0:
            w = int(12 * (i - 3) / 9)
            rect(g, 16 - w, i, 16 - w + 1, i, PURPLE)
            rect(g, 16 + w - 1, i, 16 + w, i, PURPLE)
    px(g, 16, 3, GOLD)
    rect(g, 4, 13, 27, 14, WOOD_X)
    vline(g, 5, 15, 27, WOOD_D)
    vline(g, 26, 15, 27, WOOD_D)
    # cortina ao fundo
    rect(g, 8, 15, 23, 21, PURPLE_D)
    for x in range(9, 23, 3):
        vline(g, x, 15, 21, PURPLE)
    # tapete com mercadorias
    rect(g, 6, 22, 25, 26, RED_D)
    hline(g, 6, 25, 22, RED)
    disc(g, 11, 20, 2, GOLD)
    disc(g, 20, 20, 2, GRN_L)
    hline(g, 4, 27, 28, WOOD_X)
    outline(g)
    return g


def porto():
    """Porto: píer de tábuas sobre a água com poste e barquinho."""
    g = blank()
    rect(g, 0, 16, 31, 28, WATER)                            # água
    for y in (18, 22, 26):
        for x in range(0, 32, 5):
            hline(g, x, x + 2, y, WATER_L)
    # píer
    rect(g, 4, 17, 27, 21, WOOD)
    for x in range(5, 27, 4):
        vline(g, x, 17, 21, WOOD_D)
    hline(g, 4, 27, 21, WOOD_X)
    for bx in (7, 15, 23):                                   # estacas
        vline(g, bx, 22, 27, WOOD_X)
    # poste com lanterna
    vline(g, 25, 8, 17, WOOD_D)
    rect(g, 23, 6, 27, 9, WOOD_X)
    rect(g, 24, 7, 26, 8, GOLD)
    # barquinho
    rect(g, 7, 23, 17, 25, WOOD_D)
    rect(g, 8, 25, 16, 26, WOOD_X)
    vline(g, 12, 17, 22, WOOD_L)
    for i in range(4):                                       # vela
        hline(g, 13, 13 + i, 18 + i, BONE)
    outline(g)
    return g


def quartel():
    """Quartel: fortim de pedra com ameias, portão e bandeira."""
    g = blank()
    rect(g, 5, 10, 26, 27, STONE)
    for y in range(12, 28, 4):
        hline(g, 5, 26, y, STONE_D)
    for x in range(5, 27, 3):                                # fiada alternada
        px(g, x, 14, STONE_L)
        px(g, x + 1, 18, STONE_L)
    # ameias
    for x in range(5, 27, 5):
        rect(g, x, 7, x + 2, 10, STONE)
        rect(g, x, 7, x + 2, 7, STONE_L)
    # portão
    rect(g, 12, 18, 19, 27, WOOD_D)
    rect(g, 13, 16, 18, 17, WOOD_D)
    px(g, 12, 17, WOOD_D)
    px(g, 19, 17, WOOD_D)
    for x in range(13, 19, 2):
        vline(g, x, 18, 27, WOOD_X)
    hline(g, 12, 19, 22, WOOD_X)
    # mastro + bandeira
    vline(g, 16, 1, 7, WOOD_X)
    rect(g, 17, 2, 23, 5, RED)
    px(g, 23, 3, RED_D)
    px(g, 20, 3, GOLD)
    hline(g, 4, 27, 28, STONE_D)
    outline(g)
    return g


# ---------------- itens (comida) ----------------
def item_bread():
    g = blank()
    disc(g, 16, 18, 8, WOOD)
    rect(g, 8, 18, 24, 25, WOOD)
    disc(g, 16, 18, 6, WOOD_L)
    rect(g, 10, 18, 22, 23, WOOD_L)
    for i in range(-4, 6, 4):                                # cortes
        vline(g, 16 + i, 13, 16, WOOD_D)
    hline(g, 8, 24, 25, WOOD_D)
    outline(g)
    return g


def item_soup():
    g = blank()
    rect(g, 7, 15, 25, 17, BONE)                             # borda da tigela
    for i, y in enumerate(range(18, 25)):                    # tigela afunilando
        rect(g, 8 + i, y, 24 - i, y, STONE_L)
    rect(g, 9, 15, 23, 17, FIRE)                             # caldo
    px(g, 13, 16, GRN_L)
    px(g, 18, 16, RED)
    disc(g, 11, 12, 1, SMOKE)                                # vapor
    disc(g, 20, 11, 1, SMOKE)
    outline(g)
    return g


def item_stew():
    g = blank()
    disc(g, 16, 19, 9, DARK)                                 # panela
    rect(g, 7, 12, 25, 19, DARK)
    rect(g, 9, 12, 23, 15, WOOD_D)                           # ensopado
    px(g, 12, 13, GRN)
    px(g, 17, 14, RED)
    px(g, 20, 13, GOLD)
    rect(g, 4, 13, 7, 15, STONE_D)                           # alças
    rect(g, 25, 13, 28, 15, STONE_D)
    hline(g, 10, 22, 27, STONE_D)
    outline(g)
    return g


def item_feast():
    g = blank()
    for i, y in enumerate(range(20, 26)):                    # travessa
        rect(g, 5 + i, y, 27 - i, y, STONE_L)
    hline(g, 4, 28, 19, BONE)
    disc(g, 12, 15, 5, WOOD_D)                               # assado
    disc(g, 12, 14, 4, WOOD)
    px(g, 11, 13, WOOD_L)
    vline(g, 17, 10, 18, BONE)                               # osso
    px(g, 16, 9, BONE)
    px(g, 18, 9, BONE)
    disc(g, 22, 16, 3, RED)                                  # fruta
    px(g, 22, 13, GRN_D)
    disc(g, 8, 17, 2, GRN_L)
    outline(g)
    return g


BUILDINGS = {
    'building_serraria_1': serraria,
    'building_fazenda_1': fazenda,
    'building_cozinha_1': cozinha,
    'building_mercado_1': mercado,
    'building_mina_1': mina,
    'building_estabulo_1': estabulo,
    'building_ferraria_1': ferraria,
    'building_altar_1': altar,
    'building_bazar_1': bazar,
    'building_porto_1': porto,
    'building_quartel_1': quartel,
}

ITEMS = {
    'item_bread': item_bread,
    'item_soup': item_soup,
    'item_stew': item_stew,
    'item_feast': item_feast,
}


def main():
    n = 0
    for name, fn in BUILDINGS.items():
        save(fn(), os.path.join(BUILD_DIR, name + '.png'))
        n += 1
    for name, fn in ITEMS.items():
        save(fn(), os.path.join(ITEM_DIR, name + '.png'))
        n += 1
    print(f'OK — {n} sprites gerados.')


if __name__ == '__main__':
    main()
