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

from collections import deque
import math

from PIL import Image

SIZE = 64

# ---------------------------------------------------------------- paleta ----
C = {
    # --- paleta extraida da propria referencia (k-means, 12 cores) ---
    # ----------------------------------------------------------------
    # A PALETA DO GOBLIN ORIGINAL DO JOGO.
    #
    # A anterior saiu de um k-means sobre um JPEG borrado: SEIS verdes
    # quase iguais, que no desenho viravam chuvisco — a cabeca ficava
    # uma mancha salpicada em vez de uma cabeca com volume.
    #
    # Estas sao as cores lidas dos proprios quadros do goblin antigo
    # (`art-source/goblins-originais/`), que e o visual que funciona
    # no jogo. Ele usa TRES verdes e tres marrons; aqui tem um verde
    # escuro a mais e um brilho a mais — e o "um pouco mais detalhado
    # que o original". Varios simbolos caem de proposito na MESMA cor:
    # e assim que os seis tons antigos colapsam em quatro e o
    # salpicado some sem ninguem redesenhar nada.
    'k': (37, 40, 39, 255),      # contorno (o cinza-escuro do original)
    'e': (40, 106, 62, 255),     # verde sombra (o tom a mais)
    'd': (69, 165, 96, 255),     # verde escuro do original
    'n': (69, 165, 96, 255),     # (mesmo tom: colapsa o chuvisco)
    'j': (80, 189, 111, 255),    # verde base do original
    'g': (80, 189, 111, 255),    # (mesmo tom)
    'l': (114, 210, 142, 255),   # verde claro do original
    'f': (226, 243, 230, 255),   # brilho / branco do olho
    'B': (98, 64, 35, 255),      # marrom escuro do original
    'b': (105, 72, 58, 255),     # marrom base do original
    'h': (145, 100, 81, 255),    # marrom claro do original
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
    'eye_l':   [(16, 13), (17, 13), (16, 14), (17, 14), (18, 14)],
    'pupil_l': [(18, 13)],
    'eye_r':   [(25, 13), (25, 14)],
    'pupil_r': [(26, 13), (27, 13), (28, 13)],
    'brow_l':  [(15, 12), (16, 12), (17, 12)],
    'brow_r':  [(24, 12), (25, 12), (26, 12)],
    'tusk':    [(21, 18), (22, 18)],
}


def _face_from_art():
    """O rosto nao e redesenhado: e lido da propria arte.

    Antes o rig pintava retangulos chapados por cima dos olhos, o que matava
    a pupila e o sombreado do original. Agora FACE devolve exatamente os
    pixels que ja estao no recorte, entao repintar e um no-op visual — ele
    existe so para que `swap` e as variacoes saibam onde o rosto fica.
    """
    out = {}
    for cells in FACE_CELLS.values():
        for x, y in cells:
            if 0 <= y < len(HEAD) and 0 <= x < len(HEAD[0]) and HEAD[y][x] != '.':
                out[(x, y)] = HEAD[y][x]
    return out


FACE = _face_from_art()

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
# Quem morre larga a arma. Ela nao fica presa na mao do corpo caido (ali ela
# saia atravessada na cabeca, parecia que tinha empalado o goblin): cai no
# chao ao lado dele, deitada, no canto livre a direita das pernas.
LAY_ARMA_CHAO = (43, 56)

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


# Rampas de tom, do escuro para o claro, por MATERIAL. A limpeza
# abaixo so compara tons dentro da mesma rampa: pele com pele, couro
# com couro. Misturar as duas pintaria a tunica de verde.
RAMPAS = (('e', 'd', 'n', 'j', 'g', 'l'), ('B', 'b', 'h'))
# De fora: contorno, brilho do olho e aco. Sao tracos de UM pixel por
# natureza; uma mediana os apagaria.
SEM_LIMPEZA = frozenset({'k', 'f', 'w', 'z', 'q', '.'})
_NA_RAMPA = {c: (r, i) for r, rampa in enumerate(RAMPAS)
             for i, c in enumerate(rampa)}


