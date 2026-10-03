#!/usr/bin/env python3
"""
As 45 aparencias do goblin, montadas a partir de tracos atomicos.

Em vez de 45 desenhos independentes, cada aparencia e uma receita: uma lista
de tracos (cicatriz, tapa-olho, queimadura, ataduras, albinismo, ...). Isso
mantem o mesmo goblin por baixo de todas elas e garante que o traco aparece
igual nos 62 quadros, em qualquer pose, porque e aplicado em coordenadas
relativas a cabeca/braco de CADA quadro — nao em pixels fixos do canvas.

Tres tipos de traco:
  swap   -> troca global de paleta (albinismo, goblin encardido)
  parts  -> altera a silhueta (orelha arrancada)
  detail -> pinta pixels sobre o quadro ja contornado (o caso mais comum)
"""

import copy

import goblin_rig as R

# Cores extras usadas so pelas variacoes.
R.C.update({
    # Tons escolhidos para bater com os sprites ORIGINAIS do repositorio:
    # albino rosado, tatuagem azul, queimadura avermelhada.
    'A': (234, 214, 208, 255),   # pele albina
    'a': (250, 240, 236, 255),   # pele albina luz
    'E': (190, 164, 160, 255),   # pele albina sombra
    'P': (112, 66, 124, 255),    # mancha de nascenca
    'v': (64, 42, 80, 255),      # veias amaldicoadas
    'G': (188, 150, 46, 255),    # ouro sombra
    'U': (92, 62, 66, 255),      # contorno do albino (marrom escuro)
    'F': (158, 126, 126, 255),   # sombra funda do albino
    'I': (58, 92, 170, 255),     # tatuagem azul
    'J': (32, 52, 110, 255),     # tatuagem azul escura
    'Q': (168, 58, 44, 255),     # queimadura
    'Z': (226, 96, 70, 255),     # queimadura viva (centro)
    'X': (184, 180, 166, 255),   # sombra de atadura
    'u': (240, 206, 104, 255),   # ouro luz
    'V': (156, 96, 176, 255),    # marca de nascenca luz
    't': (104, 150, 226, 255),   # tatuagem luz
    'x': (54, 54, 62, 255),      # couro do tapa-olho (brilho)
})

# Mapa da cabeca (36x20), lido da arte de referencia em 64x64:
#   cranio cols 12..30 | orelha esquerda cols 0..13, direita cols 24..35
#   testa rows 8..12 | olhos rows 13-14 | focinho rows 15..17
#   boca/dente row 18 | queixo row 19
EYE_L = R.FACE_CELLS['eye_l']
EYE_R = R.FACE_CELLS['eye_r']
PUPIL_L = R.FACE_CELLS['pupil_l']
PUPIL_R = R.FACE_CELLS['pupil_r']
BROW_L = R.FACE_CELLS['brow_l']
BROW_R = R.FACE_CELLS['brow_r']
TUSK = R.FACE_CELLS['tusk']
FOREHEAD = [(x, y) for y in range(8, 13) for x in range(12, 28)]
CROWN = [(x, y) for y in range(1, 7) for x in range(13, 30)]
EAR_L_CORE = [(x, y) for y in (5, 6, 7) for x in range(2, 11)]
EAR_R_CORE = [(x, y) for y in (4, 5, 6, 7) for x in range(28, 34)]
EAR_L_LOBE = [(1, 7), (2, 7)]
EAR_R_LOBE = [(33, 7), (34, 7)]
CHEEK_L = [(12, 15), (12, 16), (12, 17), (13, 18)]
CHEEK_R = [(26, 15), (26, 16), (25, 17), (25, 18)]


def _put(buf, x, y, ch):
    if 0 <= x < R.SIZE and 0 <= y < R.SIZE and buf[y][x] is not None:
        buf[y][x] = ch


_MASK = set()


