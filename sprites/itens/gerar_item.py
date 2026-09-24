#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gerar_item.py — gera os sprites de itens seguindo o design padrão do jogo.

 Lê os frames do goblin direto do vila-de-goblins-jogavel.html (window.EMBEDDED)
 e produz, para cada item configurado em ITENS:

   icon.png                 16×16  (inventário)
   drop.png                 32×32  (caído no chão + brilho azul embutido)
   goblin_<anim>_<n>.png    32×32  (goblin equipado — TODAS as animações)

 Peças de skin são "moldadas" no corpo: pintam apenas pixels do corpo
 (pele/cinto/tanga conforme a zona), ancorados pelos olhos por frame —
 totalmente opacas (sem transparecer).

 ┌─ GUARDA DE ROSTO (regra dura p/ QUALQUER equipamento) ──────────────────┐
 │ Nenhum equipamento pinta no rosto. Verificado frame a frame; se violar, │
 │ o script ERRA e nada é gerado:                                          │
 │  • zona torso : em pé, ≥4 px dos olhos | deitado, abaixo da boca e ≥2px │
 │  • zona cabeça: em pé, ≥2 px dos olhos e ACIMA da sobrancelha          │
 │                 | deitado, ≥3 px da boca (só no alto da cabeça)         │
 │  • zona pernas: em pé, ≥6 px abaixo dos olhos | deitado, como torso    │
└─────────────────────────────────────────────────────────────────────────┘

 ZONAS
  • torso  — banda olhos+4..olhos+8 (em pé); máscaras explícitas (deitado)
  • cabeca — coroa (topo da cabeça até 2px acima dos olhos) + janela ±4 do cx
  • pernas — tanga/cinto marrom + pernas verdes abaixo do torso

 ESTILOS
  • ferro    — aço cinza (peitoral_ferro)
  • avaritia — placas escuras + bordas de aço azul + gemas teal (ref. zip)

 Para criar um NOVO item: acrescente um bloco em ITENS. Requer Pillow.
