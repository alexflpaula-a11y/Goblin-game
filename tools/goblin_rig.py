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

SIZE = 64

# ---------------------------------------------------------------- paleta ----
C = {
    # --- paleta extraida da propria referencia (k-means, 12 cores) ---
    'k': (11, 38, 16, 255),      # contorno/pupila (verde quase preto)
    'e': (19, 75, 36, 255),      # pele sombra profunda
    'd': (47, 123, 71, 255),     # pele sombra
    'n': (80, 147, 99, 255),     # pele meio-tom frio
    'j': (58, 165, 91, 255),     # pele meio-tom
    'g': (77, 186, 109, 255),    # pele base
    'l': (102, 204, 132, 255),   # pele luz
    'f': (179, 243, 197, 255),   # pele brilho / olho
    'B': (57, 49, 35, 255),      # couro sombra
    'b': (91, 69, 55, 255),      # couro base
    'h': (116, 96, 79, 255),     # couro luz
    'z': (147, 161, 143, 255),   # aco da adaga
    'q': (205, 222, 205, 255),   # aco da adaga, brilho
    'o': (24, 32, 22, 255),      # contorno do equipamento
    'K': (12, 12, 14, 255),      # preto puro (tapa-olho)
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
}

SKIN_KEYS = ('k', 'e', 'd', 'n', 'j', 'g', 'l', 'f')


def grid(rows):
    return [list(r) for r in rows]


def check(rows, w):
    for r in rows:
        assert len(r) == w, (len(r), ''.join(r))
    return rows


# ------------------------------------------- partes (recortes da arte) --
# Recortadas pixel a pixel de art-source/goblins-v2/referencia-limpa.png,
# na resolucao nativa (64x64) e com a paleta original — inclusive os pixels
# escuros do contorno interno e das pupilas, que dao o volume do desenho.

HEAD = check(grid([
    ".................kkk....kkkkk.......",
    "...............kkkkkk....kkkkk......",
    "..............kdgggndk..ndlnndk.....",
    "............kedggggffd.engnjglne....",
    "..k.kk..eke.eglggggglfffenddjlld....",
    "..ddgggglgjedggggggglfffejddjggde...",
    ".kddgggllllddddjgggggllfgkedjjjgdkk.",
    "edddddggllflgjdjggggggggflekedjgnndk",
    ".kkkkkdddggllflgdggjgjlglfdkkdde.kk.",
    "....k.kddddggggjggggjjgggggkkkek....",
    ".......kkdddjjgggggggjjgggljnk......",
    ".......kkdddjjgjgjgjjgggjglnnk......",
    ".......k.ekedjjjggdljjjjjjednk......",
    ".......k..eejjjnffkeggjglfkkk.......",
    ".........kdedddnfffedjjggfdek.......",
    ".........kddjggjgggdlljjdgllze......",
    ".........kddjjjjjjjggjgjggjlzk......",
    ".........kdddjjjjjjljlgglggk........",
    ".........keddjjjjjjddfflggn.........",
    ".........kedngjjjggjkkennee.........",
]), 36)   # 36x20

TORSO = check(grid([
    ".....kBdnnjjjjdllgnlnkk....",
    ".....eBBddjjjglgjlggdee....",
    ".....eBBhdjgjjgglgdddnze...",
    ".......Bhdngddeeeeeekk.....",
    ".......BhbnljdddddBBkn.....",
    ".......bbhdlglddjnbbk......",
    ".......bbhdgggljjdbhB......",
    ".......hBhdngglggdbhBe.....",
    ".......bBhhdjggglnhhkk.....",
    ".......Bbzzddjjddnzzbk.....",
    "....kkkBBhhbnnnnnnzhBk.....",
    "....BbhhbbbbhbbhhhbbBB.....",
    "nkkbbbhBBBbBBBbbbbbbBk.....",
    "kkhBbbbbkBbBBBBBbBBhhB.....",
    "khzBBBBBBbhhhhhhhbbhhb.....",
    ".hzbbbBkbbbhhhhbbbbbbhBBkkk",
    ".BhBbbBBbbBbhhhhbbbBBbBbBk.",
    ".........Bbbbbbbbb.........",
    ".........kBBBBBBBB.........",
    ".........kBBBBBBBk.........",
    "..........kBkkk.k..........",
]), 27)   # 27x21