def _head_paint(buf, ctx, cells, ch, over_outline=False, add=False):
    """Pinta celulas em coordenadas da CABECA, em qualquer quadro.

    `add=True` deixa o traco sair da silhueta — e o que permite pendurar um
    brinco ao lado da orelha ou deixar a ponta da bandana balancando. Sem
    isso, todo adorno tinha de caber dentro do desenho e acabava virando
    um ou dois pixels perdidos no meio da pele, que e exatamente o que
    deixava as 45 variacoes parecendo todas iguais.
    """
    if 'head' not in ctx:
        return
    hx, hy, flip = ctx['head']
    for fx, fy in cells:
        x = hx + (R.HEAD_W - 1 - fx if flip else fx)
        y = hy + fy
        if 0 <= x < R.SIZE and 0 <= y < R.SIZE and (x, y) not in _MASK:
            if buf[y][x] is None and not add:
                continue
            if buf[y][x] == 'o' and not over_outline:
                continue
            buf[y][x] = ch


def _arm_paint(buf, ctx, part, rows, ch, cols=None):
    if part not in ctx:
        return
    ax, ay, flip = ctx[part]
    cols = cols if cols is not None else range(len(R.DEFAULT_PART[part][0]))
    for ry in rows:
        for rx in cols:
            x, y = ax + rx, ay + ry
            if (0 <= x < R.SIZE and 0 <= y < R.SIZE
                    and buf[y][x] not in (None, 'o') and (x, y) not in _MASK):
                buf[y][x] = ch


# --------------------------------------------------------------- tracos ----
# Regra destas 45 aparencias: a marca tem de ser reconhecida de longe, no
# tamanho em que o jogo desenha o goblin. Na primeira versao quase todas
# eram 1 ou 2 pixels e, lado a lado, as 45 pareciam o mesmo goblin. Agora
# cada traco tem corpo, luz e sombra — e os que sao adorno (brinco, ponta
# da bandana) podem sair da silhueta, que e o que faz eles aparecerem.


def t_gold_tooth(buf, ctx):
    """Presa de ouro: uma lasca grande subindo do labio, nao um ponto."""
    _head_paint(buf, ctx, [(19, 15), (20, 15), (21, 15)], 'u')
    _head_paint(buf, ctx, [(x, y) for y in (16, 17, 18) for x in (19, 20, 21)],
                'Y')
    _head_paint(buf, ctx, [(21, 16), (21, 17), (19, 18), (20, 19), (21, 19)],
                'G')
    _head_paint(buf, ctx, [(22, 17), (22, 18), (18, 18)], 'y')


def t_eyepatch(buf, ctx):
    """Tapa-olho: a placa cobre o olho inteiro e a tira atravessa a cabeca."""
    placa = [(x, y) for y in (12, 13, 14, 15) for x in range(23, 30)]
    _head_paint(buf, ctx, placa, 'K', over_outline=True)
    _head_paint(buf, ctx, [(24, 12), (25, 12), (24, 13)], 'x', over_outline=True)
    # tira atravessando a testa. Ela vai em escada (um passo para o lado,
    # um para cima): em diagonal pura a tira sai pontilhada.
    tira = [(22, 11), (21, 11), (21, 10), (20, 10), (19, 10), (19, 9),
            (18, 9), (17, 9), (16, 9), (16, 8), (15, 8), (14, 8), (13, 8),
            (12, 8), (12, 7), (11, 7), (10, 7), (9, 7), (8, 7)]
    _head_paint(buf, ctx, tira, 'K', over_outline=True)


def _hoop(x0, y0):
    """Argola de ouro 4x4, pendurada a partir de (x0, y0).

    O anel e FECHADO de proposito. Um anel desenhado so com as quinas fica
    preso a orelha apenas pela diagonal, e um pixel que so encosta pela
    quina conta como pedaco solto — o teste das 45 variacoes reprova.
    """
    # as quinas saem em ouro escuro: e o que arredonda o anel sem abrir
    # buraco na ligacao com a orelha
    return ([(x0, y0, 'G'), (x0 + 1, y0, 'u'), (x0 + 2, y0, 'Y'),
             (x0 + 3, y0, 'G'),
             (x0, y0 + 1, 'Y'), (x0 + 3, y0 + 1, 'Y'),
             (x0, y0 + 2, 'Y'), (x0 + 3, y0 + 2, 'Y'),
             (x0, y0 + 3, 'G'), (x0 + 1, y0 + 3, 'G'),
             (x0 + 2, y0 + 3, 'G'), (x0 + 3, y0 + 3, 'G')])


