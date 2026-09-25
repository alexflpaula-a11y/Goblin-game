#!/usr/bin/env python3
"""
gen_gear_overlays.py — Gera os overlays das peças de equipamento que ainda
não tinham arte, para que TODAS as peças "vestíveis visíveis" apareçam no
goblin: capacete, peitoral, calça, arma primária e arma secundária.

O jogo desenha o goblin em camadas: corpo (variação física) + overlays das
peças equipadas (ver js/gear.js e js/assetLoader.js). Cada overlay contém
apenas os pixels que a peça acrescenta, alinhados quadro a quadro.

Este script produz, para cada uma das 5 animações (idle/walk/attack/hurt/
death) e todos os quadros:

  • ferro_cap  (capacete de ferro)  — reaproveita a SILHUETA do capacete
    avaritia (overlay_av_cap_*) recolorida em aço. Alinhamento perfeito.
  • ferro_cal  (calça de ferro)     — idem, a partir de overlay_av_cal_*.
  • wpn_espada (espada de ferro)    — lâmina desenhada na mão direita.
  • wpn_clava  (clava do goblin)    — clava de madeira na mão direita.
  • wpn_escudo (escudo de madeira)  — escudo no braço esquerdo.

As armas seguem a MÃO detectada em cada quadro (o pixel mais externo na
faixa do tronco), então acompanham o balanço do braço nas animações.

Já existentes (feitos por gen_goblin_variations.py, não mexemos): av_cap,
av_pei, av_cal, combos avaritia e ferro_pei (peitoral de ferro).

Uso:  python3 tools/gen_gear_overlays.py
"""
import json
import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GOBLIN_DIR = ROOT / 'assets' / 'sprites' / 'goblins'
OVERLAY_DIR = ROOT / 'assets' / 'sprites' / 'goblin-gear-overlays'
MANIFEST = ROOT / 'assets' / 'manifest.json'

FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15}
S = 32

# ---------------- paletas ----------------
# Aço (mesma família do peitoral_ferro existente).
IRON_OUT = (78, 84, 96)
IRON_DARK = (120, 128, 142)
IRON_MID = (170, 180, 196)
IRON_LIGHT = (210, 217, 228)
# Madeira (mesma paleta de gen_sprites.py).
WOOD = (169, 113, 61)
WOOD_D = (110, 70, 38)
WOOD_X = (74, 48, 24)
WOOD_L = (200, 150, 95)
HANDLE = (98, 64, 35)


def load(path):
    return Image.open(path).convert('RGBA')


def base_frame(anim, frame_no):
    return load(GOBLIN_DIR / f'goblin_{anim}_{frame_no}.png')


def overlay_mask(prefix, anim, frame_no):
    """Conjunto de pixels de um overlay avaritia existente (a silhueta)."""
    p = OVERLAY_DIR / f'overlay_{prefix}_{anim}_{frame_no}.png'
    im = load(p)
    px = im.load()
    return {(x, y) for y in range(S) for x in range(S) if px[x, y][3] > 0}


def blank():
    return Image.new('RGBA', (S, S), (0, 0, 0, 0))


def shade_metal(mask):
    """Sombreia uma silhueta cheia em aço: contorno + meio-tom + brilho."""
    img = blank()
    px = img.load()
    kind = {}
    for (x, y) in mask:
        boundary = any((x + dx, y + dy) not in mask
                       for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)))
        kind[(x, y)] = 'out' if boundary else 'mid'
    # brilho na borda interna de cima/esquerda; sombra na de baixo
    for (x, y) in list(kind):
        if kind[(x, y)] != 'mid':
            continue
        if kind.get((x, y - 1)) == 'out' or kind.get((x - 1, y)) == 'out':
            kind[(x, y)] = 'light'
        elif kind.get((x, y + 1)) == 'out':
            kind[(x, y)] = 'dark'
    cmap = {'out': IRON_OUT, 'dark': IRON_DARK, 'mid': IRON_MID, 'light': IRON_LIGHT}
    for (x, y), k in kind.items():
        px[x, y] = (*cmap[k], 255)
    return img


def hand_tips(anim, frame_no):
    """(mão direita na tela, mão esquerda na tela) na faixa do tronco."""
    im = base_frame(anim, frame_no)
    px = im.load()
    right = left = None
    for y in range(21, 30):          # faixa do tronco/mãos (evita orelhas)
        for x in range(S):
            if px[x, y][3] > 0:
                if right is None or x > right[0]:
                    right = (x, y)
                if left is None or x < left[0]:
                    left = (x, y)
    return right or (22, 24), left or (9, 25)


def put(px, x, y, color):
    if 0 <= x < S and 0 <= y < S:
        px[x, y] = (*color, 255)


def draw_sword(anim, frame_no):
    """Espada de ferro empunhada na mão direita, lâmina para cima."""
    img = blank()
    px = img.load()
    (hx, hy), _ = hand_tips(anim, frame_no)
    gx = min(hx + 1, S - 2)          # ligeiramente à frente da mão
    # cabo
    put(px, gx, hy, HANDLE)
    put(px, gx, hy + 1, WOOD_X)
    # guarda (cruzeta)
    put(px, gx - 1, hy - 1, IRON_DARK)
    put(px, gx, hy - 1, IRON_MID)
    put(px, gx + 1, hy - 1, IRON_DARK)
    # lâmina
    for i in range(2, 8):
        y = hy - i
        put(px, gx, y, IRON_MID)
        put(px, gx - 1, y, IRON_LIGHT if i > 2 else IRON_OUT)  # fio brilhante
    put(px, gx, hy - 8, IRON_LIGHT)  # ponta
    return img