ARM_L = check(grid([
    "........k.k..",
    ".....k.kndd..",
    ".....k.egddkb",
    "....kdnnljgnb",
    "....kjllgjddB",
    "...kdljgjdeeB",
    ".kkdggdedekeb",
    "kddlgjgkekkkB",
    "knjgglgekkkkB",
    "knjjggenkk...",
    "kddgggknkB...",
    "..kdjg.......",
    "...kdd.......",
    ".....k.......",
]), 13)   # 13x14

ARM_R = check(grid([
    ".e........",
    ".gne......",
    "ddlk......",
    "eddk......",
    ".edne.....",
    ".ndgd.e...",
    ".dndjlne..",
    ".ndjdj.e..",
    ".kkejlgeek",
    ".kkndjdk..",
    ".kkkndk...",
    ".kkkddk...",
]), 10)   # 10x12

LEG_L = check(grid([
    "..kkkkkkkBB",
    "....kkkkkBk",
    "...kdnnnddk",
    ".kBBBeeed..",
    "kbhhhhbBk..",
    "kbbbbbbBk..",
    "kkBkkBkk...",
]), 11)   # 11x7

LEG_R = check(grid([
    "BBednnk...",
    "ednglne...",
    "kdnnkkkk..",
    ".eeeBBBBB.",
    "kBbbhhhhbk",
    "kBbbbbbbBk",
    ".kkkkkkkkk",
]), 10)   # 10x7

# Adaga da referencia: lamina apontando para cima-direita.
SWORD_DIAG = check(grid([
    ".......kk.",
    "......kkkk",
    "......kBB.",
    "....kffB..",
    "k.Bkffzkkk",
    "zzBzfzb.k.",
    "k.zBzB....",
    "...zB.....",
    ".f.zk.....",
]), 10)   # 10x9

SWORD_DOWN = check(grid([
    ".bb.",
    "kBBk",
    "khhk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    ".kzk",
    "..k.",
]), 4)

SWORD_UP = check(grid([
    ".k..",
    "kzk.",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "kzqk",
    "khhk",
    "kBBk",
    ".bb.",
]), 4)

SWORD_FWD = check(grid([
    ".kkkkkkkkkk.",
    "kbBzzzzzzzzk",
    "khBqqqqqqqzk",
    ".kkkkkkkkkk.",
]), 12)

SWORDS = {'down': SWORD_DOWN, 'diag': SWORD_DIAG, 'fwd': SWORD_FWD, 'up': SWORD_UP}
SWORD_ANCHOR = {'down': (1, 7), 'diag': (0, 0), 'fwd': (1, 6), 'up': (1, -2)}

# -------------------------------------------------------------- posicoes ----
REST = {
    'head':   (13, 20),
    'torso':  (17, 40),
    'arm_l':  (11, 41),
    'arm_r':  (38, 43),
    'leg_l':  (15, 57),
    'leg_r':  (35, 57),
    'sword':  (43, 42),
}

# O braco DIREITO (do espectador) e o que segura a adaga, como na referencia.
DRAW_ORDER = ['arm_l', 'leg_l', 'leg_r', 'torso', 'sword', 'head', 'arm_r']

