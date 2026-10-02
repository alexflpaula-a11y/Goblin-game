#!/usr/bin/env python3
"""
Armaduras e armas redesenhadas para o goblin v2.

Cada peca e um conjunto de camadas ancoradas a uma PARTE do corpo
(cabeca, tronco, braco, perna, espada). Como o rig informa onde cada parte
esta em cada quadro, a peca acompanha o goblin automaticamente nos 62
quadros das 5 animacoes — nao existe alinhamento manual.

As cores sao escritas em "D/M/L/G" (sombra, base, luz, detalhe) e so no
final sao trocadas pela paleta do material: obsidiana turquesa (AVARITIA)
ou ferro (FERRO). Uma peca nova e so mais um desenho nesse formato.
"""

import goblin_rig as R

# ------------------------------------------------------------- materiais ---
MATERIALS = {
    'avaritia': {'D': '1', 'M': '2', 'L': '3', 'G': '4', 'A': '6'},
    'ferro':    {'D': '7', 'M': '8', 'L': '9', 'G': '9', 'A': '6'},
    'madeira':  {'D': 'B', 'M': 'L', 'L': 'M', 'G': '6', 'A': '6'},
}


def paint(rows, material):
    m = MATERIALS[material]
    return [[m.get(ch, ch) for ch in row] for row in rows]


def g(rows, w):
    for r in rows:
        assert len(r) == w, (len(r), r)
    return [list(r) for r in rows]


# ------------------------------------------------------------- desenhos ----
# Geometria do goblin 64x64 recortado da referencia:
#   cabeca 38x20 | tronco 28x23 | braco esq. 13x14 | braco dir. 11x11
#   perna esq. 12x7 | perna dir. 10x7
# O rosto, as orelhas e as botas continuam a vista em todas as pecas.

# CAPACETE — calota sobre o cranio (cols 13..31), orelhas livres.
HELM = g([
    "..............DDDDDDDDDDDDDDDD........",
    "..............DMMMMMMMMMMMMMMD........",
    ".............DMMMLLLMMMMMMMMMMD.......",
    ".............DMMLLLLLMMMMMMMMMD.......",
    "............DMMMLLLMMMMMMMMMMMMD......",
    "............DMMMMMMMMMMMMMMMMMMD......",
    "............DMMMMMMMMMMMMMMMMMMD......",
    "............DMMMMMMMMMMMMMMMMMMD......",
    "............DDDGGGGGGGGGGGGGGDDD......",
    "............DDDDDDDDDDDDDDDDDDDD......",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
    "......................................",
], 38)

# PEITORAL — placa sobre o peito, acima do cinto de couro.
CHEST = g([
    ".....DDDDDDDDDDDDDDD........",
    "....DMMMMMMMMMMMMMMMD.......",
    "....DMMMMMMMMMMMMMMMD.......",
    "....DMMMMLLLLLLMMMMMD.......",
    "....DMMMLLLLLLLLMMMMD.......",
    "....DMMGGGGGGGGGGMMMD.......",
    "....DMMGGGGGGGGGGMMMD.......",
    "....DMMMMMMMMMMMMMMMD.......",
    "....DMMMMMMMMMMMMMMMD.......",
    "....DDMMMMMMMMMMMMMDD.......",
    ".....DDDDDDDDDDDDDDD........",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], 28)

# OMBREIRAS — uma por braco (grades de larguras diferentes).
PAULDRON_L = g([
    ".....DDDDDDDD",
    "....DDMMMMMMD",
    "....DMMMMMMMD",
    "....DDMMMMMDD",
    ".....DDDDDDD.",
    ".............",
    ".............",
    ".............",
    ".............",
    ".............",
    ".............",
    ".............",
    ".............",
    ".............",
], 13)

PAULDRON_R = g([
    "DDDDDDD....",
    "DMMMMMDD...",
    "DMMMMMMD...",
    "DDMMMMMD...",
    ".DDDDDDD...",
    "...........",
    "...........",
    "...........",
    "...........",
    "...........",
    "...........",
], 11)

# GREVAS — placa sobre o cano da bota; o pe fica exposto.
GREAVE_L = g([
    "....DDDDDDDD",
    "...DDMMMMMDD",
    "..DDMMMMMMDD",
    "..DDMMMMMMDD",
    "...DDDDDDDD.",
    "............",
    "............",
], 12)

GREAVE_R = g([
    "DDDDDDDD..",
    "DDMMMMMDD.",
    "DDMMMMMMDD",
    "DDMMMMMMDD",
    ".DDDDDDDD.",
    "..........",
    "..........",
], 10)

# CINTURA da calca, presa ao tronco (na linha do cinto do goblin).
HIP = g([
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "....DDDDDDDDDDDDDDDD........",
    "....DMMMMMMMMMMMMMMD........",
    "...DMMMMMMMMMMMMMMMMD.......",
    "...DMMMMMMMMMMMMMMMMD.......",
    "...DDMMMMMMMMMMMMMMDD.......",
    "....DDDDDDDDDDDDDDDD........",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
    "............................",
], 28)