def _put_hoop(buf, ctx, x0, y0):
    for x, y, ch in _hoop(x0, y0):
        _head_paint(buf, ctx, [(x, y)], ch, over_outline=True, add=True)


def t_ear_ring(buf, ctx):
    """Uma argola, na orelha esquerda. Pendurada FORA da orelha."""
    _head_paint(buf, ctx, EAR_L_LOBE, 'G', over_outline=True)
    _put_hoop(buf, ctx, 1, 9)


def t_earring(buf, ctx):
    """Um par de argolas, uma em cada orelha."""
    _head_paint(buf, ctx, EAR_L_LOBE + EAR_R_LOBE, 'G', over_outline=True)
    _put_hoop(buf, ctx, 1, 9)
    _put_hoop(buf, ctx, 31, 9)


def t_scar(buf, ctx):
    """Cicatriz costurada descendo da testa ate a bochecha."""
    corte = [(14, 8), (14, 9), (14, 10), (14, 11), (14, 12),
             (13, 13), (13, 14), (13, 15), (13, 16), (13, 17)]
    _head_paint(buf, ctx, corte, 'f', over_outline=True)
    pontos = [(13, 9), (15, 9), (13, 11), (15, 11),
              (12, 14), (14, 14), (12, 16), (14, 16)]
    _head_paint(buf, ctx, pontos, 'e')


def t_burns(buf, ctx):
    """Queimadura: mancha grande e viva no rosto, no ombro e no braco."""
    _head_paint(buf, ctx, [(25, 15), (26, 15), (27, 15),
                           (24, 16), (25, 16), (26, 16), (27, 16),
                           (24, 17), (25, 17), (26, 17),
                           (24, 18), (25, 18)], 'Q')
    _head_paint(buf, ctx, [(25, 16), (26, 17)], 'Z')
    _head_paint(buf, ctx, [(27, 14), (28, 15), (23, 18), (26, 18)], 'R')
    # respingo irregular descendo pelo braco
    _arm_paint(buf, ctx, 'arm_l', (2,), 'Q', cols=range(6, 9))
    _arm_paint(buf, ctx, 'arm_l', (3,), 'Q', cols=range(5, 10))
    _arm_paint(buf, ctx, 'arm_l', (4,), 'Q', cols=range(4, 10))
    _arm_paint(buf, ctx, 'arm_l', (5,), 'Q', cols=range(4, 9))
    _arm_paint(buf, ctx, 'arm_l', (6,), 'Q', cols=range(5, 8))
    _arm_paint(buf, ctx, 'arm_l', (4,), 'Z', cols=range(6, 8))
    _arm_paint(buf, ctx, 'arm_l', (7,), 'R', cols=range(5, 7))


# Faixas na cabeca: ficam na TESTA, acima dos olhos, e seguem a largura do
# cranio linha a linha. Antes eram um retangulo chapado que cobria os olhos e
# transbordava pelas orelhas — parecia um bone, nao uma faixa.
BANDAGE_ROWS = {9: (6, 31), 10: (7, 29), 11: (7, 29)}
BANDANA_ROWS = {8: (6, 31), 9: (6, 31), 10: (7, 29)}


def _band(spans):
    return [(x, y) for y, (a, b) in spans.items() for x in range(a, b)
            if R.HEAD[y][x] != '.']


def _weave(spans, claro, escuro):
    """Divide a faixa em voltas diagonais de pano.

    Uma faixa de uma cor so vira uma tabua branca atravessada na cara. Com
    as voltas em diagonal o olho le tecido enrolado.
    """
    a, b = [], []
    for x, y in _band(spans):
        (a if (x + 2 * y) % 5 < 3 else b).append((x, y))
    return (a, claro), (b, escuro)