"""
import base64
import io
import json
import os
import re

from PIL import Image, ImageDraw

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME_HTML = os.path.join(REPO, 'vila-de-goblins-jogavel.html')

# ---------- paletas ----------
# cores do corpo
GREENS = {(80, 189, 111), (114, 210, 142), (69, 165, 96)}   # pele
BROWNS = {(105, 72, 58), (145, 100, 81), (98, 64, 35)}      # tanga/cinto/strap
WHITE  = (241, 240, 253)                                    # olhos
YELLOW = (225, 230, 164)                                    # boca

# estilo ferro
F_O = (47, 47, 46, 255); F_L = (205, 212, 224, 255); F_M = (165, 175, 190, 255)
F_D = (120, 128, 142, 255); F_RIV = (241, 240, 253, 255)

# estilo avaritia — ICONES (fiéis ao zip "Avaritia armour")
A_K = (28, 28, 32, 255)      # placa escura
A_k = (45, 45, 50, 255)      # sombra da placa
A_L = (162, 175, 214, 255)   # aço claro (borda/bevel)
A_M = (143, 156, 192, 255)   # aço
A_m = (135, 146, 177, 255)   # aço médio
A_d = (120, 131, 162, 255)   # aço escuro
A_T = (45, 206, 164, 255)    # gema teal
A_t = (48, 173, 161, 255)    # gema teal escura
A_j = (41, 170, 195, 255)    # gema azul-teal (base da gema da perna — arte original)

# estilo avaritia — PERSONAGEM (100% baseado na imagem de referência enviada:
# placas praticamente pretas, bevels cinza-azulados escuros, gema grande no
# peito, visor e gemas das pernas em teal brilhante)
R_K = (8, 8, 10, 255)       # placa: preto (referência)
R_k = (22, 22, 26, 255)      # sombra da placa
R_L = (65, 65, 77, 255)      # borda/bevel clara (cinza-azulado escuro)
R_M = (55, 55, 65, 255)      # bevel médio
R_m = (48, 48, 58, 255)      # bevel
R_d = (40, 40, 50, 255)      # bevel escuro

PAL_ICON = {'O': F_O, 'L': F_L, 'M': F_M, 'D': F_D, 'S': (80, 87, 99, 255),
            'B': (105, 72, 58, 255), 'b': (145, 100, 81, 255),
            'd': (98, 64, 35, 255), 'R': F_RIV,
            # avaritia
            'K': A_K, 'k': A_k, 'm': A_m, 'T': A_T, 't': A_t,
            # avaritia — tons escuros/da arte original (ícones fiéis)
            '#': (17, 17, 17, 255), '?': A_K, 'o': (29, 29, 29, 255),
            '+': (45, 45, 50, 255), ';': (34, 34, 38, 255),
            '^': (40, 40, 45, 255), 'u': (41, 115, 195, 255),
            'x': A_d, 'w': A_M, 'v': A_L,
            # tons EXATOS da imagem original (ícone do peitoral)
            'Z': (0, 0, 0, 255), 'X': (25, 25, 25, 255),
            'V': (40, 40, 40, 255), 'W': (152, 165, 201, 255),
            'N': (12, 12, 12, 255), 'z': (30, 30, 30, 255),
            'a': (45, 45, 45, 255), 'p': (34, 34, 34, 255),
            'j': (41, 170, 195, 255)}

# ============================ ITENS ============================
ITENS = [
 # --------- 1) item padrão de referência ---------
 dict(
    id='peitoral_ferro', slot='peitoral', zona='torso', estilo='ferro',
    aparece_na_skin=True, cai_no_chao_ao_morrer=False,
    icon=[
        "................",
        "..OOOO....OOOO..",
        ".OLLLLO..OLLLLO.",
        ".OLMMMO..OMMMLO.",
        ".OMMSSOOOOSSMMO.",
        "OMMSSLLMMLLSSMMO",
        "OMSSLMMLLMMLSSMO",
        "OMSLMMDDMMDDMMSO",
        "OMSMMDDMMDDMMMSO",
        ".OMMDDMMMMDDMMO.",
        ".OMDMDDDDDDMDMO.",
        ".OMDMDDDDDDMDMO.",
        ".OdBBBBBBBBBdO..",
        "..OBBbRRbBBBO...",
        "..OOOOOOOOOO....",
        "................",
    ],
    mascaras_deitadas={
        'goblin_death_3':  {27: [15, 16, 17, 18]},
        'goblin_death_4':  {28: [15, 16], 29: [16, 17, 18]},
        'goblin_death_5':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
        'goblin_death_6':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
        'goblin_death_7':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
    },
    duplicados={
        'goblin_death_11': 'goblin_death_3',
        'goblin_death_12': 'goblin_death_4',
        'goblin_death_13': 'goblin_death_5',
        'goblin_death_14': 'goblin_death_7',
    },
 ),
 # --------- 2) conjunto AVARITIA: peitoral ---------
 dict(
    id='peitoral_avaritia', slot='peitoral', zona='torso', estilo='avaritia',
    aparece_na_skin=True, cai_no_chao_ao_morrer=False,
    # ícone FIEL à arte original (sprite_1 do zip, 10×10 centralizado)
    icon=[
        "................",
        "................",
        "................",
        ".....xmmwww.....",
        "....xzZZXXXx....",
        "...xzZZZXXXzx...",
        "...wzZZXXXXzw...",
        "...wzTTZXTTzw...",
        "...xzZZVZZXzm...",
        "...WzZZZNzzzm...",
        "...xxwNNZNxmw...",
        "......NxwN......",
        "......#..#......",
        "................",
        "................",
        "................",
    ],
    mascaras_deitadas={
        'goblin_death_3':  {27: [15, 16, 17, 18]},
        'goblin_death_4':  {28: [15, 16], 29: [16, 17, 18]},
        'goblin_death_5':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
        'goblin_death_6':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
        'goblin_death_7':  {29: [15, 16, 17], 30: [16, 17, 18, 19]},
    },
    duplicados={
        'goblin_death_11': 'goblin_death_3',
        'goblin_death_12': 'goblin_death_4',
        'goblin_death_13': 'goblin_death_5',
        'goblin_death_14': 'goblin_death_7',
    },
 ),
 # --------- 3) conjunto AVARITIA: capacete (FECHADO — tampa o rosto) ---------
 dict(
    id='capacete_avaritia', slot='capacete', zona='cabeca', estilo='avaritia',
    aparece_na_skin=True, cai_no_chao_ao_morrer=False,
    tampa_rosto=True,   # ← capacete fechado: cobre o rosto todo; só as ORELHAS ficam de fora
    # ícone FIEL à arte original (sprite_2: elmo com 2 chifres de ponta teal)
    icon=[
        "................",
        "....xx....mm....",
        "..xW##m..w#amW..",
        ".uo#ZZZmW###ooT.",
        ".To#ZZZZ####oau.",
        ".Wo#ZZZpZZ#ooaW.",
        ".Wo#ZZptTp#ooaW.",
        "..mo#Zpjt##oaW..",
        "..Wo##ZZZ##oam..",
        "...mo######om...",
        "...Wo#####oaW...",
        "...Woo###ooaW...",
        "...WaoooooaaW...",
        "....xaaaaaam....",
        ".....xWxmmW.....",
        "................",
    ],
    # deitado: capacete fechado cobre a cabeça inteira (boca coberta),
    # pontas das orelhas (topo) ficam verdes
    mascaras_deitadas={
        'goblin_death_3':  {19: [15, 16, 17, 19, 20],
                            20: [12, 13, 14, 15, 16, 17, 18, 20],
                            21: [13, 14, 15, 16, 17, 18, 19],
                            22: [14, 15, 16, 17, 18, 19],
                            23: [14, 15, 16, 17, 18, 19, 20],
                            24: [14, 15, 16, 17, 18, 19],
                            25: [14, 15]},
        'goblin_death_4':  {21: [14, 16, 17, 18, 20, 21],
                            22: [14, 15, 16, 17, 18, 19, 21],
                            23: [14, 15, 16, 17, 18, 19, 20],
                            24: [15, 16, 17, 18, 19, 20],
                            25: [15, 16, 17, 18, 19, 20, 21],
                            26: [15, 16, 17, 18, 19, 20],
                            27: [15, 16]},
        'goblin_death_5':  {22: [16, 17, 18, 20, 21],
                            23: [13, 14, 15, 16, 17, 18, 19, 21],
                            24: [14, 15, 16, 17, 18, 19, 20],
                            25: [15, 16, 17, 18, 19, 20],
                            26: [15, 16, 17, 18, 19, 20, 21],
                            27: [15, 16, 17, 18, 19, 20],
                            28: [15, 16]},
        'goblin_death_6':  {22: [16, 17, 18],
                            23: [12, 13, 14, 15, 16, 17, 18, 19, 21],
                            24: [14, 15, 16, 17, 18, 19, 20],
                            25: [15, 16, 17, 18, 19, 20],
                            26: [15, 16, 17, 18, 19, 20, 21],
                            27: [15, 16, 17, 18, 19, 20],
                            28: [15, 16]},
        'goblin_death_7':  {22: [16, 17, 18],
                            23: [14, 15, 16, 17, 18, 19, 21, 22],
                            24: [12, 13, 14, 15, 16, 17, 18, 19, 20],
                            25: [15, 16, 17, 18, 19, 20],
                            26: [15, 16, 17, 18, 19, 20, 21],
                            27: [15, 16, 17, 18, 19, 20],
                            28: [15, 16]},
    },
    duplicados={
        'goblin_death_11': 'goblin_death_3',
        'goblin_death_12': 'goblin_death_4',
        'goblin_death_13': 'goblin_death_5',
        'goblin_death_14': 'goblin_death_7',
    },
 ),
 # --------- 4) conjunto AVARITIA: calça ---------
 dict(
    id='calca_avaritia', slot='calcas', zona='pernas', estilo='avaritia',
    aparece_na_skin=True, cai_no_chao_ao_morrer=False,
    # ícone FIEL à arte original (sprite_3: pernas com trilhos de aço e
    # gemas teal na lateral, na altura do joelho)
    icon=[
        "................",
        "....mxwwvxvv....",
        "...xzZZZ###ox...",
        "...wzZZ###oov...",
        "...wz###oooav...",
        "...xz#oxxooax...",
        "...xz#w..xoax...",
        "...wz#v..woax...",
        "...wtTx..xtTw...",
        "...xjtv..xjtx...",
        "...xz#v..woax...",
        "...wzzv..woav...",
        "...xzav..xoax...",
        "...xwxw..xwwv...",
        "................",
        "................",
    ],
    # deitado: pernas/quadril (embaixo da boca, longe do rosto)
    mascaras_deitadas={
        'goblin_death_3':  {28: [12, 13, 14],
                            29: [12, 13, 14, 15, 16, 17], 30: [12, 13, 16, 17]},
        'goblin_death_4':  {26: [12, 13], 27: [13], 28: [10, 11, 13],
                            29: [12, 13, 14], 30: [11, 12]},
        'goblin_death_5':  {27: [12, 13], 28: [11, 12, 13],
                            29: [9, 10, 11, 12, 13], 30: [9, 10, 12, 13]},
        'goblin_death_6':  {27: [12, 13], 28: [11, 12, 13],
                            29: [9, 10, 11, 12, 13], 30: [9, 10, 12, 13]},
        'goblin_death_7':  {27: [12, 13], 28: [11, 12, 13],
                            29: [9, 10, 11, 12, 13], 30: [9, 10, 12, 13]},
    },
    duplicados={
        'goblin_death_11': 'goblin_death_3',
        'goblin_death_12': 'goblin_death_4',
        'goblin_death_13': 'goblin_death_5',
        'goblin_death_14': 'goblin_death_7',
    },
 ),
]
# ====================================================================

def extrai_frames():
    html = open(GAME_HTML, encoding='utf-8').read()
    m = re.search(r'window\.EMBEDDED = (\{.*?\});\n', html, re.S)
    data = json.loads(m.group(1))
    return {k: Image.open(io.BytesIO(base64.b64decode(v.split(',')[1]))).convert('RGBA')
            for k, v in data['sprites'].items() if k.startswith('goblin_')}


def olhos_px(px):
    return [(x, y) for y in range(32) for x in range(32)
            if px[x, y][3] >= 40 and px[x, y][:3] == WHITE]


def boca_px(px):
    return [(x, y) for y in range(32) for x in range(32)
            if px[x, y][3] >= 40 and px[x, y][:3] == YELLOW]


# ─────────────────────────── GUARDA DE ROSTO ───────────────────────────
def guarda_rosto(nome, px, painted, zona, tampa_rosto=False):
    """Nenhum equipamento pinta no rosto. Verificado frame a frame; se violar,
    o script ERRA e nada é gerado:
      • zona torso : em pé, ≥4 px dos olhos | deitado, abaixo da boca e ≥2px
      • zona cabeça: em pé, ≥2 px dos olhos e ACIMA da sobrancelha
                     | deitado, ≥3 px da boca (só no alto da cabeça)
      • zona pernas: em pé, ≥6 px abaixo dos olhos | deitado, como torso
    EXCEÇÃO (por design): peças com tampa_rosto=True (capacete fechado)
    DEVEM cobrir o rosto — só as orelhas ficam de fora.
    """
    if tampa_rosto and zona == 'cabeca':
        return          # capacete fechado: cobre o rosto intencionalmente
    eyes, mouth = olhos_px(px), boca_px(px)
    erros = []
    for (x, y) in painted:
        if eyes:
            if zona == 'cabeca':
                # só acima da sobrancelha e nunca colado no olho
                if y > min(ey for _, ey in eyes) - 2 or \
                   any(max(abs(x - ex), abs(y - ey)) <= 1 for ex, ey in eyes):
                    erros.append((x, y, 'no ROSTO (zona cabeça)'))
            elif zona == 'pernas':
                if y < max(ey for _, ey in eyes) + 6:
                    erros.append((x, y, 'perto do ROSTO (zona pernas)'))
            else:  # torso
                if any(max(abs(x - ex), abs(y - ey)) <= 3 for ex, ey in eyes):
                    erros.append((x, y, 'perto dos OLHOS'))
        elif mouth:
            if zona == 'cabeca':
                if any(max(abs(x - mx), abs(y - my)) <= 2 for mx, my in mouth):
                    erros.append((x, y, 'no ROSTO (cabeça deitado)'))
            else:  # torso / pernas deitado
                # rosto = ao redor da boca e tudo acima da linha da boca
                # que esteja sob a cabeça (x próximo ou à direita da boca)
                if any(max(abs(x - mx), abs(y - my)) <= 1 for mx, my in mouth) or \
                   any(y <= my and x >= mx - 5 for mx, my in mouth):
                    erros.append((x, y, 'no ROSTO (boca)'))
        else:
            erros.append((x, y, 'frame sem âncora de rosto'))
    if erros:
        raise SystemExit('[GUARDA DE ROSTO] %s (%s): %s' % (nome, zona, erros))


# ─────────────────────────── MÁSCARAS ───────────────────────────
def expande_cluster(xs, seed):
    chosen = set(seed); mudou = True
    while mudou:
        mudou = False
        for x in xs:
            if x not in chosen and any(abs(x - c) <= 1 for c in chosen):
                chosen.add(x); mudou = True
    return sorted(chosen)


def mascara_torso_em_pe(px, eye_x, eye_y):
    """banda olhos+4 .. olhos+8, propagando por conectividade desde os ombros"""
    c = int(eye_x + 0.5)
    top = int(eye_y + 0.5) + 4
    painted, prev = {}, None
    for r in range(5):
        y = top + r
        xs = [x for x in range(32) if px[x, y][3] >= 40 and px[x, y][:3] in GREENS]
        if r == 0:
            if not xs:
                break
            chosen = expande_cluster(xs, [x for x in xs if abs(x - c) <= 3])
        else:
            if prev is None:
                continue
            chosen = [x for x in xs if any(abs(x - p) <= 2 for p in prev)]
        if chosen:
            painted[y] = chosen; prev = chosen
        else:
            prev = None
    return painted


def mascara_pernas_em_pe(px, eye_y):
    """tanga/cinto marrom + pernas verdes, abaixo do torso.
    marrom: y ≥ eye+8 | verde (perna): y ≥ eye+10 (nunca os pés-borda)."""
    eb = int(eye_y + 0.5)
    for top_b, top_g in ((eb + 8, eb + 10), (eb + 6, eb + 8)):
        # 2ª tentativa (janela 2px mais alta): frames com a cabeça abaixada
        # (olhos y21-22) têm a tanga em y28-29 — a janela primária os perde
        # e a calça sumia inteira (death_1/9, hurt_1...)
        painted = {}
        for y in range(top_b, 32):
            xs = [x for x in range(32)
                  if px[x, y][3] >= 40 and (px[x, y][:3] in BROWNS or
                    (y >= top_g and px[x, y][:3] in GREENS))]
            if xs:
                painted[y] = xs
        if painted:
            return painted
    return {}


def mascara_cabeca_em_pe(px, eye_x, eye_y):
    """coroa: pixels de pele até 2px ACIMA do topo dos olhos, janela ±4 do
    centro da cabeça (eye_cx+1 — os olhos deslocam quando o goblin inclina)"""
    eyes = olhos_px(px)
    eye_top = min(ey for _, ey in eyes)
    cx = int(round(eye_x)) + 1
    painted = {}
    for y in range(0, eye_top - 1):          # y ≤ eye_top-2
        xs = [x for x in range(max(0, cx - 4), min(32, cx + 5))
              if px[x, y][3] >= 40 and px[x, y][:3] in GREENS]
        if xs:
            painted[y] = xs
    if painted:
        topo = min(painted)                   # 1ª linha: descarta pixels isolados
        runs = [r for r in _runs(painted[topo]) if len(r) >= 2]
        if runs:
            painted[topo] = [x for r in runs for x in r]
        else:
            del painted[topo]
    return painted


def mascara_cabeca_fechada_em_pe(px):
    """CAPACETE FECHADO — passo 1: TODA a cabeça PRETA (coroa, têmporas,
    rosto, até a boca). As ORELHAS são restauradas depois, por cima do
    preto (restaura_orelhas)."""
    eyes = olhos_px(px)
    mouth = boca_px(px)
    emin = min(x for x, _ in eyes); emax = max(x for x, _ in eyes)
    eye_top = min(y for _, y in eyes)
    my = max(y for _, y in mouth) if mouth else max(y for _, y in eyes) + 3
    W0, W1 = max(0, emin - 4), min(31, emax + 4)
    mask = {}
    for y in range(max(0, eye_top - 4), my + 1):
        xs = [x for x in range(W0, W1 + 1)
              if px[x, y][3] >= 40 and px[x, y][:3] in GREENS]
        if xs:
            mask[y] = xs
    return mask


def _dome_y(base_px, W0, W1, y0, my):
    """1ª linha (de y0 até my) em que a cabeça fica larga (run >= 6)."""
    for y in range(y0, my + 1):
        xs = [x for x in range(W0, W1 + 1)
              if base_px[x, y][3] >= 40 and base_px[x, y][:3] in GREENS]
        cont = best = (1 if xs else 0)
        for a, b in zip(xs, xs[1:]):
            cont = cont + 1 if b == a + 1 else 1
            best = max(best, cont)
        if best >= 6:
            return y
    return None


def restaura_orelhas(im, base_px):
    """CAPACETE FECHADO — passo 2: CONSERTA AS ORELHAS (fiéis ao sprite).
    dome = 1ª linha em que o crânio fica largo (run >= 6); o run largo
    dessa linha é a MASSA do crânio.
    ORELHA = run de verdes ACIMA do dome que sai pra FORA da massa
    (pontuando ao lado do crânio); na linha do dome, run SEPARADO da
    massa que continua uma orelha de cima = base da orelha.
    A COROA (run em cima da massa, dentro do vão) fica PRETA — o elmo
    cobre a cabeça inteira. Abaixo do dome: nada (rosto).
    O goblin é 3/4: a orelha direita (x17-20) aparece sempre, a esquerda
    (x10-12) só quando a cabeça vira — igual ao sprite original."""
    eyes = olhos_px(base_px)
    if not eyes:
        return set()
    emin = min(x for x, _ in eyes); emax = max(x for x, _ in eyes)
    eye_top = min(y for _, y in eyes)
    mouth = boca_px(base_px)
    my = max(y for _, y in mouth) if mouth else eye_top + 3
    W0, W1 = max(0, emin - 4), min(31, emax + 4)
    y0 = max(0, eye_top - 4)
    dome = _dome_y(base_px, W0, W1, y0, my)
    if dome is None:
        return set()
    xs_d = [x for x in range(W0, W1 + 1)
            if base_px[x, dome][3] >= 40 and base_px[x, dome][:3] in GREENS]
    if not xs_d:
        return set()
    wr = max(_runs(xs_d), key=len)          # massa do crânio (run largo)
    px = im.load()
    ears = set()
    ear_cols = set()                        # colunas de orelha na linha de cima
    for y in range(y0, dome + 1):           # dome+1 em diante é rosto — nada
        xs = [x for x in range(W0, W1 + 1)
              if base_px[x, y][3] >= 40 and base_px[x, y][:3] in GREENS]
        if not xs:
            ear_cols = set()
            continue
        runs = _runs(xs)
        if y < dome:
            # orelha: run que sai pra fora da massa do crânio
            sel = [x for r in runs if r[0] < wr[0] or r[-1] > wr[-1] for x in r]
        else:
            # linha do dome: só base separada da massa, ligada à orelha de cima
            sel = [x for r in runs if r != wr and len(r) <= 4 for x in r
                   if x - 1 in ear_cols or x in ear_cols or x + 1 in ear_cols]
        for x in sel:
            p = base_px[x, y]
            px[x, y] = p[:3] + (255,)
            ears.add((x, y))
        ear_cols = set(sel)
    return ears


def orelhas_a_preservar(px, mask):
    """pixels de ORELHA que devem continuar verdes mesmo no blackout total:
    todos os verdes ACIMA da 1ª linha do elmo (eye_top-2)."""
    eyes = olhos_px(px)
    if not eyes or not mask:
        return set()
    eye_top = min(y for _, y in eyes)
    topo = min(mask)
    return {(x, y) for y in range(0, topo)
            for x in range(32)
            if px[x, y][3] >= 40 and px[x, y][:3] in GREENS}


def _runs(xs):
    """divide lista de x's em trechos contíguos"""
    out, run = [], [xs[0]]
    for x in xs[1:]:
        if x == run[-1] + 1:
            run.append(x)
        else:
            out.append(run); run = [x]
    out.append(run)
    return out


