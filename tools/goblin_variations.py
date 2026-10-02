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

# Mapa da cabeca (38x20), recortada da arte de referencia em 64x64:
#   cranio cols 10..31 | orelha esquerda cols 0..13, direita cols 26..37
#   testa rows 5..10 | sobrancelhas row 11 | olhos rows 12-13
#   focinho rows 14..16 | boca/presa row 17 | queixo rows 18-19
EYE_L = [(x, y) for y in (12, 13) for x in (17, 18, 19)]
EYE_R = [(x, y) for y in (12, 13) for x in (25, 26)]
BROW_L = [(17, 11), (18, 11), (19, 11)]
BROW_R = [(25, 11), (26, 11)]
FOREHEAD = [(x, y) for y in range(7, 12) for x in range(15, 30)]
CROWN = [(x, y) for y in range(2, 8) for x in range(15, 31)]
EAR_L_CORE = [(x, y) for y in (4, 5, 6) for x in range(4, 11)]
EAR_R_CORE = [(x, y) for y in (3, 4, 5) for x in range(28, 35)]
EAR_L_LOBE = [(3, 6), (4, 6)]
EAR_R_LOBE = [(34, 6), (35, 6)]
TUSK = [(22, 17), (23, 17)]
CHEEK_L = [(14, 14), (14, 15), (14, 16)]
CHEEK_R = [(28, 14), (28, 15), (28, 16)]


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
    _head_paint(buf, ctx, [(x, y) for y in (11, 12, 13) for x in (24, 27, 28)], 'k')
    _head_paint(buf, ctx, [(21, 10), (22, 10), (29, 14), (30, 14)], 'k')


def t_ear_ring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE, 'Y', over_outline=True)


def t_earring(buf, ctx):
    _head_paint(buf, ctx, EAR_L_LOBE + EAR_R_LOBE, 'Y', over_outline=True)


def t_scar(buf, ctx):
    _head_paint(buf, ctx, [(15, 9), (15, 10), (15, 11), (15, 12),
                           (15, 13), (14, 14), (14, 15)], 'l')


def t_burns(buf, ctx):
    _head_paint(buf, ctx, CHEEK_R + [(27, 17), (28, 17)], 'c')
    _arm_paint(buf, ctx, 'arm_l', range(5, 9), 'c', cols=range(2, 7))


def t_bandana(buf, ctx):
    _head_paint(buf, ctx, CROWN, 'r')
    _head_paint(buf, ctx, [(x, y) for y in (4, 5) for x in range(15, 20)], 'R')


def t_arm_bandage(buf, ctx):
    _arm_paint(buf, ctx, 'arm_r', range(3, 7), 'W', cols=range(1, 6))


def t_birthmark(buf, ctx):
    _head_paint(buf, ctx, [(x, y) for y in (6, 7, 8) for x in (27, 28, 29)], 'P')


def t_head_bandage(buf, ctx):
    _head_paint(buf, ctx, FOREHEAD, 'W')
    _head_paint(buf, ctx, EYE_L + BROW_L, 'W')


def t_blind_eye(buf, ctx):
    _head_paint(buf, ctx, EYE_L, 'w')


def t_ruby_eye(buf, ctx):
    _head_paint(buf, ctx, [(17, 12), (18, 12), (17, 13)], 'r')
    _head_paint(buf, ctx, [(19, 12), (18, 13), (19, 13)], 'R')


def t_wart(buf, ctx):
    _head_paint(buf, ctx, [(21, 15), (22, 15)], 'd')


def t_freckles(buf, ctx):
    _head_paint(buf, ctx, [(15, 10), (15, 14), (29, 10), (29, 14),
                           (16, 16), (27, 16)], 'd')


def t_tattoo(buf, ctx):
    _head_paint(buf, ctx, [(15, 8), (15, 9), (16, 10),
                           (29, 8), (29, 9), (28, 10)], 'c')
    _head_paint(buf, ctx, [(15, 16), (16, 17), (29, 16), (28, 17)], 'c')


def t_double_fangs(buf, ctx):
    _head_paint(buf, ctx, [(19, 17), (20, 17), (19, 18), (26, 17), (26, 18)], 'y')


def t_glow_eyes(buf, ctx):
    _head_paint(buf, ctx, EYE_L + EYE_R, 'Y')


def t_dark_veins(buf, ctx):
    _head_paint(buf, ctx, [(x, y) for y in (4, 5, 6) for x in (16, 17, 29, 30)], 'v')


def t_dirt(buf, ctx):
    _head_paint(buf, ctx, CHEEK_L + [(21, 18), (22, 18)], 'c')
    _arm_paint(buf, ctx, 'arm_l', range(8, 11), 'c', cols=range(1, 5))


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
    for y in range(0, 9):
        for x in range(29, 38):
            head[y][x] = '.'
    for y in range(0, 9):             # fecha o coto com contorno
        if head[y][28] != '.':
            head[y][28] = 'o'
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