# As pontas da bandana caem em ESCADA, nunca em diagonal pura: um pixel
# que so encosta pela quina fica solto na tela e o teste de corpo inteiro
# reprova (foi assim que a ponta antiga saiu voando ao lado da cabeca).
BANDANA_TAIL = [(6, 11), (6, 12), (5, 12), (5, 13), (5, 14), (4, 14),
                (4, 15), (4, 16), (3, 16)]
BANDANA_TAIL_SHADOW = [(6, 13), (5, 15), (4, 17), (3, 17)]


def t_bandana(buf, ctx):
    """Bandana vermelha cobrindo a testa, com no e a ponta caida."""
    for cells, ch in _weave(BANDANA_ROWS, 'r', 'R'):
        _head_paint(buf, ctx, cells, ch)
    _head_paint(buf, ctx, _band({8: (13, 25)}), 'y')               # luz
    _head_paint(buf, ctx, [(7, 10), (8, 10), (7, 11), (8, 11)], 'r',
                over_outline=True)                                 # no
    _head_paint(buf, ctx, BANDANA_TAIL, 'r', over_outline=True, add=True)
    _head_paint(buf, ctx, BANDANA_TAIL_SHADOW, 'R', over_outline=True, add=True)


def t_arm_bandage(buf, ctx):
    """Atadura enrolada do cotovelo ao punho, com a dobra escura entre voltas."""
    for linha, ch in ((3, 'W'), (4, 'W'), (5, 'X'), (6, 'W'),
                      (7, 'W'), (8, 'X'), (9, 'W')):
        _arm_paint(buf, ctx, 'arm_r', (linha,), ch, cols=range(1, 7))
    _arm_paint(buf, ctx, 'arm_r', (4, 7), 'w', cols=range(2, 4))


def t_birthmark(buf, ctx):
    """Marca de nascenca: mancha roxa larga sobre metade da testa."""
    _head_paint(buf, ctx, [(x, y) for y in (8, 9, 10, 11, 12)
                           for x in range(22, 28)], 'P')
    _head_paint(buf, ctx, [(23, 9), (24, 9), (23, 10)], 'V')
    _head_paint(buf, ctx, [(x, 13) for x in range(23, 27)], 'v')
    _head_paint(buf, ctx, [(21, 10), (21, 11), (28, 10), (28, 11)], 'v')


def t_head_bandage(buf, ctx):
    """Cabeca enfaixada: a atadura da a volta e uma ponta desce pela tempora."""
    for cells, ch in _weave(BADAGE := BANDAGE_ROWS, 'W', 'X'):
        _head_paint(buf, ctx, cells, ch)
    _head_paint(buf, ctx, [(x, 9) for x in range(14, 20)], 'w')    # luz
    # ponta solta descendo pela tempora, sem encostar no olho
    _head_paint(buf, ctx, [(10, 12), (10, 13), (11, 13), (11, 14)], 'W',
                over_outline=True)
    _head_paint(buf, ctx, [(11, 13)], 'X')


# Regra dos olhos: a esclera continua sendo a do desenho original. So a
# PUPILA troca de cor. Pintar o olho inteiro de uma cor so apagava o olhar e
# deixava um retangulo colorido no lugar do olho.
def t_blind_eye(buf, ctx):
    """Olho cego: a pupila fica leitosa e um corte atravessa a palpebra."""
    _head_paint(buf, ctx, PUPIL_L + EYE_L, 'w', over_outline=True)
    _head_paint(buf, ctx, [(17, 14), (18, 13)], 'X')
    # corte fundo atravessando a palpebra, de cima a baixo
    _head_paint(buf, ctx, [(16, 10), (16, 11), (17, 11), (17, 12),
                           (18, 15), (18, 16), (17, 16), (17, 17)], 'f',
                over_outline=True)
    _head_paint(buf, ctx, [(15, 11), (18, 12), (19, 16), (16, 17)], 'e')


def t_ruby_eye(buf, ctx):
    """Olho de rubi: pupila acesa, com o brilho em volta."""
    _head_paint(buf, ctx, PUPIL_L, 'r', over_outline=True)
    _head_paint(buf, ctx, EYE_L, 'R', over_outline=True)
    _head_paint(buf, ctx, [(17, 13)], 'r')
    # o brilho vermelho bate na pele em volta do olho
    _head_paint(buf, ctx, [(15, 12), (16, 12), (17, 12), (18, 12),
                           (16, 15), (17, 15), (18, 15),
                           (15, 13), (19, 13), (15, 14), (19, 14)], 'Q')


