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
    'I': (58, 92, 170, 255),     # tatuagem azul
    'J': (32, 52, 110, 255),     # tatuagem azul escura
    'Q': (168, 58, 44, 255),     # queimadura
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


def _head_paint(buf, ctx, cells, ch, over_outline=False):
    if 'head' not in ctx:
        return
    hx, hy, flip = ctx['head']
    for fx, fy in cells:
        x = hx + (R.HEAD_W - 1 - fx if flip else fx)
        y = hy + fy
        if 0 <= x < R.SIZE and 0 <= y < R.SIZE and (x, y) not in _MASK:
            if buf[y][x] is None:
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
def t_gold_tooth(buf, ctx):
    _head_paint(buf, ctx, TUSK + [(20, 18)], 'Y')
    _head_paint(buf, ctx, [(21, 19)], 'G')


def t_eyepatch(buf, ctx):
    _head_paint(buf, ctx, EYE_R + PUPIL_R + BROW_R, 'K', over_outline=True)
    _head_paint(buf, ctx, [(24, 13), (24, 14), (27, 14), (28, 14)], 'K')
    _head_paint(buf, ctx, [(21, 11), (22, 11), (23, 12), (29, 15), (30, 15)], 'K')


def t_ear_ring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE, 'Y', over_outline=True)
    _head_paint(buf, ctx, [(3, 7)], 'G', over_outline=True)


def t_earring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE + EAR_R_LOBE, 'Y', over_outline=True)
    _head_paint(buf, ctx, [(3, 7), (32, 7)], 'G', over_outline=True)


def t_scar(buf, ctx):
    _head_paint(buf, ctx, [(14, 9), (14, 10), (14, 11), (14, 12),
                           (14, 13), (13, 14), (13, 15)], 'l')


def t_burns(buf, ctx):
    # Como no original: queimadura avermelhada, nao uma mancha marrom.
    _head_paint(buf, ctx, CHEEK_R + [(26, 18)], 'Q')
    _head_paint(buf, ctx, [(27, 15), (27, 16), (24, 19), (25, 19)], 'R')
    _arm_paint(buf, ctx, 'arm_l', range(4, 8), 'Q', cols=range(3, 8))
    _arm_paint(buf, ctx, 'arm_l', (5, 6), 'R', cols=range(4, 7))


def t_bandana(buf, ctx):
    _head_paint(buf, ctx, CROWN, 'r')
    _head_paint(buf, ctx, [(x, y) for y in (5, 6) for x in range(14, 19)], 'R')


def t_arm_bandage(buf, ctx):
    _arm_paint(buf, ctx, 'arm_r', range(4, 8), 'W', cols=range(1, 6))


def t_birthmark(buf, ctx):
    _head_paint(buf, ctx, [(x, y) for y in (8, 9, 10) for x in (25, 26, 27)], 'P')


def t_head_bandage(buf, ctx):
    _head_paint(buf, ctx, FOREHEAD, 'W')
    _head_paint(buf, ctx, EYE_L + PUPIL_L + BROW_L, 'W')


def t_blind_eye(buf, ctx):
    _head_paint(buf, ctx, EYE_L, 'w')
    _head_paint(buf, ctx, PUPIL_L, 'w', over_outline=True)


def t_ruby_eye(buf, ctx):
    _head_paint(buf, ctx, EYE_L, 'r')
    _head_paint(buf, ctx, PUPIL_L, 'R', over_outline=True)


def t_wart(buf, ctx):
    _head_paint(buf, ctx, [(20, 16), (21, 16), (20, 17)], 'e')
    _head_paint(buf, ctx, [(21, 17)], 'd')


def t_freckles(buf, ctx):
    _head_paint(buf, ctx, [(14, 11), (13, 15), (27, 11), (26, 15),
                           (15, 17), (24, 17), (14, 13), (27, 16)], 'e')


def t_tattoo(buf, ctx):
    # Como no original: tracos AZUIS no rosto, nao marrons.
    _head_paint(buf, ctx, [(14, 9), (14, 10), (14, 11), (15, 11),
                           (27, 9), (27, 10), (27, 11), (26, 11)], 'I')
    _head_paint(buf, ctx, [(13, 16), (13, 17), (14, 17),
                           (26, 16), (26, 17), (25, 17)], 'I')
    _head_paint(buf, ctx, [(14, 12), (27, 12), (15, 8), (26, 8)], 'J')


def t_double_fangs(buf, ctx):
    _head_paint(buf, ctx, [(18, 18), (19, 18), (18, 19), (24, 18), (24, 19)], 'y')


def t_glow_eyes(buf, ctx):
    _head_paint(buf, ctx, EYE_L + EYE_R, 'Y')
    _head_paint(buf, ctx, PUPIL_L + PUPIL_R, 'G', over_outline=True)


def t_dark_veins(buf, ctx):
    _head_paint(buf, ctx, [(x, y) for y in (5, 6, 7, 8)
                           for x in (15, 16, 27, 28)], 'v')
    _head_paint(buf, ctx, [(17, 9), (26, 9), (16, 10), (27, 10)], 'v')


def t_dirt(buf, ctx):
    _head_paint(buf, ctx, CHEEK_L + [(20, 19), (21, 19)], 'c')
    _arm_paint(buf, ctx, 'arm_l', range(8, 11), 'c', cols=range(1, 6))


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
    'albino': {'k': 'E', 'e': 'E', 'd': 'E', 'n': 'A', 'j': 'A',
               'g': 'A', 'l': 'a', 'f': 'a'},
    'grizzled': {'f': 'l', 'l': 'g', 'g': 'j', 'j': 'n', 'n': 'd', 'd': 'e'},
    'sooty': {'h': 'b', 'b': 'B', 'f': 'l', 'l': 'g', 'g': 'j'},
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
    '39_oraculo_rubi':         ['ruby_eye', 'tattoo', 'glow_eyes'],
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