def pinta_ferro(base, painted):
    im = base.copy(); px = im.load()
    rows = sorted(painted)
    for ri, y in enumerate(rows):
        xs = painted[y]
        shade = ['M', 'L', 'L', 'M', 'D'][ri] if ri < 5 else 'D'
        for x in xs:
            col = shade
            if x == xs[0]:
                col = 'L'
            elif x == xs[-1]:
                col = 'D'
            px[x, y] = {'L': F_L, 'M': F_M, 'D': F_D}[col]
        if ri == 1 and len(xs) >= 6:
            px[xs[1], y] = F_RIV; px[xs[-2], y] = F_RIV
    return im


def pinta_avaritia(base, painted, zona, deitado=False):
    """armadura avaritia no personagem: placas TOTALMENTE PRETAS + gemas teal"""
    im = base.copy(); px = im.load()
    rows = sorted(painted)
    for y in rows:
        for x in painted[y]:
            px[x, y] = R_K                # preto, sem borda cinza
    if zona == 'torso':
        _gema_peito(px, painted, rows, deitado)
    if zona == 'pernas':
        _gemas_pernas(px, painted, rows, base, deitado)
    return im


def _gema_peito(px, painted, rows, deitado):
    """DUAS gemas 2×1 lado a lado no peito, IGUAL À ARTE ORIGINAL
    (sprite_1: B#TT##TT#B — duas gemas A_T com vão central, sem sombra).
    Posição estável: linha do run mais largo (em pé: entre as 3 primeiras
    do torso). Vale para TODAS as versões com peitoral."""
    cand = rows if deitado else rows[:3]
    best = None
    for y in cand:
        rr = _runs(painted[y])
        if not rr:
            continue
        r = max(rr, key=len)
        if best is None or len(r) > len(best[1]):
            best = (y, r)
    if not best:
        return
    y, r = best
    s_, e = r[0], r[-1]
    w = e - s_ + 1
    if w >= 7:
        gemas = [[s_ + 1, s_ + 2], [e - 2, e - 1]]     # 2 gemas, vão central
    elif w == 6:
        gemas = [[s_ + 1, s_ + 2], [s_ + 4, s_ + 5]]   # vão de 1
    elif w == 5:
        gemas = [[s_ + 1], [e - 1]]                    # 2 gemas de 1px
    elif w == 4:
        gemas = [[s_ + 1, s_ + 2]]                     # 1 gema central
    elif w == 3:
        gemas = [[s_ + 1]]
    elif w == 2:
        gemas = [[s_, s_ + 1]]
    else:
        gemas = [[s_]]
    for g in gemas:
        for x in g:
            px[x, y] = A_T


