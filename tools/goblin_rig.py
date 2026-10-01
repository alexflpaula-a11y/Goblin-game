#!/usr/bin/env python3
"""
Rig de pixel art do goblin (v2).

O goblin foi redesenhado a partir da arte de referencia enviada: pele verde em
tres tons, tunica verde-escura de mangas curtas, cinto e botas de couro,
orelhas grandes e pontudas, olhos escuros e duas presas.

A arte nao e um conjunto de bitmaps prontos. Cada parte do corpo (cabeca,
tronco, bracos, pernas, espada) e definida em CORES CHAPADAS, sem contorno.
Ao montar um quadro o rig:

  1. compoe as partes nas posicoes daquela pose;
  2. gera o contorno escuro automaticamente a partir da silhueta resultante;
  3. pinta os detalhes do rosto (olhos, presas, nariz) por cima;
  4. aplica a mascara da variacao, se houver.

Com isso as 5 animacoes, as 20 variacoes e as armaduras saem todas do mesmo
desenho, sempre coerentes, e qualquer ajuste no goblin se propaga para os
62 x N quadros de uma vez.
"""

from PIL import Image

SIZE = 32

# ---------------------------------------------------------------- paleta ----
C = {
    'o': (24, 38, 28, 255),      # contorno
    'd': (54, 112, 58, 255),     # pele sombra
    'g': (94, 168, 80, 255),     # pele base
    'l': (142, 203, 110, 255),   # pele luz
    'T': (28, 54, 40, 255),      # tunica sombra
    't': (46, 86, 60, 255),      # tunica base
    'u': (70, 120, 80, 255),     # tunica luz
    'B': (52, 36, 24, 255),      # couro sombra
    'b': (96, 64, 40, 255),      # couro base
    'h': (142, 100, 60, 255),    # couro luz
    'w': (240, 240, 222, 255),   # brilho do olho
    'p': (18, 24, 20, 255),      # pupila
    'y': (238, 234, 198, 255),   # presa
    'm': (48, 24, 28, 255),      # boca
    'S': (104, 118, 132, 255),   # aco sombra
    's': (178, 189, 201, 255),   # aco base
    'i': (228, 234, 243, 255),   # aco luz
    'r': (176, 52, 48, 255),     # vermelho
    'R': (108, 28, 28, 255),     # vermelho escuro
    'W': (228, 224, 212, 255),   # pano claro / albino
    'Y': (216, 178, 58, 255),    # ouro
    'c': (70, 54, 42, 255),      # marca escura
    '1': (42, 46, 68, 255),      # obsidiana sombra (avaritia)
    '2': (86, 94, 122, 255),      # obsidiana base
    '3': (132, 142, 176, 255),   # obsidiana luz
    '4': (86, 232, 212, 255),    # gema turquesa
    '5': (30, 142, 134, 255),    # gema turquesa sombra
    '6': (214, 176, 58, 255),    # filete dourado
    '7': (82, 90, 101, 255),     # ferro sombra
    '8': (140, 150, 162, 255),   # ferro base
    '9': (198, 206, 216, 255),   # ferro luz
    'L': (134, 94, 54, 255),     # madeira (escudo)
    'M': (176, 132, 80, 255),    # madeira luz
    'n': (186, 146, 110, 255),   # pele clara alternativa
    'k': (14, 22, 18, 255),      # preto
}

SKIN_KEYS = ('d', 'g', 'l')


def grid(rows):
    return [list(r) for r in rows]


def check(rows, w):
    for r in rows:
        assert len(r) == w, (len(r), ''.join(r))
    return rows


# ------------------------------------------------- partes (cores chapadas) --
# Cabeca 18x10: cranio nas colunas 5..12, orelhas em folha nas pontas.
HEAD = check(grid([
    ".ggg..gggggg..ggg.",
    ".gggg.gggggg.gggg.",
    ".gggg.gggggg.gggg.",
    "..gggggggggggggg..",
    "...gggggggggggg...",
    ".....gggggggg.....",
    ".....gggggggg.....",
    ".....gggggggg.....",
    ".....gggggggg.....",
    "......gggggg......",
]), 18)