# Detalhes do rosto, em coordenadas relativas a cabeca (18x10).
FACE_CELLS = {
    # Os olhos ficam nas linhas 12-15 da cabeca. A arte de referencia so
    # tem, ali, uns pixels de verde mais claro: de longe o rosto some e o
    # goblin vira uma mancha de folhas. Por isso o rosto DEIXA de ser lido
    # da arte e passa a ser desenhado — branco com pupila escura, como no
    # sprite antigo, que era o que fazia o olho aparecer.
    # Olho de 4 px com a pupila de 2 px NO MEIO: sobra branco dos dois
    # lados dela. Com a pupila na beirada ela se perdia no contorno e o
    # olho virava um quadradinho branco sem olhar.
    'brow_l':  [(14, 12), (15, 12), (16, 12), (17, 12)],
    'eye_l':   [(14, 13), (17, 13), (14, 14), (17, 14)],
    'pupil_l': [(15, 13), (16, 13), (15, 14), (16, 14)],
    'under_l': [(14, 15), (15, 15), (16, 15), (17, 15)],
    'brow_r':  [(23, 12), (24, 12), (25, 12), (26, 12)],
    'eye_r':   [(23, 13), (26, 13), (23, 14), (26, 14)],
    'pupil_r': [(24, 13), (25, 13), (24, 14), (25, 14)],
    'under_r': [(23, 15), (24, 15), (25, 15), (26, 15)],
    'tusk':    [(21, 18), (22, 18)],
}

# Cor de cada parte do rosto. As variacoes mexem AQUI (swap), entao um
# olho de rubi e so trocar 'w' por vermelho nas celulas do olho.
FACE_TINTA = {
    'brow_l': 'k', 'brow_r': 'k',        # sobrancelha: a linha que da o olhar
    'eye_l': 'w', 'eye_r': 'w',          # esclera
    'pupil_l': 'k', 'pupil_r': 'k',      # pupila
    'under_l': 'e', 'under_r': 'e',      # sombra embaixo, para o olho assentar
    'tusk': 'w',
}


def _face_art():
    """Monta o rosto a partir de FACE_CELLS/FACE_TINTA, dentro da cabeca."""
    out = {}
    for nome, cells in FACE_CELLS.items():
        for x, y in cells:
            if 0 <= y < len(HEAD) and 0 <= x < len(HEAD[0]) and HEAD[y][x] != '.':
                out[(x, y)] = FACE_TINTA[nome]
    return out


FACE = _face_art()

# Pontos de ancoragem usados pelos geradores de armadura (canvas 32x32, repouso).
ANCHORS = {
    'head_box': (13, 20, 48, 39),
    'skull_box': (22, 20, 42, 39),
    'ear_l': (13, 23, 26, 28),
    'ear_r': (37, 21, 48, 28),
    'torso_box': (24, 40, 44, 60),
    'belt_y': 52,
    'legs_box': (15, 57, 44, 63),
    'hand_l': (16, 52),
    'hand_r': (45, 50),
    'ground_y': 63,
}



# ----------------------------------------------------------- corpo caido ---
# A pose de morto NAO sai de rotacao. Girar o goblin de pe num angulo
# quebrado arrebenta o contorno de 1 px e embaralha o rosto; em 90 graus
# exatos ele fica deitado na horizontal, que nao e a pose pedida. Entao o
# corpo caido e um DESENHO proprio, na mesma paleta e no mesmo canvas de
# 64x64: DE BRUCOS, de costas para a camera, despencado numa diagonal
# RASA (mais largo que alto, como na imagem de referencia): botas
# embaixo a esquerda, cabeca la na direita, as orelhas abertas no chao,
# as costas do macacao a mostra e os membros jogados para os lados.
# Nao ha rosto nenhum: a cara esta enfiada no chao.
#
# A arte vem de art-source/goblins-v2/caido-limpa.png e e colada aqui pelo
# mesmo motivo das outras partes: o rig nao depende de arquivo em tempo de
# execucao. Para regerar: python3 tools/import_caido.py
# Onde cai a mao aberta do braco estendido: e dai que pende a arma
# equipada quando o goblin morre segurando alguma coisa.
LAY_HAND = (50, 44)