def _gemas_pernas(px, painted, rows, base, deitado):
    """GEMAS DAS PERNAS iguais à arte original (sprite_3): 2×2 MISTA por
    perna — topo (A_t, A_T), base (A_j, A_t) — preenchendo a largura da
    perna (lado interno quando larga), a partir da 2ª linha abaixo do
    cós. Pernas juntas (de frente): 2 gemas espelhadas com vão central.
    Deitado: mesma regra. A gema nunca some."""
    bpx = base.load()
    yb = None
    if not deitado:
        yb = min((y for y in rows
                  if any(bpx[x, y][:3] in BROWNS for x in painted[y])), default=None)
    if yb is not None:
        cos_runs = _runs(painted[yb])
        centro = ((cos_runs[0][0] + cos_runs[-1][-1]) / 2) if cos_runs else 16.0
        ys = [r for r in rows if r > yb]
    else:
        centro = 16.0                     # sem cós (deitado/hurt): centro neutro
        ys = rows
    # componentes conexas: uma PERNA = um componente (pode ter várias runs
    # por linha — ex.: 2 pernas na mesma linha ligadas à de cima)
    comps = []
    for y in ys:
        for r in _runs(painted[y]):
            alvo = None
            for comp in comps:
                prev = comp.get(y - 1)
                if prev and any(set(r) & set(c) for c in prev):
                    if alvo is None:
                        comp.setdefault(y, []).append(r)
                        alvo = comp
            if alvo is None:
                comps.append({y: [r]})
    for comp in comps:
        ys_c = sorted(comp)
        gi = 1 if len(ys_c) >= 3 else 0  # 2ª linha da perna (arte: 3ª de 7)
        y = ys_c[gi]
        y2 = ys_c[gi + 1] if gi + 1 < len(ys_c) else None
        for run in comp[y]:
            w = len(run)
            if w >= 7:    # pernas juntas largas: 2 gemas espelhadas
                pares = [((run[1], run[2]), False), ((run[-3], run[-2]), True)]
            elif w == 6:
                pares = [((run[1], run[2]), False), ((run[4], run[5]), True)]
            elif w == 5:
                pares = [((run[1], run[1]), False), ((run[-2], run[-2]), True)]
            elif w == 4:  # par estreito: 1 gema central
                pares = [((run[1], run[2]), False)]
            elif w == 3:  # perna larga: gema no lado interno (2px)
                if (run[0] + run[-1]) / 2 < centro:
                    pares = [((run[1], run[2]), False)]
                else:
                    pares = [((run[0], run[1]), False)]
            elif w == 2:  # gema preenche a perna (como na arte)
                pares = [((run[0], run[1]), False)]
            else:         # w == 1
                px[run[0], y] = A_T
                if y2 is not None and run[0] in painted[y2]:
                    px[run[0], y2] = A_t
                continue
            for (x0, x1), espelho in pares:
                top = (A_T, A_t) if espelho else (A_t, A_T)
                bot = (A_t, A_j) if espelho else (A_j, A_t)
                px[x0, y] = top[0]
                if x1 != x0:
                    px[x1, y] = top[1]
                if y2 is not None:
                    if x0 in painted[y2]:
                        px[x0, y2] = bot[0]
                    if x1 != x0 and x1 in painted[y2]:
                        px[x1, y2] = bot[1]


