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
    'o': (24, 32, 22, 255),      # contorno
    'e': (24, 78, 42, 255),      # pele verde profunda
    'j': (60, 145, 86, 255),     # pele verde media
    'f': (168, 235, 190, 255),   # pele verde brilho
    'z': (150, 162, 148, 255),   # aco da adaga
    'q': (205, 222, 205, 255),   # aco da adaga, brilho
    'd': (44, 117, 67, 255),     # pele sombra
    'g': (74, 178, 104, 255),     # pele base
    'l': (104, 205, 132, 255),   # pele luz
    'T': (28, 52, 38, 255),      # tunica sombra
    't': (42, 74, 52, 255),      # tunica base
    'u': (58, 98, 66, 255),     # tunica luz
    'B': (60, 48, 36, 255),      # couro sombra
    'b': (106, 82, 62, 255),      # couro base
    'h': (142, 112, 80, 255),    # couro luz
    'w': (240, 240, 222, 255),   # brilho do olho
    'p': (18, 24, 20, 255),      # pupila
    'y': (222, 214, 178, 255),   # presa
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

SKIN_KEYS = ('e', 'd', 'j', 'g', 'l', 'f')


def grid(rows):
    return [list(r) for r in rows]


def check(rows, w):
    for r in rows:
        assert len(r) == w, (len(r), ''.join(r))
    return rows


# ------------------------------------------- partes (recortes da arte) --
HEAD = check(grid([
    "........ooolgdoodgjoo...",
    "...oooooeejllfjeljggeo..",
    ".oojlljddllgglffddgldoo.",
    "oodjjllljdjglgllledjljeo",
    ".oooodjglfljlllgldedeooo",
    "..o..oedjjgllgjlggjeo.o.",
    "......oddgoojggoojjoo...",
    "......oedjffgdlffjeo....",
    "......oddjollddgojfo....",
    "......oddjggjdjgglfo....",
    "......oedgggeeeeggo.....",
    ".....ooBdjjgggjydo......",
]), 24)   # 24x12

TORSO = check(grid([
    "....oBdggllgjddo..",
    "....oBdgdeeeeeeo..",
    ".....bbggjddBd....",
    ".....Bbjgljdb.....",
    ".....Bbdglldbo....",
    ".....BbbjjjlbB....",
    "...BbbBBbbbbBo....",
    ".bbBbBoBBBBBbB....",
    ".bbBBBBbbbbbbb....",
    "oBBbBoBBbbbBBBBooo",
    ".......BBBBo......",
    ".......oBoBo......",
    ".......ooooo......",
    "...........o......",
]), 18)   # 18x14

ARM_L = check(grid([
    "....ode.",
    "...oegd.",
    "..ojlgjd",
    ".ojgljeo",
    "odgjeeoo",
    "djggdooo",
    "djgdjo..",
    "oojg....",
    "..oo....",
]), 8)   # 8x9

ARM_R = check(grid([
    ".geo...",
    "dddo...",
    ".djd...",
    ".djjl..",
    ".Belgeo",
    ".ojjdo.",
    ".oodeo.",
]), 7)   # 7x7

LEG_L = check(grid([
    "..oBoBBo",
    ".ooddjeo",
    "oBbbboo.",
    "oBBBoo..",
]), 8)   # 8x4

LEG_R = check(grid([
    "djgeo..",
    "edBBoo.",
    "oBbbBoo",
    "BoBBBoo",
]), 7)   # 7x4

# Adaga da referencia (empunhadura embaixo a esquerda, lamina para cima-direita)
SWORD_DIAG = check(grid([
    "....o",
    "...oo",
    ".oooB",
    "oofzo",
    "bbzBo",
    ".joo.",
]), 5)

SWORD_DOWN = check(grid([
    ".bb.",
    "oBBo",
    "ozqo",
    "ozqo",
    "ozqo",
    ".oo.",
]), 4)

SWORD_UP = check(grid([
    ".oo.",
    "ozqo",
    "ozqo",
    "ozqo",
    "oBBo",
    ".bb.",
]), 4)

SWORD_FWD = check(grid([
    ".ooooo.",
    "obBzzzo",
    "obBqqzo",
    ".ooooo.",
]), 7)

SWORDS = {'down': SWORD_DOWN, 'diag': SWORD_DIAG, 'fwd': SWORD_FWD, 'up': SWORD_UP}
SWORD_ANCHOR = {'down': (-1, 4), 'diag': (0, 0), 'fwd': (-3, 3), 'up': (-1, -1)}