def t_wart(buf, ctx):
    """Verruga grande no focinho, com volume."""
    _head_paint(buf, ctx, [(x, y) for y in (14, 15, 16) for x in (19, 20, 21)]
                + [(20, 17), (21, 17), (22, 15), (22, 16)], 'e')
    _head_paint(buf, ctx, [(19, 14), (20, 14), (19, 15)], 'd')
    _head_paint(buf, ctx, [(23, 15), (23, 16), (22, 17), (21, 18)], 'k')
    # segunda verruga, menor, no queixo
    _head_paint(buf, ctx, [(16, 18), (17, 18), (16, 19)], 'e')


# Sardas de 1 px desaparecem no sombreado da pele. Cada sarda e um par de
# pixels, com um ponto mais escuro ao lado, para virar mancha e nao ruido.
FRECKLES = [(13, 10), (16, 10), (12, 13), (15, 13), (12, 16), (15, 16),
            (18, 16), (26, 10), (29, 10), (24, 12), (27, 12),
            (24, 16), (27, 16), (21, 15)]


def t_freckles(buf, ctx):
    """Sardas: pares de pixels espalhados pelas duas bochechas e pelo nariz."""
    _head_paint(buf, ctx, FRECKLES, 'e')
    _head_paint(buf, ctx, [(x + 1, y) for x, y in FRECKLES], 'e')
    _head_paint(buf, ctx, [(x, y + 1) for x, y in FRECKLES[::2]], 'd')


def t_tattoo(buf, ctx):
    """Tatuagem facial: tracos largos em azul descendo pelas duas faces."""
    for x in (14, 15):
        _head_paint(buf, ctx, [(x, y) for y in range(8, 13)], 'I')
    for x in (26, 27):
        _head_paint(buf, ctx, [(x, y) for y in range(8, 13)], 'I')
    _head_paint(buf, ctx, [(15, y) for y in range(8, 13)], 't')
    _head_paint(buf, ctx, [(26, y) for y in range(8, 13)], 't')
    _head_paint(buf, ctx, [(13, 15), (13, 16), (14, 17),
                           (26, 15), (26, 16), (25, 17)], 'I')
    _head_paint(buf, ctx, [(x, 7) for x in (14, 15, 26, 27)], 'J')
    _head_paint(buf, ctx, [(19, 12), (20, 12), (21, 12), (22, 12)], 'J')


def t_double_fangs(buf, ctx):
    """Presas duplas: dois caninos grandes saindo da boca."""
    _head_paint(buf, ctx, [(17, 16), (18, 16), (17, 17), (18, 17),
                           (17, 18), (18, 18), (18, 19)], 'w')
    _head_paint(buf, ctx, [(23, 16), (24, 16), (23, 17), (24, 17),
                           (23, 18), (24, 18), (23, 19)], 'w')
    _head_paint(buf, ctx, [(17, 16), (24, 16)], 'y')
    _head_paint(buf, ctx, [(19, 17), (19, 18), (22, 17), (22, 18)], 'X')


def t_glow_eyes(buf, ctx):
    """Olhos acesos: os dois brilham e espalham luz na pele em volta."""
    _head_paint(buf, ctx, PUPIL_L + PUPIL_R + EYE_L + EYE_R, 'Y',
                over_outline=True)
    _head_paint(buf, ctx, [(17, 13), (26, 13)], 'u')
    _head_paint(buf, ctx, [(15, 12), (19, 12), (15, 15), (19, 15),
                           (24, 12), (29, 12), (24, 15), (29, 15)], 'G')