def entre_orelhas_capacete(im, base_px, mask):
    """MOLDA o elmo nas linhas das ORELHAS (não adiciona nada fora do
    sprite): pinta de PRETO os pixels de contorno no vão ENTRE as duas
    orelhas e nos 2 pixels ao redor delas — o preto do elmo passa a envolver
    as orelhas, que ficam verdes pontando para fora. Os contornos ACIMA das
    orelhas são preservados (pontinhas das orelhas)."""
    if not mask:
        return
    ytop = min(mask)
    px = im.load()
    OUT = (47, 47, 46)
    for y in range(max(0, ytop - 2), ytop):
        xs = [x for x in range(32)
              if base_px[x, y][3] >= 40 and base_px[x, y][:3] in GREENS]
        if not xs:
            continue
        clusters, run = [], [xs[0]]
        for x in xs[1:]:
            if x == run[-1] + 1:
                run.append(x)
            else:
                clusters.append(run); run = [x]
        clusters.append(run)
        if len(clusters) < 2:
            continue
        lo = max(0, clusters[0][0] - 2)
        hi = min(31, clusters[-1][-1] + 2)
        for x in range(lo, hi + 1):
            p = px[x, y]
            if p[3] >= 40 and p[:3] == OUT:
                px[x, y] = R_K