# ---- armas: um desenho por orientacao da adaga do rig ----
# Cada grade cobre EXATAMENTE a silhueta da adaga nativa (overlay so
# adiciona pixels, nunca apaga), por isso os formatos batem com R.SWORDS.
SWORD_SKIN = {
    'down': (g([
        ".GG.",
        "GGGG",
        "GMMG",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        ".DMD",
        "..D.",
    ], 4), 0, 0),
    'diag': (g([
        ".......DD",
        "......DLD",
        ".....DLMD",
        "D.D.DLLMD",
        "DDDDLLMDD",
        "MMDMLMDD.",
        "GMGMDDD..",
        "...GGD...",
        "...GDD...",
    ], 9), 0, 0),
    'fwd': (g([
        ".DDDDDDDDDD.",
        "DGGMLLLLLLLD",
        "DGGMLLLLLLMD",
        ".DDDDDDDDDD.",
    ], 12), 0, 0),
    'up': (g([
        ".D..",
        "DLD.",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "DMLD",
        "GMMG",
        "GGGG",
        ".GG.",
    ], 4), 0, 0),
}

CLUB_SKIN = {
    'down': (g([
        ".GG.",
        "GGGG",
        "GMMG",
        "DMMD",
        "DMLD",
        "DMMD",
        "DMMD",
        "DMLD",
        "DMMD",
        "DMMD",
        ".DMD",
        "..D.",
    ], 4), 0, 0),
    'diag': (g([
        ".......MM",
        "......MMD",
        ".....MMMD",
        "M.M.MMLMD",
        "MMMMMMLMD",
        "GMGMMMMD.",
        "GGGGMDD..",
        "...GGD...",
        "...GDD...",
    ], 9), 0, 0),
    'fwd': (g([
        ".DMMMMMMMMD.",
        "GGGMMLLMMMMD",
        "GGGMMLLMMMMD",
        ".DMMMMMMMMD.",
    ], 12), 0, 0),
    'up': (g([
        ".D..",
        "DMD.",
        "DMMD",
        "DMLD",
        "DMMD",
        "DMMD",
        "DMLD",
        "DMMD",
        "DMMD",
        "GMMG",
        "GGGG",
        ".GG.",
    ], 4), 0, 0),
}

SHIELD = g([
    "...DDDD...",
    "..DMMMMD..",
    ".DMMMMMMD.",
    "DMMMMMMMMD",
    "DMMGGGGMMD",
    "DMMGGGGMMD",
    "DMMGGGGMMD",
    "DMMMMMMMMD",
    ".DMMMMMMD.",
    "..DMMMMD..",
    "...DDDD...",
], 10)


def _layer(anchor, rows, material, dx=0, dy=0):
    return {'anchor': anchor, 'grid': paint(rows, material), 'dx': dx, 'dy': dy}


def helm(material):
    return [_layer('head', HELM, material)]


def chest(material):
    return [
        _layer('torso', CHEST, material),
        _layer('arm_l', PAULDRON_L, material),
        _layer('arm_r', PAULDRON_R, material),
    ]


def pants(material):
    return [
        _layer('torso', HIP, material),
        _layer('leg_l', GREAVE_L, material),
        _layer('leg_r', GREAVE_R, material),
    ]


def weapon(skin, material):
    """Arma: um desenho por orientacao, escolhido pelo tipo de espada da pose."""
    return [{'anchor': 'sword', 'material': material, 'by_kind': {
        k: (paint(rows, material), dx, dy) for k, (rows, dx, dy) in skin.items()
    }}]


def shield(material):
    # Escudo no braco LIVRE (a adaga esta na mao direita, como na referencia).
    return [_layer('arm_l', SHIELD, material, dx=-1, dy=3)]


# ------------------------------------------------------------- catalogo ----
# prefixo -> (camadas, pasta do sprite completo ou None)
PIECES = {
    'av_cap':     (helm('avaritia'), 'avaritia'),
    'av_pei':     (chest('avaritia'), 'avaritia'),
    'av_cal':     (pants('avaritia'), 'avaritia'),
    'av_cap_pei': (helm('avaritia') + chest('avaritia'), 'avaritia'),
    'av_cap_cal': (helm('avaritia') + pants('avaritia'), 'avaritia'),
    'av_pei_cal': (chest('avaritia') + pants('avaritia'), 'avaritia'),
    'av_full':    (helm('avaritia') + chest('avaritia') + pants('avaritia'), 'avaritia'),
    'ferro_cap':  (helm('ferro'), None),
    'ferro_pei':  (chest('ferro'), 'goblins'),
    'ferro_cal':  (pants('ferro'), None),
    'wpn_espada': (weapon(SWORD_SKIN, 'ferro'), None),
    'wpn_clava':  (weapon(CLUB_SKIN, 'madeira'), None),
    'wpn_escudo': (shield('madeira'), None),
}

# Icones 16x16 do inventario: recorte da parte do corpo que a peca cobre.
ICONS = {
    'av_cap_icon': ('av_cap', R.ANCHORS['head_box']),
    'av_pei_icon': ('av_pei', (17, 38, 48, 57)),
    'av_cal_icon': ('av_cal', (14, 48, 45, 63)),
}


def resolve(layers, kind):
    """Troca as camadas 'by_kind' pela orientacao certa da arma."""
    out = []
    for layer in layers:
        if 'by_kind' in layer:
            if kind not in layer['by_kind']:
                continue
            rows, dx, dy = layer['by_kind'][kind]
            out.append({'anchor': 'sword', 'grid': rows, 'dx': dx, 'dy': dy})
        else:
            out.append(layer)
    return out