# -------------------------------------------------------------- posicoes ----
REST = {
    'head':   (3, 6),
    'torso':  (6, 18),
    'arm_l':  (3, 18),
    'arm_r':  (19, 20),
    'leg_l':  (5, 28),
    'leg_r':  (18, 28),
    'sword':  (23, 18),
}

# O braco DIREITO (do espectador) e o que segura a adaga, como na referencia.
DRAW_ORDER = ['arm_l', 'leg_l', 'leg_r', 'torso', 'sword', 'head', 'arm_r']

# Detalhes do rosto, em coordenadas relativas a cabeca (18x10).
FACE = {
    (10, 6): 'o', (11, 6): 'o', (15, 6): 'o', (16, 6): 'o',   # sobrancelhas
    (10, 7): 'f', (11, 7): 'f', (15, 7): 'f', (16, 7): 'f',   # olhos
    (13, 8): 'd', (14, 8): 'd', (13, 9): 'd',                 # focinho
    (15, 11): 'y',                                            # presa
}

# Pontos de ancoragem usados pelos geradores de armadura (canvas 32x32, repouso).
ANCHORS = {
    'head_box': (3, 6, 26, 17),
    'skull_box': (9, 6, 21, 17),
    'ear_l': (3, 8, 10, 11),
    'ear_r': (19, 7, 26, 11),
    'torso_box': (9, 18, 20, 29),
    'belt_y': 24,
    'legs_box': (5, 28, 24, 31),
    'hand_l': (4, 23),
    'hand_r': (23, 22),
    'ground_y': 31,
}



DEFAULT_PART = {
    'head': HEAD, 'torso': TORSO, 'arm_l': ARM_L, 'arm_r': ARM_R,
    'leg_l': LEG_L, 'leg_r': LEG_R,
}
HEAD_W = len(HEAD[0])


def _outline_region(buf, cells):
    """Contorna apenas os pixels de equipamento que ficam na borda."""
    out = [row[:] for row in buf]
    for x, y in cells:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < SIZE and 0 <= ny < SIZE) or buf[ny][nx] is None:
                out[y][x] = 'o'
                break
    return out


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



def save_png(img, path):
    """Grava o sprite como PNG indexado (mesmos pixels, metade do tamanho).

    O jogo embute todos os sprites em base64 no arquivo unico, entao cada
    byte conta. Quadros com transparencia parcial (o fade da morte) nao
    cabem em paleta e sao gravados em RGBA normal.
    """
    img = img.convert('RGBA')
    data = list(img.getdata())
    if any(0 < px[3] < 255 for px in data):
        img.save(path, optimize=True)
        return
    opaque = sorted({px[:3] for px in data if px[3] == 255})
    if len(opaque) > 255:
        img.save(path, optimize=True)
        return
    index = {c: i + 1 for i, c in enumerate(opaque)}
    out = Image.new('P', img.size, 0)
    out.putdata([index[px[:3]] if px[3] == 255 else 0 for px in data])
    pal = [0, 0, 0]
    for c in opaque:
        pal.extend(c)
    out.putpalette(pal)
    out.save(path, optimize=True, transparency=0)


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
        else:
            art = extra_parts.get(name, DEFAULT_PART[name])
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

    # A arte ja vem com contorno e sombreamento proprios (recortados da
    # referencia), entao so o equipamento precisa de contorno automatico.
    if gear_mask:
        buf = _outline_region(buf, gear_mask)

    # Rosto por cima do contorno.
    if head_pos and pose.get('head') is not None and not pose.get('_faceless'):
        hx, hy, hflip = head_pos
        face = dict(FACE)
        if swap:
            face = {k: swap.get(v, v) for k, v in face.items()}
        for (fx, fy), ch in face.items():
            x = hx + (HEAD_W - 1 - fx if hflip else fx)
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
    p['_sword'] = 'diag'
    p.update(over)
    return p


if __name__ == '__main__':
    import os
    os.makedirs('/tmp/prev', exist_ok=True)
    img = render(base_pose())
    img.save('/tmp/prev/goblin_base.png')
    img.resize((SIZE * 12, SIZE * 12), Image.NEAREST).save('/tmp/prev/goblin_base_big.png')
    print('ok', img.getbbox())