def chifres_capacete(im, base_px, mask):
    """desenha os 2 chifres do elmo avaritia saindo do topo do domo
    (entre as orelhas), com ponta teal — como no capacete original.
    Só pinta sobre fundo transparente ou contorno — nunca sobre orelha/pele."""
    if not mask:
        return im
    ytop = min(mask)
    xs = mask[ytop]
    if len(xs) < 3:
        return im
    px = im.load()
    for x in (xs[0], xs[-1]):
        for dy, cor in ((-1, R_K), (-2, A_T)):
            y = ytop + dy
            if y < 0:
                continue
            p = base_px[x, y]
            if p[3] < 40 or p[:3] == (47, 47, 46):
                px[x, y] = cor
    return im


# ─────────────────────────── ICON / DROP ───────────────────────────
def make_icon(cfg):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0)); px = im.load()
    for y, row in enumerate(cfg['icon']):
        assert len(row) == 16, 'ícone 16 colunas (linha %d de %s)' % (y, cfg['id'])
        for x, ch in enumerate(row):
            if ch != '.':
                px[x, y] = PAL_ICON[ch]
    return im


def make_drop(icon):
    im = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    im.alpha_composite(icon, (8, 8))
    px = im.load()
    itempix = [(x, y) for y in range(32) for x in range(32) if px[x, y][3] >= 40]
    for y in range(32):
        for x in range(32):
            if px[x, y][3] >= 10:
                continue
            dmin = min((x - ix) ** 2 + (y - iy) ** 2 for ix, iy in itempix) ** 0.5
            dc = ((x - 15.5) ** 2 + (y - 15.5) ** 2) ** 0.5
            a = 0
            if dmin < 7:
                a = max(a, int(175 * (1 - dmin / 7) ** 1.15))
            if dc < 15:
                a = max(a, int(50 * (1 - dc / 15)))
            if a:
                px[x, y] = (96, 176, 255, a)
    d = ImageDraw.Draw(im)
    for (sx, sy, a) in [(6, 7, 235), (26, 9, 210), (9, 26, 225), (25, 24, 195)]:
        d.point((sx, sy), fill=(235, 250, 255, 255))
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            d.point((sx + dx, sy + dy), fill=(205, 235, 255, a))
    return im