def t_dark_veins(buf, ctx):
    """Veias amaldicoadas: grossas, subindo da testa para o alto do cranio."""
    esq = [(15, 5), (15, 6), (16, 7), (16, 8), (16, 9), (17, 10), (17, 11),
           (16, 12), (14, 7), (13, 8), (18, 9), (19, 10)]
    dir_ = [(27, 5), (27, 6), (27, 7), (26, 8), (26, 9), (26, 10), (27, 11),
            (27, 12), (29, 8), (30, 9), (24, 10), (23, 11)]
    _head_paint(buf, ctx, esq + dir_, 'v')
    _head_paint(buf, ctx, [(16, 6), (26, 9), (17, 10), (27, 7)], 'P')


def t_dirt(buf, ctx):
    """Encardido: barro borrado na cara, no queixo e nos dois bracos."""
    borrao = ([(x, y) for y in (14, 15, 16) for x in range(11, 15)]
              + [(x, y) for y in (17, 18) for x in range(12, 16)]
              + [(x, 19) for x in range(17, 24)]
              + [(x, y) for y in (16, 17) for x in range(25, 28)]
              + [(28, 11), (27, 10), (12, 11), (13, 10)])
    _head_paint(buf, ctx, borrao, 'c')
    _head_paint(buf, ctx, [(12, 15), (13, 17), (19, 19), (26, 16)], 'B')
    _arm_paint(buf, ctx, 'arm_l', range(6, 11), 'c', cols=range(0, 8))
    _arm_paint(buf, ctx, 'arm_r', range(7, 12), 'c', cols=range(1, 8))


DETAILS = {
    'gold_tooth': t_gold_tooth, 'eyepatch': t_eyepatch, 'ear_ring': t_ear_ring,
    'earring': t_earring, 'scar': t_scar, 'burns': t_burns, 'bandana': t_bandana,
    'arm_bandage': t_arm_bandage, 'birthmark': t_birthmark,
    'head_bandage': t_head_bandage, 'blind_eye': t_blind_eye,
    'ruby_eye': t_ruby_eye, 'wart': t_wart, 'freckles': t_freckles,
    'tattoo': t_tattoo, 'double_fangs': t_double_fangs, 'glow_eyes': t_glow_eyes,
    'dark_veins': t_dark_veins, 'dirt': t_dirt,
}

SWAPS = {
    # Trocas de paleta: respeitam os 8 tons de pele do original, entao o
    # volume do desenho continua la — muda so a matiz.
    # O contorno NAO vira pele. Antes 'k' virava rosa junto com o resto e o
    # goblin perdia a silhueta inteira — ficava um borrao. Agora a linha de
    # contorno so esquenta de tom e continua sendo a mais escura do desenho.
    'albino': {'k': 'U', 'e': 'F', 'd': 'E', 'n': 'E', 'j': 'A',
               'g': 'A', 'l': 'a', 'f': 'a'},
    'grizzled': {'f': 'l', 'l': 'g', 'g': 'j', 'j': 'n', 'n': 'd', 'd': 'e'},
    # Encardido: a pele inteira perde um tom e o couro escurece, senao a
    # variacao ficava igual ao goblin limpo.
    'sooty': {'f': 'g', 'l': 'j', 'g': 'j', 'j': 'n', 'n': 'd',
              'h': 'b', 'b': 'B', 'q': 'z', 'z': 'h'},
}


# Onde a orelha direita comeca em cada linha da cabeca. Os valores saem do
# proprio desenho (a coluna escura que separa cranio e orelha), por isso o
# corte tira a orelha inteira sem comer o cranio.
EAR_R_CUT = {0: 23, 1: 23, 2: 23, 3: 23, 4: 24, 5: 24, 6: 25, 7: 27, 8: 27, 9: 27}


def _head_without_right_ear():
    head = copy.deepcopy(R.HEAD)
    w = len(head[0])
    for y, cut in EAR_R_CUT.items():
        for x in range(cut, w):
            head[y][x] = '.'
        if head[y][cut - 1] != '.':   # fecha o coto com contorno escuro
            head[y][cut - 1] = 'k'
    return head


PARTS = {
    'missing_ear': lambda: {'head': _head_without_right_ear()},
}