LAY = check(grid([
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    "................................................................",
    ".........................................kk.....................",
    "..........................kk.............kkk....................",
    ".......................kkknk.............klk....................",
    "......................knllllk............klfk...................",
    "......................kgglglk...........knggkk..................",
    "......................kjjjggnk..........kngglk..................",
    "......................kkjjjglkk.........kndglfk.................",
    "........................kkjjgffk........kddggnkkk...............",
    ".........................kkjjllkkk......kdddggkffkk.............",
    "..........................kkegglfk......kddgglfffffk............",
    "...........................kkjjllfkk....kdgggglggllfk...........",
    "............................keeggfffkkkknggggggggglllk..........",
    ".............................kkggglfflknnggggggggggglk..........",
    "..............................kddggllhkkngggggggggggllk.........",
    "..............................kddgggbbbBgggggggggggggkk.........",
    ".............................kkdgbbbbbbldggggggggggggjk.........",
    "............................kkllbbbbbbggddgggggggggggjk.........",
    "..........................kknbhbbbbbgggggggggggggggggk..........",
    ".......................kkkbhhbbbbbbgggggggdjgggggggggk..........",
    ".......kkkk.....kkkkkkkbbhbhbbbbdgggggggggddgggggggglk..........",
    ".......kbkhk..kkhhhhhhhhhbbBbbbbgggggggggggkddgjgggggfkk........",
    "......kkbbhkkkknhhhhhhhbbbbBBbbegggggggggggBeeeeeeegggfk........",
    "......kBBkbhkfflhbbbbbbbbbbbBbbBggggggggbbbBeeeeeeeeeglk........",
    ".......kBBkhdllgBbbbbbbbbbbbBBbbbggggbbbbbbhkekkkkeeeeelkk......",
    ".......kBkkbhlgjBBbBBBbbbbbbbBBbbegbbbbbbbbgkk....kkkeeggk......",
    ".......kBBkBeejeeBBBBBBbbbbbbbBbbebbbbbbbgggfk......kkkekk......",
    ".......kBBkBBeeekBBkkkBbbbbbbbBBbbbbbbjeggggfk........kkkk......",
    "........kkkkkkkkkkk...kbbbbbbbBBbbbbBeeeeggglk..................",
    "......................kBbbbbbbbBbbbeeekkkggglk..................",
    ".......................kbbbbbbbBBBBekkkkkegggk..................",
    ".......................kBbbbbbbBBBBk.....kgggfk.................",
    ".......................kBBbbbbBBBkk......kggggk.................",
    "......................kkbbbbbbBBk........kegggk.................",
    ".....................kbbbbbbBBBk..........kgggkk................",
    ".................kkkkllbbbbbBBk...........kggggk................",
    "...............kkbkhdlgBbbbbBk............keggnk................",
    "...............kbBhhhljdBbBBk..............kggglkk..............",
    "...............kbBhBejjeBBBBk..............kgggllk..............",
    "...............kBkkBeekekBkk...............kjgglkk..............",
    "...............kBBBkkkkkkk.................kjjjjjk..............",
    "..............kBBBBk........................kjeek...............",
    "..............kBBBk.........................kkkk................",
    "...............kBBk.............................................",
    "...............kkkk.............................................",
]), SIZE)   # 64x64


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


