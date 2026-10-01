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

# Mapa da cabeca (18x10) em coordenadas relativas ao desenho atual:
#   cranio nas colunas 4..13 | orelhas pontudas nas colunas 0..2 e 15..17
#   testa rows 1-3 | sobrancelha row 4 | olhos row 5 | nariz row 6 | boca row 8
EYE_L = [(6, 5), (7, 5)]
EYE_R = [(10, 5), (11, 5)]
BROW_L = [(6, 4), (7, 4)]
BROW_R = [(10, 4), (11, 4)]
FOREHEAD = [(x, y) for y in (1, 2, 3) for x in range(5, 13)]
CROWN = [(x, y) for y in (0, 1, 2) for x in range(4, 14)]
EAR_L_CORE = [(1, 4), (2, 4), (2, 5)]
EAR_R_CORE = [(16, 4), (15, 4), (15, 5)]


def _put(buf, x, y, ch):
    if 0 <= x < R.SIZE and 0 <= y < R.SIZE and buf[y][x] is not None:
        buf[y][x] = ch


_MASK = set()


def _head_paint(buf, ctx, cells, ch, over_outline=False):
    if 'head' not in ctx:
        return
    hx, hy, flip = ctx['head']
    for fx, fy in cells:
        x = hx + (17 - fx if flip else fx)
        y = hy + fy
        if 0 <= x < R.SIZE and 0 <= y < R.SIZE and (x, y) not in _MASK:
            if buf[y][x] is None:
                continue
            if buf[y][x] == 'o' and not over_outline:
                continue
            buf[y][x] = ch


def _arm_paint(buf, ctx, part, rows, ch):
    if part not in ctx:
        return
    ax, ay, flip = ctx[part]
    for ry in rows:
        for rx in range(3):
            x, y = ax + rx, ay + ry
            if (0 <= x < R.SIZE and 0 <= y < R.SIZE
                    and buf[y][x] not in (None, 'o') and (x, y) not in _MASK):
                buf[y][x] = ch


# --------------------------------------------------------------- tracos ----
def t_gold_tooth(buf, ctx):
    _head_paint(buf, ctx, [(7, 8)], 'Y')


def t_eyepatch(buf, ctx):
    _head_paint(buf, ctx, EYE_R + BROW_R, 'k')
    _head_paint(buf, ctx, [(8, 4), (9, 4), (8, 5), (9, 5)], 'k')


def t_ear_ring(buf, ctx):
    _head_paint(buf, ctx, [(2, 5)], 'Y')


def t_earring(buf, ctx):
    _head_paint(buf, ctx, [(2, 4), (2, 5)], 'Y')


def t_scar(buf, ctx):
    _head_paint(buf, ctx, [(6, 2), (6, 3), (6, 4)], 'l')


def t_burns(buf, ctx):
    _head_paint(buf, ctx, [(10, 6), (11, 6), (11, 7), (11, 3)], 'c')
    _arm_paint(buf, ctx, 'arm_r', (3, 4), 'c')


def t_bandana(buf, ctx):
    _head_paint(buf, ctx, CROWN, 'r')
    _head_paint(buf, ctx, [(5, 2), (6, 2)], 'R')


def t_arm_bandage(buf, ctx):
    _arm_paint(buf, ctx, 'arm_l', (3, 4, 5), 'W')


def t_birthmark(buf, ctx):
    _head_paint(buf, ctx, [(10, 2), (10, 3), (11, 3)], 'P')


def t_head_bandage(buf, ctx):
    _head_paint(buf, ctx, FOREHEAD, 'W')
    _head_paint(buf, ctx, EYE_L, 'W')


def t_blind_eye(buf, ctx):
    _head_paint(buf, ctx, EYE_L, 'w')


def t_ruby_eye(buf, ctx):
    _head_paint(buf, ctx, [(6, 5)], 'r')
    _head_paint(buf, ctx, [(7, 5)], 'R')


def t_wart(buf, ctx):
    _head_paint(buf, ctx, [(11, 6)], 'd')


def t_freckles(buf, ctx):
    _head_paint(buf, ctx, [(6, 6), (11, 6), (6, 3), (11, 3)], 'd')


def t_tattoo(buf, ctx):
    _head_paint(buf, ctx, [(6, 3), (6, 6), (11, 3), (11, 6)], 'c')


def t_double_fangs(buf, ctx):
    _head_paint(buf, ctx, [(8, 8), (9, 8)], 'y')


def t_glow_eyes(buf, ctx):
    _head_paint(buf, ctx, EYE_L + EYE_R, 'Y')


def t_dark_veins(buf, ctx):
    _head_paint(buf, ctx, [(6, 2), (7, 2), (10, 2), (11, 2)], 'v')


def t_dirt(buf, ctx):
    _head_paint(buf, ctx, [(7, 6), (10, 7)], 'c')
    _arm_paint(buf, ctx, 'arm_r', (5, 6), 'c')


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
    'albino': {'g': 'A', 'l': 'a', 'd': 'E'},
    'grizzled': {'g': 'd', 'l': 'g'},
    'sooty': {'t': 'T', 'u': 't'},
}


def _head_without_right_ear():
    head = copy.deepcopy(R.HEAD)
    for y in range(3, 7):
        for x in range(14, 18):
            head[y][x] = '.'
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