# ------------------------------------------------------------- receitas ----
# Mesma ordem e mesmos ids que js/goblin.js espera.
RECIPES = {
    '01_dente_dourado':        ['gold_tooth'],
    '02_tapa_olho':            ['eyepatch'],
    '04_orelha_furada':        ['ear_ring'],
    '07_cicatriz':             ['scar'],
    '08_albinismo':            ['albino', 'ruby_eye'],
    '09_queimaduras':          ['burns'],
    '10_corsario':             ['bandana', 'eyepatch'],
    '13_sobrevivente':         ['scar', 'arm_bandage'],
    '14_anel':                 ['earring'],
    '15_marca_de_nascenca':    ['birthmark'],
    '16_sem_orelha':           ['missing_ear'],
    '17_enfaixado':            ['head_bandage'],
    '18_ileso':                [],
    '19_olho_cego':            ['blind_eye'],
    '20_verruga':              ['wart'],
    '21_sardas':               ['freckles'],
    '22_tatuagem_facial':      ['tattoo'],
    '23_presas_duplas':        ['double_fangs'],
    '24_olho_rubi':            ['ruby_eye'],
    '26_veterano':             ['scar', 'grizzled'],
    '27_queimado_enfaixado':   ['burns', 'head_bandage'],
    '28_albino_rubi':          ['albino', 'ruby_eye', 'earring'],
    '29_guerreiro_marcado':    ['scar', 'tattoo'],
    '30_sobrevivente_ferido':  ['scar', 'arm_bandage', 'blind_eye'],
    '31_mistico':              ['tattoo', 'glow_eyes'],
    '32_brigao':               ['missing_ear', 'scar'],
    '33_amaldicoado':          ['birthmark', 'dark_veins'],
    '34_sardento':             ['freckles', 'wart'],
    '35_cacador_marcado':      ['tattoo', 'earring'],
    '36_pirata_queimado':      ['bandana', 'eyepatch', 'burns'],
    '37_albino_cicatrizado':   ['albino', 'scar'],
    '38_guerreiro_enfaixado':  ['head_bandage', 'arm_bandage', 'scar'],
    # o rubi vem DEPOIS do brilho: um olho fica dourado e o outro
    # vermelho, senao o oraculo saia identico ao mistico
    '39_oraculo_rubi':         ['tattoo', 'glow_eyes', 'ruby_eye'],
    '40_presas_douradas':      ['double_fangs', 'gold_tooth'],
    '41_veterano_enfaixado':   ['scar', 'grizzled', 'head_bandage'],
    '42_queimado_tatuado':     ['burns', 'tattoo'],
    '43_albino_sardento':      ['albino', 'freckles'],
    '44_brigao_cego':          ['missing_ear', 'blind_eye'],
    '45_fanatico':             ['tattoo', 'glow_eyes', 'head_bandage'],
    '46_marcado_rubi':         ['birthmark', 'ruby_eye'],
    '47_sobrevivente_sujo':    ['arm_bandage', 'dirt', 'sooty'],
    '48_corsario_tatuado':     ['bandana', 'eyepatch', 'tattoo'],
    '49_guerreiro_dourado':    ['gold_tooth', 'earring', 'scar'],
    '50_amaldicoado_enfaixado': ['birthmark', 'dark_veins', 'head_bandage'],
    '51_mutilado':             ['missing_ear', 'blind_eye', 'scar', 'burns'],
}

ORDER = list(RECIPES)
assert len(ORDER) == 45, len(ORDER)


def build(variation_id):
    """Converte a receita no dicionario que goblin_anim.render_action espera."""
    traits = RECIPES[variation_id]
    swap, parts, details = {}, {}, []
    for t in traits:
        if t in SWAPS:
            swap.update(SWAPS[t])
        elif t in PARTS:
            parts.update(PARTS[t]())
        elif t in DETAILS:
            details.append(DETAILS[t])
        else:
            raise KeyError(f'traco desconhecido: {t} ({variation_id})')

    def detail(buf, ctx, mask=()):
        global _MASK
        _MASK = mask or set()
        try:
            for fn in details:
                fn(buf, ctx)
        finally:
            _MASK = set()

    return {
        'swap': swap or None,
        'parts': parts or None,
        'detail': detail if details else None,
    }