def squash_rows(grid, n, lo, hi):
    """Encolhe `grid` em n linhas, tirando linhas da faixa [lo, hi).

    Serve para o goblin AGACHAR. Antes, agachar era so empurrar o tronco
    para baixo, e o corpo afundava por dentro das pernas — parecia que ele
    encolhia dentro das botas. Aqui as linhas somem de verdade: as coxas
    comprimem, o quadril continua no chao e o ombro desce.

    A altura final e a mesma (as linhas que sairam viram vazio no TOPO), de
    propositio: assim a armadura que veste a parte passa pelo mesmo encolhe
    e continua encaixada pixel a pixel, sem nenhum alinhamento manual.
    """
    cand = list(range(lo, min(hi, len(grid))))
    n = max(0, min(n, len(cand)))
    if not n:
        return grid
    # linhas espalhadas por igual: comprimir sempre no mesmo ponto criaria
    # uma dobra, comprimir espalhado le como joelho flexionando
    fora = {c for i, c in enumerate(cand)
            if ((i + 1) * n) // len(cand) > (i * n) // len(cand)}
    w = len(grid[0])
    return ([['.'] * w for _ in range(len(fora))]
            + [list(row) for i, row in enumerate(grid) if i not in fora])


# Faixa de cada parte que pode comprimir. So o tronco agacha, e so da
# cintura para baixo: as linhas 14-19 do desenho sao a barra da calca e as
# coxas. Comprimir mais acima comeria a calca inteira e o goblin parecia
# que estava perdendo a roupa, nao dobrando o joelho.
SQUASH_BAND = {'torso': (14, 20)}


def _squash_part(name, art, n):
    lo, hi = SQUASH_BAND.get(name, (len(art) // 2, len(art) - 1))
    return squash_rows(art, n, lo, hi)


def compose(pose, variation=None, swap=None, extra_parts=None, overlay=None,
            gear=None):
    """Monta um quadro. Retorna o buffer de chars (ainda nao convertido)."""
    extra_parts = extra_parts or {}
    squash = pose.get('_squash') or {}
    buf = _blank()
    head_pos = None
    ctx = {}

    if pose.get('_lay') is not None:
        # Corpo caido: um desenho inteiro, nao as partes remontadas. A pose
        # so diz onde ele encosta no quadro (o quique ao bater no chao).
        lx, ly = pose['_lay']
        _blit(buf, LAY, lx, ly)
        ctx['lay'] = (lx, ly, False)
        ctx['sword'] = (lx + LAY_HAND[0], ly + LAY_HAND[1], False)
    for name in DRAW_ORDER:
        if pose.get('_lay') is not None:
            break
        spec = pose.get(name)
        if spec is None:
            continue
        dx, dy = spec[0], spec[1]
        flip = len(spec) > 2 and bool(spec[2])
        if name == 'sword':
            # 'sword' e um ANCORA de mao, nao uma parte do corpo. O goblin
            # nasce desarmado: a posicao e sempre calculada (para a arma
            # equipada saber onde se encaixar), mas a adaga so e desenhada
            # se a pose pedir explicitamente (_weapon), o que hoje nenhuma
            # animacao faz — quem desenha arma e o equipamento.
            kind = pose.get('_sword', 'down')
            ax, ay = SWORD_ANCHOR[kind]
            dx, dy = dx + ax, dy + ay
            if not pose.get('_weapon'):
                ctx[name] = (REST[name][0] + dx, REST[name][1] + dy, flip)
                continue
            art = SWORDS[kind]
        else:
            art = extra_parts.get(name, DEFAULT_PART[name])
            if squash.get(name):
                art = _squash_part(name, art, squash[name])
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
        # 'lay' nao e uma parte do corpo: e o quadro inteiro do corpo caido.
        viva = (pose.get('_lay') is not None if anchor == 'lay'
                else pose.get(anchor) is not None)
        if anchor not in ctx or not viva:
            continue
        ax, ay, aflip = ctx[anchor]
        gx = ax + (-piece.get('dx', 0) if aflip else piece.get('dx', 0))
        gy = ay + piece.get('dy', 0)
        art = piece['grid']
        # A peca encolhe junto com a parte que veste (ver squash_rows): so
        # vale quando ela cobre a parte inteira, que e o caso do peitoral e
        # da calca. Escudo e ombreira sao retalhos soltos e ficam de fora.
        n = squash.get(anchor, 0)
        if n and piece.get('dy', 0) == 0 and \
                len(art) == len(DEFAULT_PART.get(anchor, art)):
            art = _squash_part(anchor, art, n)
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
        if pose.get('_eyes_shut'):
            # Morto de olho aberto fica com cara de susto, e os 2 px de
            # pupila somem no giro da queda. Fechar o olho vira uma linha
            # escura, que sobrevive a rotacao e le como morto.
            lid = {}
            for k in ('eye_l', 'pupil_l', 'eye_r', 'pupil_r'):
                for cx, cy in FACE_CELLS[k]:
                    lid[(cx, cy)] = 'd'
            for (cx, cy) in list(lid):
                if (cx, cy + 1) not in lid:
                    lid[(cx, cy)] = 'k'
            for (fx, fy), ch in lid.items():
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