def draw_club(anim, frame_no):
    """Clava de madeira na mão direita."""
    img = blank()
    px = img.load()
    (hx, hy), _ = hand_tips(anim, frame_no)
    gx = min(hx + 1, S - 2)
    # cabo
    put(px, gx, hy, HANDLE)
    put(px, gx, hy - 1, WOOD_D)
    put(px, gx, hy - 2, WOOD_D)
    # cabeça da clava (bloco)
    head = [(-1, -3), (0, -3), (1, -3),
            (-1, -4), (0, -4), (1, -4),
            (-1, -5), (0, -5), (1, -5),
            (0, -6)]
    for dx, dy in head:
        put(px, gx + dx, hy + dy, WOOD)
    # contorno + luz/nós
    put(px, gx - 1, hy - 3, WOOD_X)
    put(px, gx + 1, hy - 5, WOOD_X)
    put(px, gx, hy - 6, WOOD_L)
    put(px, gx - 1, hy - 4, WOOD_L)
    put(px, gx + 1, hy - 4, WOOD_D)
    return img


def draw_shield(anim, frame_no):
    """Escudo de madeira no braço esquerdo (na tela)."""
    img = blank()
    px = img.load()
    _, (hx, hy) = hand_tips(anim, frame_no)
    cx = max(hx - 1, 1)
    cy = hy - 1
    # corpo oval do escudo
    body = [(0, -3), (0, -2), (-1, -1), (0, -1), (1, -1),
            (-1, 0), (0, 0), (1, 0), (-1, 1), (0, 1), (1, 1),
            (0, 2), (0, 3)]
    for dx, dy in body:
        put(px, cx + dx, cy + dy, WOOD)
    # aros/planos
    for dy in (-3, -1, 1, 3):
        put(px, cx, cy + dy, WOOD_D)
    # contorno
    for dx, dy in [(-2, 0), (2, 0), (-1, -2), (1, -2), (-1, 2), (1, 2), (0, -4), (0, 4)]:
        put(px, cx + dx, cy + dy, WOOD_X)
    # umbo de ferro no centro
    put(px, cx, cy, IRON_LIGHT)
    put(px, cx - 1, cy, IRON_DARK)
    put(px, cx + 1, cy, IRON_DARK)
    return img


def lower_body_mask(anim, frame_no):
    """Pixels do goblin da cintura para baixo (cintura + pernas + pés)."""
    im = base_frame(anim, frame_no)
    px = im.load()
    mask = set()
    for y in range(27, S):           # 27 = quadril; abaixo disso são as pernas
        for x in range(S):
            if px[x, y][3] > 0:
                mask.add((x, y))
    return mask


def draw_pants(anim, frame_no):
    """Calça de aço: cinto de couro na cintura + duas perneiras de aço
    (mantendo a separação entre as pernas) + botas escuras nos pés.
    Desenhada sobre a silhueta real das pernas do goblin, quadro a quadro."""
    mask = lower_body_mask(anim, frame_no)
    img = blank()
    if not mask:
        return img
    px = img.load()
    top = min(y for _, y in mask)
    bot = max(y for _, y in mask)
    belt = top                       # cintura
    waist_xs = [x for (x, y) in mask if y == belt]

    for (x, y) in mask:
        inside = lambda dx, dy: (x + dx, y + dy) in mask
        boundary = not (inside(-1, 0) and inside(1, 0) and inside(0, -1) and inside(0, 1))
        if y == belt:
            col = WOOD_D             # cinto de couro
        elif y >= bot - 1:
            col = IRON_DARK          # botas
        elif boundary:
            col = IRON_OUT           # contorno das perneiras
        else:
            col = IRON_MID           # aço
        px[x, y] = (*col, 255)

    # brilho vertical na frente de cada perna (borda esquerda interna)
    for (x, y) in mask:
        if belt < y < bot - 1 and px[x, y][:3] == IRON_MID and (x - 1, y) not in mask:
            px[x, y] = (*IRON_LIGHT, 255)
    # fivela do cinto no centro da cintura
    if waist_xs:
        cx = (min(waist_xs) + max(waist_xs)) // 2
        px[cx, belt] = (*IRON_LIGHT, 255)
    return img


# prefixo → função que gera um quadro
GENERATORS = {
    'ferro_cap': lambda a, f: shade_metal(overlay_mask('av_cap', a, f)),
    'ferro_cal': draw_pants,
    'wpn_espada': draw_sword,
    'wpn_clava': draw_club,
    'wpn_escudo': draw_shield,
}


def main():
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    produced = 0
    for prefix, gen in GENERATORS.items():
        for anim, count in FRAME_COUNTS.items():
            for frame_no in range(count):
                img = gen(anim, frame_no)
                sprite_id = f'overlay_{prefix}_{anim}_{frame_no}'
                rel = f'assets/sprites/goblin-gear-overlays/{sprite_id}.png'
                img.save(ROOT / rel, optimize=True)
                entries.append({'id': sprite_id, 'path': rel})
                produced += 1
        print(f'  {prefix}: {sum(FRAME_COUNTS.values())} quadros')

    # manifest: adiciona/atualiza só estes ids (idempotente)
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    new_ids = {e['id'] for e in entries}
    kept = [e for e in manifest.get('sprites', []) if e['id'] not in new_ids]
    manifest['sprites'] = kept + entries
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                        encoding='utf-8')
    print(f'OK — {produced} overlays gerados e registrados no manifest')


if __name__ == '__main__':
    main()