def tira_chuvisco(grid, protege=(), passadas=2):
    """Mediana 3x3 por material: apaga o ponto solto, mantem a forma.

    A arte veio de uma foto pequena e borrada e trouxe o RUIDO do
    JPEG junto: a cabeca tinha 445 pixels pintados com seis tons de
    verde salpicados um no outro. Na tela isso nao le como volume,
    le como mancha — foi a queixa de "ficou com qualidade menor".

    A mediana e o filtro que o pixel art pede: apaga o pixel solto e
    NAO borra a fronteira entre claro e escuro (a media borraria).
    Nenhum pixel muda de lugar, nenhum aparece ou some, nenhuma cor
    nova entra: muda so QUAL dos tons ja existentes ocupa cada pixel.
    E as celulas do rosto ficam de fora — e a parte que menos pode
    ser mexida.
    """
    alt, larg = len(grid), len(grid[0])
    fora = set(protege)
    out = [list(linha) for linha in grid]
    for _ in range(passadas):
        base = [linha[:] for linha in out]
        for y in range(alt):
            for x in range(larg):
                c = base[y][x]
                if c in SEM_LIMPEZA or c not in _NA_RAMPA or (x, y) in fora:
                    continue
                rampa = _NA_RAMPA[c][0]
                perto = [_NA_RAMPA[base[ny][nx]][1]
                         for dy in (-1, 0, 1) for dx in (-1, 0, 1)
                         if 0 <= (ny := y + dy) < alt
                         and 0 <= (nx := x + dx) < larg
                         and base[ny][nx] in _NA_RAMPA
                         and _NA_RAMPA[base[ny][nx]][0] == rampa]
                if len(perto) < 5:
                    continue        # borda da peca: nao se mexe
                perto.sort()
                out[y][x] = RAMPAS[rampa][perto[len(perto) // 2]]
    return [list(linha) for linha in out]


_ROSTO = {(x, y) for cells in FACE_CELLS.values() for (x, y) in cells}

DEFAULT_PART = {
    'head': tira_chuvisco(HEAD, _ROSTO),
    'torso': tira_chuvisco(TORSO),
    'arm_l': tira_chuvisco(ARM_L),
    'arm_r': tira_chuvisco(ARM_R),
    'leg_l': tira_chuvisco(LEG_L),
    'leg_r': tira_chuvisco(LEG_R),
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


# ===================================================================== #
#  ARTICULACAO: INCLINAR UMA PARTE                                      #
# ===================================================================== #
# Ate aqui cada parte do goblin so podia ser DESLOCADA inteira. Mover um
# retangulo inteiro e exatamente o que faz um boneco parecer robo: a perna
# nao dobra, ela escorrega; o braco nao balanca, ele teleporta para o lado
# e descola do ombro.
#
# `inclinar` resolve isso sem reamostrar um unico pixel: cada LINHA da
# parte anda um tanto na horizontal, crescendo do topo para a base. Com o
# topo parado e a base andando, o quadril fica colado no tronco e so o pe
# vai para a frente — e isso que le como perna balancando. Com a base
# parada e o topo andando, o corpo se inclina por cima de um pe plantado.
#
# Nao ha giro de verdade (girar pixel art em angulo qualquer destroi o
# desenho); ha cisalhamento, que em sprite pequeno le igual e e exato.


# ===================================================================== #
#  A GRADE DA TELA                                                      #
# ===================================================================== #
# Este sprite tem 64x64, mas o jogo o desenha numa caixa de 32x32 com a
# suavizacao DESLIGADA (js/world.js: drawImage(spr, -16, -30, 32, 32) e
# ctx.imageSmoothingEnabled = false). Na pratica o canvas fica com UM
# pixel a cada dois: dos 1076 pixels desenhados, 270 chegam na tela.
#
# A consequencia nao e so perder detalhe, e muito pior. Medido:
#
#   mover o goblin 1 px  ->  195 dos 270 pixels da tela mudam (72%)
#   mover o goblin 2 px  ->  ZERO mudam; a forma e identica, so que
#                            noutro lugar
#
# Com deslocamento impar o canvas passa a amostrar a outra metade da
# arte, entao rosto, contorno e roupa se REFAZEM a cada quadro. Nao e a
# animacao que fica estranha: e o desenho que ferve por baixo dela. E
# nenhuma amplitude, curva ou suavizacao conserta isso.
#
# Por isso tudo que se mexe aqui anda de dois em dois. O goblin passa a
# se comportar na tela exatamente como um sprite de 32 px feito a mao —
# que e o que o primeiro goblin era.
PASSO_TELA = 2


def na_grade(v):
    """Arredonda para o passo da grade da tela (multiplo de PASSO_TELA)."""
    return int(math.floor(v / PASSO_TELA + 0.5)) * PASSO_TELA


# Quanto de cada peca fica PLANTADO quando ela inclina.
#
# PIVO planta o ALTO, PIVO_BASE planta o BAIXO.
#
#   perna  — pivota no quadril, que e a linha de cima dela: nada plantado
#            em cima, a reta corre do quadril ao pe.
#   O par (PIVO, PIVO_BASE) define ONDE a rampa acontece. Importa muito:
#   com a rampa espalhada pela peca inteira, o meio do braco so recebe
#   um terco do movimento e a peca parece de borracha. Terminando a
#   rampa no meio, o antebraco e a mao viajam JUNTOS, inteiros — que e
#   como o braco do original se mexe (ele e um bastao de 4 linhas que
#   balanca todo).
#
#   braco  — pendura do ombro: so a primeira quinta parte fica plantada.
#            Plantar metade (como ja se tentou) congelava o braco
#            inteiro: medindo o original, a faixa do braco varia 50% da
#            altura do corpo ao longo da corrida e eu entregava 14%.
#            No original os bracos chegam a se separar do tronco — sao
#            dois bastoes apontando para os lados — entao uma frestinha
#            no ombro e fiel, desde que nada se SOLTE.
#   cabeca — pivota no PESCOCO, que e a linha de BAIXO dela. O queixo
#            fica colado no tronco e quem viaja e o alto do cranio e as
#            ORELHAS. E assim que o original mexe a cabeca: medindo os
#            quadros dele, as linhas das orelhas mudam de largura (11 a
#            13 px) enquanto o rosto quase nao sai do lugar.
# O par (PIVO, PIVO_BASE) define ONDE a rampa acontece, e importa muito:
# com a rampa espalhada pela peca inteira o meio do braco so recebe um
# terco do movimento e a peca parece de borracha. Terminando a rampa no
# meio, antebraco e mao viajam JUNTOS, inteiros — que e como o braco do
# original se mexe (la ele e um bastao de 4 linhas que balanca todo).
PIVO = {'arm_l': 0.05, 'arm_r': 0.05, 'leg_l': 0.0, 'leg_r': 0.0}

# As duas pontas de cima da cabeca, em coordenadas do desenho dela. Sao
# os dois picos das linhas 0 a 3: a linha 4 ja e o cranio inteiro e nao
# pode ser aberta, senao rasga a cabeca ao meio.
# AS DUAS ORELHAS, no desenho da cabeca. Olhando a arte ampliada:
# a esquerda e comprida e DEITADA, saindo na horizontal pela esquerda;
# a direita e EM PE, apontando para cima e para a direita; e no meio,
# entre elas, fica o topo do cranio — que nao e orelha nenhuma.
#
# Isto ja esteve errado: "orelha esquerda = tudo a esquerda da coluna
# 22" pegava o TOPO DO CRANIO junto, e mexer as orelhas duplicava a
# cabeca. Cada orelha tem agora a sua caixa, medida no desenho.
#
# `base` diz onde a orelha nasce — o lado que NAO se mexe. A ponta anda
# tudo, a base nada, e no meio o movimento e proporcional: a orelha
# gira em vez de escorregar, e por isso nunca se descola do cranio.
# `abre` e `cai` sao as direcoes que a PONTA toma. A orelha deitada nao
# tem para onde abrir na horizontal (a ponta dela ja esta na borda do
# desenho), e orelha deitada bate mesmo e para cima e para baixo; a
# orelha em pe abre para o lado.
ORELHAS = (
    {'x0': 0, 'x1': 11, 'y0': 3, 'y1': 9, 'base': 'dir',
     'abre': (0, -1), 'cai': (0, 1)},
    # a orelha em pe NAO abaixa: o que se mede no original e a
    # diferenca entre as duas pontas (a esquerda fica mais baixa que a
    # direita), entao quem cai e so a deitada. Abaixando as duas, a em
    # pe era espremida contra o cranio e a cabeca perdia 16 px.
    {'x0': 23, 'x1': 35, 'y0': 0, 'y1': 6, 'base': 'baixo',
     'abre': (1, 0), 'cai': (0, 0)},
)

PIVO_BASE = {'head': 0.5, 'arm_l': 0.45, 'arm_r': 0.45,
             'leg_l': 0.3, 'leg_r': 0.3}


def abrir_orelhas(art, d, cai=0):
    """Mexe as duas orelhas: `d` abre para os lados, `cai` abaixa a ponta.

    O original mexe as orelhas e nao as mexe juntas. Alinhando os
    quadros dele pelo topo do corpo, a largura da faixa das pontas vai
    de 11 a 13 px (elas abrem e fecham) e em varios quadros uma esta
    uma linha abaixo da outra.

    Inclinar a cabeca nao reproduz nada disso: inclinar TRANSLADA as
    duas pontas juntas e a largura fica igual. Aqui cada orelha gira em
    torno da propria base.

    Girar, e nao escorregar, e o que mantem a orelha presa: a base fica
    exatamente onde estava, encostada no cranio, e so a ponta viaja.
    """
    if not d and not cai:
        return art
    out = [list(r) for r in art]
    alt, larg = len(art), len(art[0])
    for o in ORELHAS:
        x0, x1 = o['x0'], min(o['x1'], larg - 1)
        y0, y1 = o['y0'], min(o['y1'], alt - 1)
        if x1 <= x0 or y1 <= y0:
            continue

        def peso(y, x):
            """1 na ponta da orelha, 0 na base. A base nao anda."""
            if o['base'] == 'dir':
                return (x1 - x) / (x1 - x0)
            if o['base'] == 'esq':
                return (x - x0) / (x1 - x0)
            return (y1 - y) / (y1 - y0)

        # AMOSTRAGEM INVERSA: para cada celula do destino procura-se de
        # onde ela veio, em vez de empurrar cada celula da origem para a
        # frente. Empurrando, as colunas vizinhas andam quantidades
        # diferentes (e disso que a orelha gira) e sobram colunas vazias
        # no meio dela — uma fenda. Puxando, todo destino recebe alguem.
        ax, ay = o['abre']
        cx, cy = o['cai']
        # A varredura vai ALEM da caixa, na direcao em que a orelha
        # anda. Parando na borda da caixa, a parte que saiu dela sumia:
        # a orelha abaixada perdia as linhas de baixo e encolhia 20 px.
        folga = max(abs(d), abs(cai))
        for y in range(y0 - folga, y1 + folga + 1):
            for x in range(x0 - folga, x1 + folga + 1):
                if not (0 <= y < alt and 0 <= x < larg):
                    continue
                w = peso(min(max(y, y0), y1), min(max(x, x0), x1))
                # NA GRADE DA TELA. A rampa dava deslocamentos de 1 px,
                # e 1 px aqui e MEIO pixel de tela: o desenho reamostra,
                # muda de forma sozinho e a orelha chega a se descolar
                # do cranio na reducao. Todo o resto do rig ja anda de 2
                # em 2 (ver na_grade); a orelha era a excecao esquecida.
                sx = x - na_grade(d * w) * ax - na_grade(cai * w) * cx
                sy = y - na_grade(d * w) * ay - na_grade(cai * w) * cy
                na_caixa = (x0 <= x <= x1 and y0 <= y <= y1)
                if x0 <= sx <= x1 and y0 <= sy <= y1 and art[sy][sx] != '.':
                    out[y][x] = art[sy][sx]
                elif na_caixa:
                    out[y][x] = '.'
    return out


def mexe_orelhas(art, esq=0, dir=0):
    """Mexe as orelhas SEM reamostrar: cada uma anda em bloco inteiro.

    A versao antiga interpolava celula a celula (uma rampa da base ate
    a ponta) e era disso que vinha a orelha borrada. Aqui o bloco da
    ponta anda de uma vez, em 2 px — um pixel de tela — e as duas
    fileiras junto da cabeca ficam onde estao. O resultado e uma
    dobra, igual a de uma orelha de verdade, com o desenho intacto.

    `esq` sobe/desce a ponta da orelha deitada (a da esquerda);
    `dir` balanca de lado a orelha em pe (a da direita).
    """
    if not esq and not dir:
        return art
    alt, larg = len(art), len(art[0])
    out = [list(linha) for linha in art]

    def move(celulas, dx, dy):
        tirados = {}
        for x, y in celulas:
            tirados[(x, y)] = out[y][x]
            out[y][x] = '.'
        for (x, y), ch in tirados.items():
            nx, ny = x + dx, y + dy
            if ch != '.' and 0 <= nx < larg and 0 <= ny < alt:
                out[ny][nx] = ch

    if esq:
        # orelha deitada: a ponta (colunas 0-9) sobe ou desce; as duas
        # colunas da base ficam presas no cranio
        move([(x, y) for y in range(3, 10) for x in range(0, 10)], 0, esq)
    if dir:
        # orelha em pe: o alto (linhas 0-4) balanca de lado; a base
        # fica no cranio
        move([(x, y) for y in range(0, 5) for x in range(23, 36)], dir, 0)
    return out


def mapa_orelhas(d, cai):
    """Para onde cada celula das orelhas foi parar.

    As marcas das variacoes (brinco, corte na orelha, anel) sao pintadas
    em coordenadas da cabeca DEPOIS que ela ja foi desenhada. Sem este
    mapa, mexer a orelha deixa o brinco parado no ar e ele vira um
    pedaco solto. Mesmo problema, e mesma solucao, do `_desl` da
    inclinacao: uma funcao so, valendo para qualquer marca.
    """
    if not d and not cai:
        return {}
    mapa = {}
    for o in ORELHAS:
        x0, x1, y0, y1 = o['x0'], o['x1'], o['y0'], o['y1']
        ax, ay = o['abre']
        cx, cy = o['cai']
        # A zona vai 3 linhas ABAIXO da orelha. O que pendura dela — a
        # argola do brinco — fica fora da caixa, e sem isto a argola se
        # partia em duas: a metade de cima acompanhava a orelha e a de
        # baixo ficava no ar. O peso e o da borda da caixa, entao o que
        # pendura anda exatamente junto com o lobo de onde pendura.
        for y in range(y0, y1 + 4):
            for x in range(x0, x1 + 1):
                yc = min(y, y1)
                if o['base'] == 'dir':
                    w = (x1 - x) / (x1 - x0)
                elif o['base'] == 'esq':
                    w = (x - x0) / (x1 - x0)
                else:
                    w = (y1 - yc) / (y1 - y0)
                mapa[(x, y)] = (
                    x + na_grade(d * w) * ax + na_grade(cai * w) * cx,
                    y + na_grade(d * w) * ay + na_grade(cai * w) * cy)
    return mapa


# POR QUE NAO EXISTE MAIS UM "ESTICA O OMBRO" AQUI
#
# Houve uma versao em que o ombro e o quadril se alongavam para
# acompanhar o membro, repetindo a cor da propria linha. Fechava a
# fenda, mas ALARGAVA o desenho: o braco ganhava colunas que o artista
# nao pintou e o goblin engordava um pouco a cada quadro. Era parte da
# queixa de "tem pixels a mais e a qualidade caiu".
#
# A fenda sumiu de outro jeito, sem acrescentar nada: o membro anda
# INTEIRO (ver goblin_anim: topo == base), entao o ombro continua
# encaixado no tronco exatamente como no desenho parado, so que 2 px
# para o lado. Membro rigido nao abre junta.


def deslocamento(h, topo, base, pivo=0.0, pivo_base=0.0):
    """Quanto CADA linha de uma peca de altura `h` anda ao inclinar.

    Uma fonte unica: a arte, o equipamento que veste a peca, o rosto
    pintado por cima e as marcas das variacoes tem de usar exatamente
    esta lista, senao um desliza em relacao ao outro. Ja aconteceu do
    rosto ficar fora da cabeca.
    """
    if h <= 0:
        return []
    if h == 1:
        return [na_grade(topo)]
    vao = max(1e-6, 1.0 - pivo - pivo_base)
    out = []
    for i in range(h):
        t = i / (h - 1)
        u = min(max((t - pivo) / vao, 0.0), 1.0)
        # cada linha tambem tem de cair na grade da tela, senao a
        # inclinacao reserra o desenho linha sim, linha nao
        out.append(na_grade(topo + (base - topo) * u))
    return out


def inclinar(art, topo, base, pivo=0.0, pivo_base=0.0):
    """Desloca cada linha da arte: `topo` px na primeira, `base` na ultima.

    Devolve (arte_nova, dx) — a arte cresce para os dois lados para nada
    ser cortado, e `dx` e o quanto o blit precisa recuar para compensar.
    """
    if not art or (topo == 0 and base == 0):
        return art, 0
    m = max(abs(topo), abs(base))
    ds = deslocamento(len(art), topo, base, pivo, pivo_base)
    out = []
    for row, d in zip(art, ds):
        d = d + m
        out.append(['.'] * d + list(row) + ['.'] * (2 * m - d))
    return out, -m


def inclinar_em(art, topo, base, altura, linha0, pivo=0.0,
                pivo_base=0.0):
    """Mesma inclinacao, mas para uma peca que cobre so parte da altura.

    A armadura tem de acompanhar a perna que ela veste. Como a calca comeca
    na linha `linha0` da parte e nao no topo, o deslocamento dela e lido da
    MESMA reta da parte inteira — senao a calca inclina num angulo e a
    perna noutro, e a peca sai de cima do corpo.
    """
    if not art or (topo == 0 and base == 0) or altura < 2:
        return art, 0
    m = max(abs(topo), abs(base))
    ds = deslocamento(altura, topo, base, pivo, pivo_base)
    out = []
    for i, row in enumerate(art):
        d = ds[min(max(linha0 + i, 0), altura - 1)] + m
        out.append(['.'] * d + list(row) + ['.'] * (2 * m - d))
    return out, -m


# Faixa de cada parte que pode comprimir. So o tronco agacha, e so da
# cintura para baixo: as linhas 14-19 do desenho sao a barra da calca e as
# coxas. Comprimir mais acima comeria a calca inteira e o goblin parecia
# que estava perdendo a roupa, nao dobrando o joelho.
SQUASH_BAND = {'torso': (14, 20)}


def _squash_part(name, art, n):
    lo, hi = SQUASH_BAND.get(name, (len(art) // 2, len(art) - 1))
    return squash_rows(art, n, lo, hi)


# ===================================================================== #
#  AS MARCAS DA VARIACAO NO CORPO CAIDO                                 #
# ===================================================================== #
# O goblin caido e UM desenho inteiro (LAY), nao as partes remontadas,
# entao os tracos das variacoes — que sao escritos em coordenadas da
# cabeca, do torso e dos bracos — nao tinham onde se encaixar: so a troca
# de paleta sobrevivia a morte, e um goblin sem orelha caia com as duas.
#
# Desenhar os 45 caidos a mao seriam 45 x 12 = 540 quadros novos. Em vez
# disso esta funcao LE o que a variacao mudou no goblin de pe e reposiciona
# esses mesmos pixels no corpo deitado, pela transformacao que leva um
# desenho no outro. Qualquer traco — os de hoje e os que vierem — ja cai no
# lugar certo sozinho, do mesmo jeito que a arma encaixa em qualquer goblin.

# Dois pontos de referencia medidos nos dois desenhos: o centro da cabeca
# e o centro do couro (macacao + botas). Duas duplas de pontos bastam para
# fixar rotacao, escala e deslocamento.
REF_PE = ((31.36, 29.54), (29.09, 53.50))
REF_DEITADO = ((45.96, 36.13), (26.03, 45.81))

# O goblin cai de BRUCOS. Tudo que e rosto (linhas 12-19 da cabeca) fica
# contra o chao e nao se ve: olho, presa, tatuagem da bochecha, marca de
# nascenca, queimadura. O que esta no alto do cranio e nas orelhas —
# atadura, bandana, argola, orelha cortada — continua aparecendo.
ROSTO_BOX = (13, 32, 49, 40)


def _similaridade(a0, a1, b0, b1):
    """Leva o par de pontos (a0,a1) no par (b0,b1): giro + escala + offset.

    Devolve (ida, volta); cada uma e uma funcao (x, y) -> (x, y) em float.
    """
    ax, ay = a1[0] - a0[0], a1[1] - a0[1]
    bx, by = b1[0] - b0[0], b1[1] - b0[1]
    den = ax * ax + ay * ay
    # numero complexo (c + di) tal que (ax+ay*i) * (c+di) = (bx+by*i)
    c = (ax * bx + ay * by) / den
    d = (ax * by - ay * bx) / den

    def ida(x, y):
        dx, dy = x - a0[0], y - a0[1]
        return (b0[0] + c * dx - d * dy, b0[1] + d * dx + c * dy)

    det = c * c + d * d

    def volta(x, y):
        dx, dy = x - b0[0], y - b0[1]
        return (a0[0] + (c * dx + d * dy) / det,
                a0[1] + (c * dy - d * dx) / det)

    return ida, volta


DEITAR, LEVANTAR = _similaridade(REF_PE[0], REF_PE[1],
                                 REF_DEITADO[0], REF_DEITADO[1])


def _diferenca_de_pe(variation, extra_parts):
    """O que a variacao muda no goblin DE PE: {(x,y): char ou None}."""
    limpo = compose(base_pose())
    marcado = compose(base_pose(), variation=variation,
                      extra_parts=extra_parts)
    x0, y0, x1, y1 = ROSTO_BOX
    out = {}
    for y in range(SIZE):
        for x in range(SIZE):
            if marcado[y][x] == limpo[y][x]:
                continue
            if x0 <= x < x1 and y0 <= y < y1:
                continue                      # rosto: de brucos nao se ve
            out[(x, y)] = marcado[y][x]       # None = o traco APAGOU o pixel
    return out


def _varrer_restos(marcas):
    """Apaga os cacos que o corte deixou soltos no corpo caido.

    Tirar uma orelha do goblin deitado as vezes separa a pontinha do resto
    do corpo, e ela fica boiando ao lado. Aqui o corpo ja cortado e varrido
    por vizinhanca: o que nao estiver ligado ao bloco maior sai junto.
    """
    apagados = {(x, y) for x, y, ch in marcas if ch is None}
    if not apagados:
        return marcas
    corpo = {(x, y) for y in range(SIZE) for x in range(SIZE)
             if LAY[y][x] != '.' and (x, y) not in apagados}
    if not corpo:
        return marcas
    inicio = max(corpo, key=lambda p: sum(
        1 for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (p[0] + dx, p[1] + dy) in corpo))
    vistos, fila = {inicio}, [inicio]
    while fila:
        x, y = fila.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in corpo and (nx, ny) not in vistos:
                vistos.add((nx, ny))
                fila.append((nx, ny))
    restos = corpo - vistos
    if not restos:
        return marcas
    marcas = [m for m in marcas if (m[0], m[1]) not in restos]
    return marcas + [(x, y, None) for x, y in restos]


_CACHE_DEITADO = {}


def marcas_deitadas(variation, extra_parts=None):
    """Lista [(x, y, char)] das marcas da variacao sobre o corpo caido.

    O mapeamento e feito ao CONTRARIO (para cada pixel do corpo deitado,
    pergunta de onde ele veio no goblin de pe). Mapear para a frente
    deixaria buracos: a escala entre os dois desenhos e menor que 1, entao
    varios pixels de origem caem no mesmo destino e sobram vazios no meio
    de uma atadura.
    """
    chave = (id(variation), id(extra_parts))
    achado = _CACHE_DEITADO.get(chave)
    if achado is not None:
        return achado[2]
    dif = _diferenca_de_pe(variation, extra_parts)
    out = []
    for y in range(SIZE):
        for x in range(SIZE):
            if LAY[y][x] == '.':
                continue
            sx, sy = LEVANTAR(x, y)
            ch = dif.get((int(round(sx)), int(round(sy))), False)
            if ch is False:
                continue
            out.append((x, y, ch))
    out = _varrer_restos(out)
    # guarda tambem as proprias referencias: enquanto elas viverem o id()
    # nao pode ser reaproveitado por outro objeto e a chave continua valida
    _CACHE_DEITADO[chave] = (variation, extra_parts, out)
    return out


def compose(pose, variation=None, swap=None, extra_parts=None, overlay=None,
            gear=None, costurar=True):
    """Monta um quadro. Retorna o buffer de chars (ainda nao convertido)."""
    extra_parts = extra_parts or {}
    squash = pose.get('_squash') or {}
    shear = pose.get('_shear') or {}
    alturas = {}
    buf = _blank()
    head_pos = None
    ctx = {}

    if pose.get('_lay') is not None:
        # Corpo caido: um desenho inteiro, nao as partes remontadas. A pose
        # so diz onde ele encosta no quadro (o quique ao bater no chao).
        lx, ly = pose['_lay']
        _blit(buf, LAY, lx, ly)
        # as marcas da variacao, reposicionadas no corpo caido
        if variation is not None or extra_parts:
            for mx, my, ch in marcas_deitadas(variation, extra_parts):
                x, y = lx + mx, ly + my
                if 0 <= x < SIZE and 0 <= y < SIZE:
                    buf[y][x] = ch
        ctx['lay'] = (lx, ly, False)
        ctx['sword'] = (lx + LAY_ARMA_CHAO[0], ly + LAY_ARMA_CHAO[1], False)
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
            if name == 'head' and (pose.get('_ears')
                                   or pose.get('_ear_drop')):
                # bloco inteiro, 2 px: ver mexe_orelhas
                art = mexe_orelhas(art, pose.get('_ears') or 0,
                                   pose.get('_ear_drop') or 0)
            if squash.get(name):
                art = _squash_part(name, art, squash[name])
        bx, by = REST[name]
        ox, oy = bx + dx, by + dy
        inc = shear.get(name)
        if inc and name != 'sword':
            alturas[name] = len(art)
            # Guarda o quanto CADA linha desta peca andou. As marcas das
            # variacoes (verruga, cicatriz, brinco, corte na orelha...)
            # sao pintadas em coordenadas da peca, depois que ela ja foi
            # desenhada. Sem esta lista elas ficam na reta antiga e se
            # soltam do corpo assim que a peca inclina. Uma funcao so,
            # valendo para qualquer marca em qualquer peca.
            m_ = max(abs(inc[0]), abs(inc[1]))
            ctx.setdefault('_desl', {})[name] = [
                d + m_ for d in deslocamento(
                    len(art), inc[0], inc[1], PIVO.get(name, 0.0),
                    PIVO_BASE.get(name, 0.0))]
            art, sdx = inclinar(art, inc[0], inc[1], PIVO.get(name, 0.0),
                                PIVO_BASE.get(name, 0.0))
            ox += sdx
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
        # a peca inclina junto com a parte que veste
        inc = shear.get(anchor)
        if inc and anchor in alturas:
            art, sdx = inclinar_em(art, inc[0], inc[1], alturas[anchor],
                                   piece.get('dy', 0),
                                   PIVO.get(anchor, 0.0),
                                   PIVO_BASE.get(anchor, 0.0))
            gx += sdx
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
        # Se a cabeca inclinou, o rosto tem de inclinar com ela. As
        # celulas do rosto estao em coordenadas da cabeca NAO inclinada,
        # entao cada uma anda o que a linha dela andou — a mesma lista
        # que a arte usou. Sem isso o rosto escorrega para fora da cara.
        fdesl = ctx.get('_desl', {}).get('head')
        face = dict(FACE)
        if swap:
            face = {k: swap.get(v, v) for k, v in face.items()}
        for (fx, fy), ch in face.items():
            x = hx + (HEAD_W - 1 - fx if hflip else fx)
            y = hy + fy
            if fdesl and 0 <= fy < len(fdesl):
                x += -fdesl[fy] if hflip else fdesl[fy]
            if (0 <= x < SIZE and 0 <= y < SIZE
                    and buf[y][x] is not None and (x, y) not in gear_mask):
                buf[y][x] = ch
        rosto = pose.get('_rosto')
        if rosto:
            # A CARA MUDA. Ate aqui o goblin batia e levava pancada com
            # a mesma expressao de quem esta parado — e o rosto e a
            # primeira coisa que o olho procura. Sao poucos pixels,
            # todos com cores que ja existem no desenho, e so dentro da
            # caixa do rosto: nada aqui mexe na silhueta.
            marca = {}
            if rosto == 'bravo':
                # sobrancelha fechada sobre o olho e boca aberta de
                # quem esta fazendo forca
                for k in ('brow_l', 'brow_r'):
                    for cx, cy in FACE_CELLS[k]:
                        marca[(cx, cy)] = 'k'
                for cx in range(19, 24):
                    marca[(cx, 19)] = 'k'
            elif rosto == 'dor':
                # olho apertado (uma linha escura) e boca aberta
                for k in ('eye_l', 'pupil_l', 'eye_r', 'pupil_r'):
                    for cx, cy in FACE_CELLS[k]:
                        marca[(cx, cy)] = 'd'
                for (cx, cy) in list(marca):
                    if (cx, cy + 1) not in marca:
                        marca[(cx, cy)] = 'k'
                for cx in range(19, 24):
                    marca[(cx, 19)] = 'k'
                    marca[(cx, 18)] = 'k' if cx in (19, 23) else marca.get(
                        (cx, 18), None) or 'k'
            for (fx, fy), ch in marca.items():
                x = hx + (HEAD_W - 1 - fx if hflip else fx)
                y = hy + fy
                if fdesl and 0 <= fy < len(fdesl):
                    x += -fdesl[fy] if hflip else fdesl[fy]
                if (0 <= x < SIZE and 0 <= y < SIZE
                        and buf[y][x] is not None
                        and (x, y) not in gear_mask):
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
                if fdesl and 0 <= fy < len(fdesl):
                    x += -fdesl[fy] if hflip else fdesl[fy]
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
    if costurar:
        _fecha_buracos(buf)
        _solda_carne(buf)
    _tira_lascas(buf)
    return buf


def _fecha_buracos(buf, limite=60):
    """Tapa com contorno qualquer fundo que tenha ficado PRESO no corpo.

    Quando o braco balanca, a fresta entre ele e o tronco fecha em cima
    (no ombro) e embaixo (no quadril) e vira um buraco: um talho
    transparente no meio do goblin, por onde se ve o mundo atras dele.
    Correndo chegavam a 30 px por quadro.

    Nao da para simplesmente encostar o braco no tronco — era isso que
    o mantinha congelado. E nao da para preencher com pele, que fundiria
    o braco no peito. O que resolve e o que o pixel art faz: a fresta
    presa vira CONTORNO, e ai ela le como a linha que separa o braco do
    corpo, em vez de um furo.

    O buraco vira SOMBRA da cor que o cerca, nunca contorno puro. Tapar
    com contorno (a primeira versao disto) construia uma parede preta
    entre o braco e o peito: o sprite continuava sendo uma peca so para
    o teste de conectividade, mas a CARNE ficava partida em duas e o
    olho via um braco flutuando ao lado do corpo. Com a sombra da
    propria pele a fresta le como vinco e o braco continua presente.

    So fecha buraco pequeno. Um vazio grande e o vao entre as pernas ou
    algo que deu muito errado, e nos dois casos tapar seria pior.
    """
    vazio = [[buf[y][x] is None for x in range(SIZE)] for y in range(SIZE)]
    fora = [[False] * SIZE for _ in range(SIZE)]
    fila = deque()
    for y in range(SIZE):
        for x in range(SIZE):
            if (y in (0, SIZE - 1) or x in (0, SIZE - 1)) \
                    and vazio[y][x] and not fora[y][x]:
                fora[y][x] = True
                fila.append((y, x))
    while fila:
        y, x = fila.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < SIZE and 0 <= nx < SIZE \
                    and vazio[ny][nx] and not fora[ny][nx]:
                fora[ny][nx] = True
                fila.append((ny, nx))

    visto = [[False] * SIZE for _ in range(SIZE)]
    for y0 in range(SIZE):
        for x0 in range(SIZE):
            if not vazio[y0][x0] or fora[y0][x0] or visto[y0][x0]:
                continue
            pilha = [(y0, x0)]
            visto[y0][x0] = True
            buraco = []
            while pilha:
                y, x = pilha.pop()
                buraco.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < SIZE and 0 <= nx < SIZE and vazio[ny][nx] \
                            and not fora[ny][nx] and not visto[ny][nx]:
                        visto[ny][nx] = True
                        pilha.append((ny, nx))
            if len(buraco) > limite:
                continue
            # FRESTA ESTREITA VIRA CONTORNO; buraco largo vira sombra.
            #
            # Quando o braco se afasta 2 px do tronco, o que se abre
            # nao e um buraco: e a fenda entre o braco e o corpo, e no
            # pixel art ela se desenha com a MESMA linha de contorno
            # que ja contorna o goblin inteiro. Pintando-a de verde
            # escuro (como se fazia aqui) nascia uma mancha de pele que
            # o artista nunca pos — eram ~24 px por quadro so no
            # ataque, e e disso que vinha a impressao de "pixels verdes
            # a mais". Com o contorno, zero cor nova entra no sprite.
            larg = max(x for _, x in buraco) - min(x for _, x in buraco) + 1
            alt = max(y for y, _ in buraco) - min(y for y, _ in buraco) + 1
            if min(larg, alt) <= 3:
                for y, x in buraco:
                    buf[y][x] = 'k'
                continue
            # a cor mais escura entre as que encostam no buraco, fora o
            # contorno — e a sombra natural daquele ponto do corpo
            vizinhas = set()
            for y, x in buraco:
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < SIZE and 0 <= nx < SIZE:
                        c = buf[ny][nx]
                        if c is not None and c != 'k' and c in C:
                            vizinhas.add(c)
            if not vizinhas:
                continue
            sombra = min(vizinhas, key=lambda c: sum(C[c][:3]))
            for y, x in buraco:
                buf[y][x] = sombra


def _carne(buf):
    """Mascara do corpo SEM o contorno. E isto que o jogador enxerga."""
    return [[buf[y][x] is not None and buf[y][x] != 'k'
             for x in range(SIZE)] for y in range(SIZE)]


def _componentes(mascara, lado=None):
    """Pedacos 4-conexos de uma mascara, do maior para o menor."""
    lado = lado or SIZE
    visto = [[False] * lado for _ in range(lado)]
    saida = []
    for y0 in range(lado):
        for x0 in range(lado):
            if not mascara[y0][x0] or visto[y0][x0]:
                continue
            visto[y0][x0] = True
            pilha = [(y0, x0)]
            celulas = []
            while pilha:
                y, x = pilha.pop()
                celulas.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < lado and 0 <= nx < lado \
                            and mascara[ny][nx] and not visto[ny][nx]:
                        visto[ny][nx] = True
                        pilha.append((ny, nx))
            saida.append(celulas)
    saida.sort(key=len, reverse=True)
    return saida


def vista_de_tela(buf, fx=0, fy=0):
    """O sprite COMO O JOGO DESENHA: uma coluna e uma linha sim, outra nao.

    `fx`/`fy` sao a FASE da amostragem. Ela nao e fixa: depende de onde
    a camera parou e de como cada motor arredonda. O Pillow pega os
    impares, o canvas pode pegar os pares. Entao as quatro combinacoes
    tem de estar inteiras — garantir so uma delas e deixar o jogo
    quebrado em tres de cada quatro posicoes do goblin.

    `js/world.js` faz drawImage(sprite64, -16, -30, 32, 32) com a
    suavizacao desligada, e isso amostra uma coluna e uma linha sim,
    outra nao. Metade do desenho nunca chega ao monitor.

    E por isso que conferir o sprite de 64 engana: uma solda de 1 px
    pode cair inteira na coluna impar e sumir. Toda verificacao de
    "esta grudado?" tem de ser feita aqui.
    """
    return [[buf[y][x] for x in range(fx, SIZE, 2)]
            for y in range(fy, SIZE, 2)]


def _solda_carne(buf, minimo=3, ponte_max=3):
    """Religa, NA TELA, a carne de um membro que ficou ilhado.

    Duas armadilhas ja custaram caro aqui, as duas por medir no lugar
    errado:

    1. O teste de "uma peca so" olhava todo pixel, contorno incluido.
       Dois pedacos grudados por uma parede preta passavam nele, mas o
       jogador nao ve contorno como corpo: ele ve um braco flutuando.
    2. Corrigido o item 1, a solda foi feita no sprite de 64 e tinha
       1 px de largura — some na reducao para 32. No sprite estava
       colado; na tela, solto. Os 47 quadros do jogo estavam partidos
       com o teste verde.

    Entao a conta e feita na vista de tela e cada celula soldada volta
    como um bloco 2x2 no sprite, que e o unico tamanho que sobrevive.
    A ponte atravessa contorno de graca e, se precisar, ate um pouco de
    fundo — um membro que so encosta no corpo na diagonal nao esta
    preso, e e melhor acrescentar dois pixels de pele do que deixar o
    braco voando.
    """
    for fy in (0, 1):
        for fx in (0, 1):
            _solda_em(buf, SIZE // 2, ponte_max, minimo, fx, fy)
    # ... e de novo na resolucao cheia. Uma parede de contorno de 1 px
    # desaparece na reducao: o membro fica preso na tela de 32 e solto
    # no sprite de 64, que e o que aparece em monitor de alta
    # densidade. As duas escalas tem de estar costuradas.
    #
    # Nesta segunda passada a ponte NAO pode atravessar fundo e so vale
    # para ilha grande. Deixando-a inventar pele sobre o fundo, ela
    # criava farpas de 1 px que, reduzidas para a tela, viravam ilhas
    # NOVAS — a correcao de 64 estragava a de 32.
    _solda_em(buf, SIZE, ponte_max=0, minimo=10)


def _solda_em(buf, lado, ponte_max=3, minimo=3, fx=0, fy=0):
    """Uma passada de solda numa escala: `lado` 32 e a tela, 64 o sprite."""
    passo = SIZE // lado

    def pinta(cx, cy, cor):
        for dy in range(passo):
            for dx in range(passo):
                y = cy * passo + dy + (fy if passo == 2 else 0)
                x = cx * passo + dx + (fx if passo == 2 else 0)
                if 0 <= y < SIZE and 0 <= x < SIZE:
                    buf[y][x] = cor

    for _ in range(4):                     # uma ilha por volta
        tela = (vista_de_tela(buf, fx, fy) if passo == 2
                else [list(linha) for linha in buf])
        # A CONTA E FEITA NA SILHUETA, CONTORNO INCLUIDO.
        #
        # Por muito tempo foi feita so na carne (sem o 'k'), com o
        # argumento de que o jogador nao ve contorno como corpo. E
        # falso: um fio preto entre o tronco e a perna e uma DOBRA,
        # todo mundo desenha assim — tanto que a arte original, do
        # jeito que o artista entregou e sem pose nenhuma, ja tem duas
        # "ilhas" de carne. Perseguir esse criterio era perseguir um
        # defeito que nao existe, e o preco foi alto: a solda pintava
        # 20 px por quadro e a arte chegou a ser reescrita para
        # agradar a metrica. Dai "tem pixels a mais" e "voce mudou o
        # sprite".
        #
        # Membro solto de verdade e membro com FUNDO em volta. E isso
        # — e so isso — que esta solda conserta agora.
        corpo_mask = [[c is not None for c in linha] for linha in tela]
        partes = _componentes(corpo_mask, lado)
        if len(partes) < 2:
            return
        ilha = next((p for p in partes[1:] if len(p) >= minimo), None)
        if ilha is None:
            return
        corpo = set(partes[0])

        # custo: contorno nao custa nada, fundo custa 1 (e limitado)
        import heapq
        dist = {}
        fila = []
        for cel in ilha:
            dist[cel] = 0
            heapq.heappush(fila, (0, cel))
        veio = {cel: None for cel in ilha}
        destino = None
        while fila:
            d, (y, x) = heapq.heappop(fila)
            if d > dist.get((y, x), 1e9):
                continue
            if (y, x) in corpo:
                destino = (y, x)
                break
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if not (0 <= ny < lado and 0 <= nx < lado):
                    continue
                c = tela[ny][nx]
                # NAO chamar de `passo`: esse nome ja e o tamanho do
                # bloco que a solda pinta. Sobrescrito aqui, `pinta`
                # desenhava um bloco de zero pixel e a solda inteira
                # virava enfeite — com o teste acusando o membro solto.
                custo = 0 if c == 'k' else (1 if c is None else 0)
                nd = d + custo
                if nd > ponte_max or nd >= dist.get((ny, nx), 1e9):
                    continue
                dist[(ny, nx)] = nd
                veio[(ny, nx)] = (y, x)
                heapq.heappush(fila, (nd, (ny, nx)))
        if destino is None:
            return

        caminho = []
        no = veio[destino]
        while no is not None and no not in set(ilha):
            caminho.append(no)
            no = veio[no]
        if not caminho:
            return
        for cy, cx in caminho:
            vizinhas = set()
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < lado and 0 <= nx < lado:
                    c = tela[ny][nx]
                    if c is not None and c != 'k' and c in C:
                        vizinhas.add(c)
            if vizinhas:
                pinta(cx, cy, min(vizinhas, key=lambda c: sum(C[c][:3])))


def _tira_lascas(buf, limite=2):
    """Apaga lasquinhas de 1-2 px que ficaram soltas do corpo.

    Guarda geral, e de proposito: as marcas das variacoes apagam e
    pintam pixels na borda (o corte da orelha tira pedaco de verdade), e
    quando a peca inclina um desses pixels pode cair isolado — fica uma
    sujeirinha boiando ao lado do goblin. Em vez de remendar traco por
    traco, qualquer sobra minuscula desencostada some aqui.

    So lasca: um pedaco solto MAIOR que `limite` continua passando e
    quebrando o teste, porque ai e membro descolando, nao sujeira.
    """
    visto = [[False] * SIZE for _ in range(SIZE)]
    pedacos = []
    for y0 in range(SIZE):
        for x0 in range(SIZE):
            if buf[y0][x0] is None or visto[y0][x0]:
                continue
            pilha = [(y0, x0)]
            visto[y0][x0] = True
            atual = []
            while pilha:
                y, x = pilha.pop()
                atual.append((y, x))
                for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    ny, nx = y + dy, x + dx
                    if (0 <= ny < SIZE and 0 <= nx < SIZE
                            and buf[ny][nx] is not None and not visto[ny][nx]):
                        visto[ny][nx] = True
                        pilha.append((ny, nx))
            pedacos.append(atual)
    if len(pedacos) < 2:
        return
    pedacos.sort(key=len, reverse=True)
    for pedaco in pedacos[1:]:
        if len(pedaco) <= limite:
            for y, x in pedaco:
                buf[y][x] = None


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