# Tronco 10x7 (tunica, cinto, calcao)
TORSO = check(grid([
    "..tttttt..",
    ".tttttttt.",
    "tttuuuuttt",
    "ttuuuuuutt",
    "tttuuuuttt",
    "bbbbhhbbbb",
    "TTttttttTT",
]), 10)

# Braco 3x6 (manga curta, antebraco, mao)
ARM = check(grid([
    "ttt",
    "ttt",
    "ggg",
    "ggg",
    "ggg",
    "ggg",
]), 3)

# Perna 4x6 (coxa + bota)
LEG = check(grid([
    "gggg",
    "gggg",
    "gggg",
    "gggg",
    "bbbb",
    "bbbb",
]), 4)

# ------------------------------------------------------------- espadas ------
SWORD_DOWN = check(grid([
    ".b.",
    "hhh",
    "sss",
    "sss",
    "sss",
    "sss",
    ".s.",
]), 3)

SWORD_DIAG = check(grid([
    ".....s",
    "....ss",
    "...ss.",
    ".hss..",
    "hhs...",
    "b.....",
]), 6)

SWORD_FWD = check(grid([
    "bhhsssss",
    ".hsssssi",
    "...sss..",
]), 8)

SWORD_UP = check(grid([
    ".s.",
    "sss",
    "sss",
    "sss",
    "sss",
    "hhh",
    ".b.",
]), 3)

SWORDS = {'down': SWORD_DOWN, 'diag': SWORD_DIAG, 'fwd': SWORD_FWD, 'up': SWORD_UP}
SWORD_ANCHOR = {'down': (0, 0), 'diag': (-3, 0), 'fwd': (-5, 1), 'up': (0, -6)}

# -------------------------------------------------------------- posicoes ----
REST = {
    'head':  (7, 10),
    'torso': (11, 20),
    'arm_l': (8, 21),
    'arm_r': (21, 21),
    'leg_l': (11, 26),
    'leg_r': (17, 26),
    'sword': (6, 25),
}

DRAW_ORDER = ['arm_r', 'leg_l', 'leg_r', 'torso', 'sword', 'head', 'arm_l']

# Detalhes do rosto, em coordenadas relativas a cabeca (18x10).
FACE = {
    (6, 4): 'l', (7, 4): 'l', (6, 5): 'l',
    (6, 6): 'p', (7, 6): 'w', (10, 6): 'w', (11, 6): 'p',
    (8, 7): 'd', (9, 7): 'd',
    (6, 8): 'y', (7, 8): 'm', (8, 8): 'm', (9, 8): 'm', (10, 8): 'm', (11, 8): 'y',
}

# Pontos de ancoragem usados pelos geradores de armadura (canvas 32x32, repouso).
ANCHORS = {
    'head_box': (8, 10, 23, 19),    # x0, y0, x1, y1 inclusivos
    'skull_box': (12, 10, 19, 19),
    'ear_l': (8, 11, 11, 14),
    'ear_r': (20, 11, 23, 14),
    'torso_box': (11, 20, 20, 26),
    'belt_y': 25,
    'legs_box': (11, 26, 20, 31),
    'hand_l': (9, 26),
    'hand_r': (22, 26),
    'ground_y': 31,
}


# ------------------------------------------------------------ renderizacao --
def _blank():
    return [[None] * SIZE for _ in range(SIZE)]


def _blit(buf, part, ox, oy, flip=False):
    rows = part
    if flip:
        rows = [list(reversed(r)) for r in rows]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == '.':
                continue
            px, py = ox + x, oy + y
            if 0 <= px < SIZE and 0 <= py < SIZE:
                buf[py][px] = ch


def _outline(buf):
    """Transforma em contorno os pixels da borda da silhueta (contorno interno)."""
    out = [row[:] for row in buf]
    for y in range(SIZE):
        for x in range(SIZE):
            if buf[y][x] is None:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if not (0 <= nx < SIZE and 0 <= ny < SIZE) or buf[ny][nx] is None:
                    out[y][x] = 'o'
                    break
    return out


