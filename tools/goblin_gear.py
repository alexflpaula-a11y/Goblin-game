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
# CAPACETE — cobre a calota e desce num filete sobre as tempora; o rosto,
# as orelhas e a boca continuam a vista.
HELM = g([
    "......DDDDDD......",
    "......MMLMMM......",
    "......MMMMMM......",
    "....DMMMMMMMMD....",
    "....DMMGGMMMMD....",
    ".....DMMMMMMD.....",
    "..................",
    "..................",
    "..................",
    "..................",
], 18)

# PEITORAL — placa do peito; o cinto e o calcao continuam do goblin.
CHEST = g([
    "..DDDDDD..",
    ".DMMMMMMD.",
    "DMMMLLMMMD",
    "DMMGGGGMMD",
    "DMMMMMMMMD",
    "..........",
    "..........",
], 10)

# OMBREIRA — duas linhas sobre a manga, uma em cada braco.
PAULDRON = g([
    "DDD",
    "DMD",
    "...",
    "...",
    "...",
    "...",
], 3)

# CALCA — grevas sobre a coxa e a canela; a bota fica exposta.
GREAVE = g([
    "DDDD",
    "DMMD",
    "DMMD",
    "DDDD",
    "....",
    "....",
], 4)

# CINTURA da calca, presa ao tronco.
HIP = g([
    "..........",
    "..........",
    "..........",
    "..........",
    "..........",
    "..........",
    "DMMMMMMMMD",
], 10)

# ---- armas: um desenho por orientacao da espada do rig ----
SWORD_SKIN = {
    'down': (g([
        ".G.",
        "GGG",
        "MLM",
        "MLM",
        "MLM",
        "MLM",
        "MLM",
        "MLM",
        ".M.",
    ], 3), 0, -2),
    'diag': (g([
        ".....L",
        "....LL",
        "...LL.",
        ".GLL..",
        "GGM...",
        "G.....",
    ], 6), 0, 0),
    'fwd': (g([
        "GGMLLLLL",
        ".GMLLLLL",
        "...LLL..",
    ], 8), 0, 0),
    'up': (g([
        ".L.",
        "MLM",
        "MLM",
        "MLM",
        "MLM",
        "GGG",
        ".G.",
    ], 3), 0, 0),
}

CLUB_SKIN = {
    'down': (g([
        ".GG.",
        ".GG.",
        ".GG.",
        "DMMD",
        "DMLD",
        "DMMD",
        "DMMD",
        ".DD.",
    ], 4), -1, -1),
    'diag': (g([
        "....MM",
        "...MMD",
        "..MMD.",
        ".GMD..",
        "GGD...",
        "G.....",
    ], 6), 0, 0),
    'fwd': (g([
        "GGMMMMDD",
        ".GMMMMMD",
        "...MMM..",
    ], 8), 0, 0),
    'up': (g([
        ".DD.",
        "DMMD",
        "DMLD",
        "DMMD",
        ".GG.",
        ".GG.",
        ".GG.",
    ], 4), -1, 0),
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
        _layer('arm_l', PAULDRON, material),
        _layer('arm_r', PAULDRON, material),
    ]


def pants(material):
    return [
        _layer('torso', HIP, material),
        _layer('leg_l', GREAVE, material),
        _layer('leg_r', GREAVE, material),
    ]


def weapon(skin, material):
    """Arma: um desenho por orientacao, escolhido pelo tipo de espada da pose."""
    return [{'anchor': 'sword', 'material': material, 'by_kind': {
        k: (paint(rows, material), dx, dy) for k, (rows, dx, dy) in skin.items()
    }}]


def shield(material):
    return [_layer('arm_r', SHIELD, material, dx=2, dy=-1)]


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
    'av_pei_icon': ('av_pei', (8, 19, 23, 27)),
    'av_cal_icon': ('av_cal', (10, 24, 21, 31)),
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
