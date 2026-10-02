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
# Todos os desenhos abaixo foram remapeados para a geometria do goblin novo
# (recortado da arte de referencia): cabeca 24x12, tronco 18x14, bracos
# 8x9 / 7x7, pernas 8x4 / 7x4. O rosto, as orelhas e as botas ficam a vista.

# CAPACETE — calota sobre o cranio (cols 8..18), orelhas livres.
HELM = g([
    "........DDDDDDDDDDD.....",
    "........DMMLLMMMMMD.....",
    "........DMMMMMMMMMD.....",
    "........DMMMMMMMMMD.....",
    "........DDDGGGGDDDD.....",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
], 24)

# PEITORAL — placa sobre o peito; o cinto e o calcao continuam do goblin.
CHEST = g([
    ".....DDDDDDD......",
    "....DMMMMMMMD.....",
    "....DMMLLLMMD.....",
    "....DMGGGGGMD.....",
    "....DMMMMMMMD.....",
    "....DDMMMMMDD.....",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
], 18)

# OMBREIRAS — uma para cada braco (grades de larguras diferentes).
PAULDRON_L = g([
    "...DDDD.",
    "...DMMD.",
    "...DDDD.",
    "........",
    "........",
    "........",
    "........",
    "........",
    "........",
], 8)

PAULDRON_R = g([
    "DDDD...",
    "DMMD...",
    "DDDD...",
    ".......",
    ".......",
    ".......",
    ".......",
], 7)

# GREVAS — placa sobre o cano da bota.
GREAVE_L = g([
    "..DDDDDD",
    ".DDMMMDD",
    "........",
    "........",
], 8)

GREAVE_R = g([
    "DDDDD..",
    "DDMMDD.",
    ".......",
    ".......",
], 7)

# CINTURA da calca, presa ao tronco (linha do cinto do goblin).
HIP = g([
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..DDDDDDDDDDDD....",
    "..DMMMMMMMMMMD....",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
    "..................",
], 18)

# ---- armas: um desenho por orientacao da adaga do rig ----
# Cada desenho cobre EXATAMENTE a silhueta da adaga nativa (overlay so
# adiciona pixels, nunca apaga), por isso as grades batem com R.SWORDS.
SWORD_SKIN = {
    'down': (g([
        ".GG.",
        "DGGD",
        "DMLD",
        "DMLD",
        "DMLD",
        ".DD.",
    ], 4), 0, 0),
    'diag': (g([
        "....D",
        "...DD",
        ".DDDM",
        "DDLMD",
        "GGLMD",
        ".GDD.",
    ], 5), 0, 0),
    'fwd': (g([
        ".DDDDD.",
        "DGGMMMD",
        "DGGLLMD",
        ".DDDDD.",
    ], 7), 0, 0),
    'up': (g([
        ".DD.",
        "DMLD",
        "DMLD",
        "DMLD",
        "DGGD",
        ".GG.",
    ], 4), 0, 0),
}

CLUB_SKIN = {
    'down': (g([
        ".GG.",
        "DGGD",
        "DMMD",
        "DMLD",
        "DMMD",
        ".DD.",
    ], 4), 0, 0),
    'diag': (g([
        "....M",
        "...MM",
        ".GMMM",
        "GGMLM",
        "GGMMD",
        ".GDD.",
    ], 5), 0, 0),
    'fwd': (g([
        ".DMMMD.",
        "GGMMMMD",
        "GGMMLMD",
        ".DMMMD.",
    ], 7), 0, 0),
    'up': (g([
        ".MM.",
        "DMMD",
        "DMLD",
        "DMMD",
        "DGGD",
        ".GG.",
    ], 4), 0, 0),
}

SHIELD = g([
    "..DD..",
    ".DMMD.",
    "DMMMMD",
    "DMGGMD",
    "DMGGMD",
    "DMMMMD",
    ".DMMD.",
    "..DD..",
], 6)


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
    return [_layer('arm_l', SHIELD, material, dx=-1, dy=2)]


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
    'av_pei_icon': ('av_pei', (6, 17, 21, 28)),
    'av_cal_icon': ('av_cal', (5, 23, 24, 31)),
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