def _shade(buf):
    """Escurece 1px abaixo da fronteira pele/tunica e acima do cinto."""
    out = [row[:] for row in buf]
    for y in range(1, SIZE):
        for x in range(SIZE):
            cur, up = buf[y][x], buf[y - 1][x]
            if cur in SKIN_KEYS and up in ('t', 'u', 'T', 'b', 'B'):
                out[y][x] = 'd'
            if cur == 't' and up in ('b', 'B'):
                out[y][x] = 'T'
    return out


def to_image(buf):
    img = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            ch = buf[y][x]
            if ch is not None:
                px[x, y] = C[ch]
    return img


def compose(pose, variation=None, swap=None, extra_parts=None, overlay=None,
            gear=None):
    """Monta um quadro. Retorna o buffer de chars (ainda nao convertido)."""
    extra_parts = extra_parts or {}
    buf = _blank()
    head_pos = None
    ctx = {}
    for name in DRAW_ORDER:
        spec = pose.get(name)
        if spec is None:
            continue
        dx, dy = spec[0], spec[1]
        flip = len(spec) > 2 and bool(spec[2])
        if name == 'sword':
            kind = pose.get('_sword', 'down')
            art = SWORDS[kind]
            ax, ay = SWORD_ANCHOR[kind]
            dx, dy = dx + ax, dy + ay
        elif name.startswith('arm'):
            art = extra_parts.get(name, ARM)
        elif name.startswith('leg'):
            art = extra_parts.get(name, LEG)
        elif name == 'head':
            art = extra_parts.get(name, HEAD)
        else:
            art = extra_parts.get(name, TORSO)
        bx, by = REST[name]
        ox, oy = bx + dx, by + dy
        ctx[name] = (ox, oy, flip)
        if name == 'head':
            head_pos = (ox, oy, flip)
        _blit(buf, art, ox, oy, flip=flip)

    # Camadas de equipamento: cada peca e ancorada a uma parte do corpo e
    # desenhada na posicao que a parte tem NAQUELE quadro, entao a armadura
    # acompanha o goblin em qualquer pose. Entram antes do contorno para
    # ganharem contorno proprio e se fundirem com a silhueta.
    gear_mask = set()
    for piece in (gear or ()):
        anchor = piece['anchor']
        if anchor not in ctx or pose.get(anchor) is None:
            continue
        ax, ay, aflip = ctx[anchor]
        gx = ax + (-piece.get('dx', 0) if aflip else piece.get('dx', 0))
        gy = ay + piece.get('dy', 0)
        art = piece['grid']
        rows = [list(reversed(r)) for r in art] if aflip else art
        for yy, row in enumerate(rows):
            for xx, ch in enumerate(row):
                if ch == '.':
                    continue
                px, py = gx + xx, gy + yy
                if 0 <= px < SIZE and 0 <= py < SIZE:
                    buf[py][px] = ch
                    gear_mask.add((px, py))

    buf = _shade(buf)
    buf = _outline(buf)

    # Rosto por cima do contorno.
    if head_pos and pose.get('head') is not None and not pose.get('_faceless'):
        hx, hy, hflip = head_pos
        face = dict(FACE)
        if swap:
            face = {k: swap.get(v, v) for k, v in face.items()}
        for (fx, fy), ch in face.items():
            x = hx + (17 - fx if hflip else fx)
            y = hy + fy
            if (0 <= x < SIZE and 0 <= y < SIZE
                    and buf[y][x] is not None and (x, y) not in gear_mask):
                buf[y][x] = ch
        if variation:
            variation(buf, ctx, gear_mask)

    if swap:
        for y in range(SIZE):
            for x in range(SIZE):
                if buf[y][x] in swap and (x, y) not in gear_mask:
                    buf[y][x] = swap[buf[y][x]]

    if overlay:
        overlay(buf, ctx)
    return buf


def render(pose, **kw):
    return to_image(compose(pose, **kw))


def base_pose(**over):
    p = {k: (0, 0) for k in DRAW_ORDER}
    p['arm_r'] = (0, 0, True)
    p['leg_r'] = (0, 0, True)
    p['_sword'] = 'down'
    p.update(over)
    return p


if __name__ == '__main__':
    import os
    os.makedirs('/tmp/prev', exist_ok=True)
    img = render(base_pose())
    img.save('/tmp/prev/goblin_base.png')
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save('/tmp/prev/goblin_base_big.png')
    print('ok', img.getbbox())
