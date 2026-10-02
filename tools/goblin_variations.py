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
    'A': (214, 220, 204, 255),   # pele albina
    'a': (240, 243, 233, 255),   # pele albina luz
    'E': (176, 186, 168, 255),   # pele albina sombra
    'P': (112, 66, 124, 255),    # mancha de nascenca
    'v': (64, 42, 80, 255),      # veias amaldicoadas
    'G': (188, 150, 46, 255),    # ouro sombra
})

# Mapa da cabeca (24x12), recortada da arte de referencia:
#   cranio nas colunas 7..18 | orelha esquerda cols 1..6, direita cols 17..22
#   testa rows 3-5 | sobrancelhas row 6 | olhos row 7 | focinho rows 8-9
#   boca row 10 | presa (15, 11)
EYE_L = [(10, 7), (11, 7)]
EYE_R = [(15, 7), (16, 7)]
BROW_L = [(10, 6), (11, 6)]
BROW_R = [(15, 6), (16, 6)]
FOREHEAD = [(x, y) for y in (3, 4, 5) for x in range(8, 18)]
CROWN = [(x, y) for y in (0, 1, 2) for x in range(8, 20)]
EAR_L_CORE = [(3, 2), (4, 2), (3, 3), (4, 3)]
EAR_R_CORE = [(18, 2), (19, 2), (19, 3), (20, 3)]
EAR_L_LOBE = [(2, 4)]
EAR_R_LOBE = [(21, 4)]
TUSK = [(15, 11)]


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
    _head_paint(buf, ctx, TUSK, 'Y')


def t_eyepatch(buf, ctx):
    _head_paint(buf, ctx, EYE_R + BROW_R, 'k', over_outline=True)
    _head_paint(buf, ctx, [(13, 6), (14, 6), (17, 6), (18, 6),
                           (17, 7), (18, 7)], 'k')


def t_ear_ring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE, 'Y', over_outline=True)


def t_earring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE + EAR_R_LOBE, 'Y', over_outline=True)


def t_scar(buf, ctx):
    _head_paint(buf, ctx, [(9, 5), (9, 6), (9, 7), (9, 8)], 'l')


def t_burns(buf, ctx):
    _head_paint(buf, ctx, [(17, 7), (17, 8), (16, 9), (17, 9)], 'c')
    _arm_paint(buf, ctx, 'arm_l', (3, 4), 'c', cols=(2, 3, 4))


def t_bandana(buf, ctx):
    _head_paint(buf, ctx, CROWN, 'r')
    _head_paint(buf, ctx, [(9, 2), (10, 2), (14, 1)], 'R')


def t_arm_bandage(buf, ctx):
    _arm_paint(buf, ctx, 'arm_r', (2, 3), 'W', cols=(1, 2, 3, 4))


def t_birthmark(buf, ctx):
    _head_paint(buf, ctx, [(16, 2), (16, 3), (17, 3)], 'P')


def t_head_bandage(buf, ctx):
    _head_paint(buf, ctx, FOREHEAD, 'W')
    _head_paint(buf, ctx, EYE_L, 'W')


def t_blind_eye(buf, ctx):
    _head_paint(buf, ctx, EYE_L, 'w')


def t_ruby_eye(buf, ctx):
    _head_paint(buf, ctx, [(10, 7)], 'r')
    _head_paint(buf, ctx, [(11, 7)], 'R')


def t_wart(buf, ctx):
    _head_paint(buf, ctx, [(12, 8)], 'd')


def t_freckles(buf, ctx):
    _head_paint(buf, ctx, [(9, 5), (9, 7), (17, 5), (17, 7)], 'd')


def t_tattoo(buf, ctx):
    _head_paint(buf, ctx, [(9, 4), (9, 8), (17, 4), (17, 8)], 'c')


def t_double_fangs(buf, ctx):
    _head_paint(buf, ctx, [(12, 11), (13, 11)], 'y')


def t_glow_eyes(buf, ctx):
    _head_paint(buf, ctx, EYE_L + EYE_R, 'Y')


def t_dark_veins(buf, ctx):
    _head_paint(buf, ctx, [(9, 2), (10, 2), (16, 2), (17, 2)], 'v')


def t_dirt(buf, ctx):
    _head_paint(buf, ctx, [(11, 6), (16, 8)], 'c')
    _arm_paint(buf, ctx, 'arm_l', (5, 6), 'c', cols=(1, 2, 3))


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
    'albino': {'e': 'E', 'd': 'E', 'j': 'A', 'g': 'A', 'l': 'a', 'f': 'a'},
    'grizzled': {'f': 'l', 'l': 'g', 'g': 'j', 'j': 'd'},
    'sooty': {'h': 'b', 'b': 'B', 'f': 'l', 'l': 'g'},
}


def _head_without_right_ear():
    head = copy.deepcopy(R.HEAD)
    for y in range(1, 6):
        for x in range(17, 24):
            head[y][x] = '.'
    for x in range(17, 20):           # fecha o coto com contorno
        if head[6][x] != '.':
            head[6][x] = 'o'
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