# ─────────────────────────── MAIN ───────────────────────────
def alvo_valido(px, x, y, zona):
    c = px[x, y][:3]
    if zona == 'pernas':
        return c in BROWNS or c in GREENS
    return c in GREENS


def main():
    frames = extrai_frames()
    for cfg in ITENS:
        out = os.path.join(REPO, 'sprites', 'itens', cfg['id'])
        os.makedirs(out, exist_ok=True)
        icon = make_icon(cfg)
        icon.save(os.path.join(out, 'icon.png'))
        make_drop(icon).save(os.path.join(out, 'drop.png'))
        ger = 0
        for name, base in sorted(frames.items()):
            px = base.load()
            chave = cfg['duplicados'].get(name, name)
            deitado = chave in cfg['mascaras_deitadas']
            if deitado:
                mask = {int(y): list(xs)
                        for y, xs in cfg['mascaras_deitadas'][chave].items()}
            else:
                eyes = olhos_px(px)
                assert eyes, 'sem olhos e sem máscara deitada: %s' % name
                ex = sum(p[0] for p in eyes) / len(eyes)
                ey = sum(p[1] for p in eyes) / len(eyes)
                if cfg['zona'] == 'torso':
                    mask = mascara_torso_em_pe(px, ex, ey)
                elif cfg['zona'] == 'cabeca':
                    if cfg.get('tampa_rosto'):
                        mask = mascara_cabeca_fechada_em_pe(px)
                    else:
                        mask = mascara_cabeca_em_pe(px, ex, ey)
                else:
                    mask = mascara_pernas_em_pe(px, ey)
            painted = [(x, y) for y, xs in mask.items() for x in xs]
            for (x, y) in painted:
                assert px[x, y][3] >= 40 and alvo_valido(px, x, y, cfg['zona']), \
                    'pixel-alvo inválido %s em %s' % ((x, y), name)
            guarda_rosto(name, px, painted, cfg['zona'], cfg.get('tampa_rosto', False))
            if cfg['estilo'] == 'ferro':
                im = pinta_ferro(base, mask)
            else:
                im = pinta_avaritia(base, mask, cfg['zona'], deitado)
            if cfg.get('tampa_rosto'):
                # capacete fechado: visor teal nos olhos + boca coberta
                ipx = im.load()
                for (x, y) in olhos_px(px):
                    ipx[x, y] = A_T
                for (x, y) in boca_px(px):
                    ipx[x, y] = R_K
                restaura_orelhas(im, px)   # passo 2: orelhas consertadas
            anim = '_'.join(name.split('_')[1:-1]); idx = int(name.split('_')[-1])
            im.save(os.path.join(out, 'goblin_%s_%d.png' % (anim, idx)))
            ger += 1
        print('item %-20s icon + drop + %2d frames  (zona %-6s estilo %s)' %
              (cfg['id'], ger, cfg['zona'], cfg['estilo']))
    print('guarda de rosto: todos os frames verificados — nenhum pixel no rosto ✓')


if __name__ == '__main__':
    main()
