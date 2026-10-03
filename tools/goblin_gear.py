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
R.C.update({
    'N': (72, 72, 80, 255),      # pedra sombra
    'O': (118, 118, 126, 255),   # pedra base
    'T': (170, 170, 178, 255),   # pedra luz
})

MATERIALS = {
    'avaritia': {'D': '1', 'M': '2', 'L': '3', 'G': '4', 'A': '6'},
    'ferro':    {'D': '7', 'M': '8', 'L': '9', 'G': '9', 'A': '6'},
    'madeira':  {'D': 'B', 'M': 'L', 'L': 'M', 'G': '6', 'A': '6'},
    'pedra':    {'D': 'N', 'M': 'O', 'L': 'T', 'G': 'T', 'A': '6'},
}


def paint(rows, material):
    m = MATERIALS[material]
    return [[m.get(ch, ch) for ch in row] for row in rows]


def g(rows, w):
    for r in rows:
        assert len(r) == w, (len(r), r)
    return [list(r) for r in rows]


# ------------------------------------------------------------- desenhos ----
# As placas NAO sao desenhadas a mao. Elas sao MOLDADAS sobre a silhueta da
# parte do corpo que vestem: o molde le o recorte do goblin, escolhe quais
# pixels a peca cobre e devolve a chapa ja com borda, volume e gemas.
#
# Vantagem: o encaixe e exato por construcao. Nao sobra pele por baixo da
# armadura nem a placa invade uma area que precisa ficar livre — maos,
# antebracos, orelhas e queixo saem de regras, nao de tentativa e erro.


def _mold(part, keep, gems=(), slits=(), flat=False, marks=()):
    """Molda uma chapa sobre `part`, cobrindo os pixels onde keep(x, y).

    borda -> L (aco claro) · miolo -> D (escuro) · bisel sob a borda -> M
    `gems` recebem G (turquesa) e `slits` viram visor, tambem em G.
    `flat` serve para pecas finas (bracos, pernas), onde um miolo escuro
    deixaria a peca quase invisivel: a chapa fica em M com luz em cima.
    """
    h, w = len(part), len(part[0])
    dentro = [[part[y][x] != '.' and keep(x, y) for x in range(w)]
              for y in range(h)]
    # Fecha buracos: a chapa e solida de ponta a ponta em cada linha, senao
    # um vao do desenho vira um pixel de borda solto no meio da armadura.
    for linha in dentro:
        if True in linha:
            for x in range(linha.index(True), len(linha) - linha[::-1].index(True)):
                linha[x] = True

    def eh(x, y):
        return 0 <= x < w and 0 <= y < h and dentro[y][x]

    out = [['.'] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not dentro[y][x]:
                continue
            borda = not all(eh(x + dx, y + dy)
                            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
            if flat:
                out[y][x] = 'L' if (borda and not eh(x, y - 1)) else 'M'
            else:
                out[y][x] = 'L' if borda else 'D'
    if not flat:                      # bisel: uma linha clara sob a borda
        for y in range(1, h):
            for x in range(w):
                if out[y][x] == 'D' and out[y - 1][x] == 'L':
                    out[y][x] = 'M'
    # Gemas e visor so entram no miolo: pintar por cima da borda abriria um
    # rombo no contorno da peca.
    for x, y, ch in list(marks) + [(x, y, 'G') for x, y in
                                   list(gems) + list(slits)]:
        if 0 <= y < h and 0 <= x < w and out[y][x] in ('D', 'M'):
            out[y][x] = ch
    return out


# --- CAPACETE -------------------------------------------------------------
# Cobre o rosto inteiro. Fica de fora so o que o usuario pediu: as duas
# orelhas e o focinho/queixo. Os limites laterais sao as colunas escuras que
# o proprio desenho usa para separar cranio e orelha.
HELM_TOP, HELM_BOTTOM = 2, 16
HELM_LEFT = {2: 12, 3: 12, 4: 12, 5: 12, 6: 11, 7: 12, 8: 6, 9: 6,
             10: 7, 11: 7, 12: 7, 13: 7, 14: 9, 15: 9, 16: 9}
HELM_RIGHT = {2: 23, 3: 23, 4: 24, 5: 24, 6: 25, 7: 27, 8: 27, 9: 27}


def _keep_head(x, y):
    if not (HELM_TOP <= y <= HELM_BOTTOM):
        return False
    return HELM_LEFT[y] <= x < HELM_RIGHT.get(y, len(R.HEAD[0]))


# O visor nasce dos olhos do goblin: as mesmas celulas que o rig usa para
# olho e pupila, entao a fresta cai exatamente sobre o olhar dele.
VISOR = [c for k in ('eye_l', 'pupil_l', 'eye_r', 'pupil_r')
         for c in R.FACE_CELLS[k]]

# Nasal e sobrancelha dao volume ao elmo: sem eles a chapa vira um balde.
NASAL = ([(x, y, 'M') for y in range(11, 16) for x in (21, 22, 23)]
         + [(22, y, 'L') for y in range(11, 16)])
SOBRANCELHA = ([(x, 11, 'L') for x in range(14, 20)]
               + [(x, 11, 'L') for x in range(24, 29)])

# Rebites na face: quebram a chapa lisa sem mudar o recorte da peca.
REBITES_ELMO = [(10, 11), (10, 13), (10, 15), (29, 12), (29, 14)]

HELM = _mold(R.HEAD, _keep_head, slits=VISOR,
             marks=NASAL + SOBRANCELHA + [(x, y, 'L') for x, y in REBITES_ELMO])

# --- PEITORAL -------------------------------------------------------------
# Todo o torax (linhas 0..10 do tronco, ate a altura do cinto). Os bracos
# sao partes separadas no rig, entao maos e antebracos ficam livres sozinhos.
# Gema central mais as duas dos ombros, como no icone do inventario.
CHEST = _mold(
    R.TORSO, lambda x, y: y <= 10,
    gems=[(12, 5), (13, 5), (12, 6), (13, 6), (6, 1), (20, 1)],
    # esterno, gola e rebites: a chapa lisa parecia uma placa de papelao
    marks=[(x, y, 'L') for y in (3, 4, 7, 8) for x in (12, 13)]
          + [(x, 2, 'M') for x in range(7, 21)]
          + [(x, y, 'L') for y in (4, 7) for x in (9, 16)]
          + [(8, 9, 'L'), (17, 9, 'L'), (12, 9, 'L'), (13, 9, 'L')])

# Ombreiras: so o alto do braco. O antebraco e a mao comecam logo abaixo.
PAULDRON_L = _mold(R.ARM_L, lambda x, y: y <= 4 and x >= 4, flat=True)
PAULDRON_R = _mold(R.ARM_R, lambda x, y: y <= 4 and x <= 4, flat=True)

# --- CALCA ----------------------------------------------------------------
# Quadril inteiro (o resto do tronco, da linha do cinto para baixo) mais as
# duas pernas completas, botas inclusive.
# Cinto na linha de cima e costura no meio das pernas.
HIP = _mold(R.TORSO, lambda x, y: y >= 11, gems=[(7, 13), (18, 13)],
            marks=[(x, 12, 'L') for x in range(3, 22)]
                  + [(x, 13, 'M') for x in range(3, 22)]
                  + [(13, y, 'L') for y in range(16, 20)]
                  + [(5, 15, 'L'), (20, 15, 'L')])
GREAVE_L = _mold(R.LEG_L, lambda x, y: True, flat=True)
GREAVE_R = _mold(R.LEG_R, lambda x, y: True, flat=True)

# Escudo redondo. Antes ele tinha 10x11 e sumia atras do braco; agora
# cobre o antebraco inteiro e sobra para fora, que e o que faz um escudo
# parecer escudo. O desenho e construido, nao escrito a mao, para o circulo
# sair redondo em qualquer tamanho:
#   aro escuro em volta -> tabuas verticais (as colunas em L sao as juntas)
#   -> umbo de metal no centro.
SHIELD_W, SHIELD_H = 15, 17


def _round_shield(w, h):
    cx, cy = (w - 1) / 2, (h - 1) / 2
    out = [['.'] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            d = ((x - cx) / (w / 2)) ** 2 + ((y - cy) / (h / 2)) ** 2
            if d > 1.0:
                continue
            if d > 0.66:                       # aro
                out[y][x] = 'D'
            elif d > 0.52:                     # bisel por dentro do aro
                out[y][x] = 'M'
            else:                              # tabuas
                out[y][x] = 'L' if (x - int(cx)) % 3 == 0 else 'M'
    # umbo: chapa de metal no meio, com brilho
    for y in range(h):
        for x in range(w):
            dx, dy = abs(x - cx), abs(y - cy)
            if dx <= 2.2 and dy <= 2.2 and dx + dy <= 3.4:
                out[y][x] = 'G'
    out[int(cy)][int(cx)] = 'A'
    out[int(cy)][int(cx) + 1] = 'A'
    return out


SHIELD = _round_shield(SHIELD_W, SHIELD_H)

# ------------------------------------------------------------------ armas --
# O goblin nasce DESARMADO: a adaga deixou de fazer parte do corpo e virou
# equipamento. Com isso a arma nao precisa mais cobrir pixel a pixel uma
# adaga ja desenhada, entao cada arma pode ter o tamanho e o formato dela.
#
# De cada arma so sao desenhadas DUAS vistas, a vertical ("down") e a
# diagonal. As outras duas saem por transformacao exata:
#   up  = "down" espelhado na vertical     (ponta para cima)
#   fwd = "down" girado 90 graus           (ponta para frente)
# Rotacao de 90 graus nao perde nenhum pixel, diferente de um angulo
# qualquer, que borra arte em pixel art.
#
# O cabo e sempre couro (B/b/h passam direto pela paleta); so a lamina ou a
# cabeca da arma usam as cores do material.


def _flip_v(grid):
    return [list(r) for r in reversed(grid)]


def _rot_ccw(grid):
    """Gira 90 graus no sentido anti-horario. Exato, sem reamostragem."""
    h, w = len(grid), len(grid[0])
    return [[grid[y][w - 1 - x] for y in range(h)] for x in range(w)]


def _views(down, diag):
    """Monta as 4 vistas e o deslocamento de cada uma.

    Os deslocamentos sao calculados para que o CABO caia sempre na mesma
    posicao da mao, qualquer que seja o comprimento da arma — por isso dao
    para desenhar uma adaga curta e uma espada longa na mesma montagem.
    """
    hd, wd = len(down), len(down[0])
    hg = len(diag)
    return {
        # cabo nas linhas 1-2 da grade -> deslocamento fixo
        'down': (down, -1, 0),
        # espelhado: o cabo vai para as linhas h-3/h-2, entao sobe a grade
        'up': (_flip_v(down), -1, 12 - hd),
        # girado: a grade fica deitada, cabo a esquerda
        'fwd': (_rot_ccw(down), 0, -(wd // 2) + 2),
        # diagonal: cabo no canto de baixo, lamina subindo para a direita
        'diag': (diag, 0, 9 - hg),
    }


# cabo de couro comum a todas as armas: B contorno, b couro, h brilho
ADAGA_DOWN = g([
    "..BB..",
    ".BbhB.",
    ".BbhB.",
    "DLLLLD",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    "..DLD.",
    "..DD..",
    "......",
], 6)

ADAGA_DIAG = g([
    "........DD",
    ".......DLD",
    "......DLMD",
    ".....DLMD.",
    "....DLMD..",
    "...DLMD...",
    "..LLLD....",
    ".BbhB.....",
    ".BBB......",
], 10)

ESPADA_DOWN = g([
    "..BB..",
    ".BbhB.",
    ".BbhB.",
    "DLLLLD",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    ".DMLD.",
    "..DLD.",
    "..DD..",
    "......",
], 6)

ESPADA_DIAG = g([
    "...........DD",
    "..........DLD",
    ".........DLMD",
    "........DLMD.",
    ".......DLMD..",
    "......DLMD...",
    ".....DLMD....",
    "....DLMD.....",
    "...DLMD......",
    "..LLLD.......",
    ".BbhB........",
    ".BBB.........",
], 13)

CLAVA_DOWN = g([
    "..BB..",
    ".BbhB.",
    ".BbhB.",
    ".DMMD.",
    ".DMMD.",
    "DMLLMD",
    "DMLLMD",
    "DMLLMD",
    "DMLLMD",
    "DMLLMD",
    ".DMMD.",
    "..DD..",
    "......",
    "......",
], 6)

CLAVA_DIAG = g([
    "......DDD..",
    ".....DMLLD.",
    "....DMLLMD.",
    "....DMLLD..",
    "...DMMLD...",
    "...DMMD....",
    "..DMMD.....",
    ".BbhB......",
    ".BbD.......",
    ".BB........",
], 11)

ADAGA = _views(ADAGA_DOWN, ADAGA_DIAG)
ESPADA = _views(ESPADA_DOWN, ESPADA_DIAG)
CLAVA = _views(CLAVA_DOWN, CLAVA_DIAG)

# ---- armas: reskin da propria adaga do rig ----
# Em vez de desenhar cada orientacao a mao (e arriscar deixar um pixel da
# adaga original aparecendo por baixo, ja que overlay so ADICIONA), as armas
# sao geradas a partir da silhueta do proprio rig, trocando cor por cor.
# Cobertura 100% por construcao, em qualquer orientacao.
SWORD_REMAP = {'k': 'D', 'B': 'D', 'b': 'G', 'h': 'G',
               'z': 'M', 'q': 'L', 'f': 'L'}
CLUB_REMAP = {'k': 'D', 'B': 'D', 'b': 'M', 'h': 'M',
              'z': 'M', 'q': 'L', 'f': 'L'}


def _reskin(remap):
    """Monta {orientacao: (grade, dx, dy)} a partir de R.SWORDS."""
    out = {}
    for kind, rows in R.SWORDS.items():
        out[kind] = ([[remap.get(ch, ch) if ch != '.' else '.' for ch in row]
                      for row in rows], 0, 0)
    return out


SWORD_SKIN = _reskin(SWORD_REMAP)
CLUB_SKIN = _reskin(CLUB_REMAP)


# ------------------------------------------- armadura sobre o corpo caido --
# O corpo caido e um desenho inteiro, nao as partes remontadas (ver
# goblin_rig.LAY), entao a armadura dele tambem e moldada sobre o desenho
# inteiro: uma chapa de 64x64 por peca, no lugar exato que a peca cobre.
# As regioes nao sao escritas pixel a pixel — sao LIDAS do desenho:
#   calca e botas  = as tres manchas de couro (a maior e o avental)
#   elmo           = o disco do cranio
#   peitoral       = o que sobra entre o cranio e o avental
#   ombreiras      = a raiz de cada braco
# Assim, se o desenho do corpo caido mudar, a armadura o acompanha.
from collections import deque as _deque                       # noqa: E402

_COURO = ('B', 'b', 'h')


def _manchas(pred):
    """Separa em manchas ligadas os pixels do corpo caido que casam `pred`."""
    n = R.SIZE
    dentro = [[R.LAY[y][x] != '.' and pred(R.LAY[y][x]) for x in range(n)]
              for y in range(n)]
    visto = [[False] * n for _ in range(n)]
    out = []
    for y in range(n):
        for x in range(n):
            if dentro[y][x] and not visto[y][x]:
                fila, visto[y][x], px = _deque([(x, y)]), True, []
                while fila:
                    cx, cy = fila.popleft()
                    px.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if (0 <= nx < n and 0 <= ny < n and dentro[ny][nx]
                                and not visto[ny][nx]):
                            visto[ny][nx] = True
                            fila.append((nx, ny))
                out.append(set(px))
    return sorted(out, key=len, reverse=True)


def _disco(cx, cy, r):
    return {(x, y) for y in range(R.SIZE) for x in range(R.SIZE)
            if R.LAY[y][x] != '.' and (x - cx) ** 2 + (y - cy) ** 2 <= r * r}


_couro = _manchas(lambda c: c in _COURO)

# O macacao e uma mancha so no corpo caido (costas + calca). O corte em
# dois sai da propria altura: deitado de bruços na diagonal, o que esta
# acima da linha da cintura e o dorso, o que esta abaixo e a calca.
LAY_MACACAO = _couro[0]
LAY_CINTURA = 40
LAY_DORSO = {p for p in LAY_MACACAO if p[1] < LAY_CINTURA}
LAY_CALCA = {p for p in LAY_MACACAO if p[1] >= LAY_CINTURA}
LAY_BOTAS = sorted(_couro[1:3], key=lambda s: min(p[0] for p in s))

LAY_CRANIO = _disco(40, 24, 9) - LAY_MACACAO
LAY_PEITO = (LAY_DORSO | _disco(33, 31, 5)) - LAY_CRANIO - LAY_CALCA
LAY_OMBRO_A = _disco(29, 28, 5) - LAY_MACACAO - LAY_CRANIO - LAY_PEITO
LAY_OMBRO_B = _disco(44, 32, 5) - LAY_MACACAO - LAY_CRANIO - LAY_PEITO

# Deitado de bruços nao ha rosto a mostra, entao o elmo nao tem visor —
# o que aparece dele e so a calota, inteira.
LAY_VISOR = []


def _mold_lay(regiao, **kw):
    return _mold(R.LAY, lambda x, y: (x, y) in regiao, **kw)


HELM_LAY = _mold_lay(LAY_CRANIO, slits=LAY_VISOR,
                     marks=[(38, 19, 'L'), (45, 23, 'L'), (36, 28, 'L')])
CHEST_LAY = _mold_lay(LAY_PEITO, gems=[(30, 33), (31, 33), (30, 34), (31, 34)],
                      marks=[(27, 30, 'L'), (34, 37, 'L')])
HIP_LAY = _mold_lay(LAY_CALCA, gems=[(24, 44), (30, 50)],
                    marks=[(x, 41, 'L') for x in range(18, 36)]
                          + [(x, 42, 'M') for x in range(18, 36)])
GREAVE_LAY_A = _mold_lay(LAY_BOTAS[0], flat=True)
GREAVE_LAY_B = _mold_lay(LAY_BOTAS[1], flat=True)
PAULDRON_LAY_A = _mold_lay(LAY_OMBRO_A, flat=True)
PAULDRON_LAY_B = _mold_lay(LAY_OMBRO_B, flat=True)

# O escudo cai ao lado do corpo, encostado na mao do braco aberto
# para a esquerda — solto no chao ele seria reprovado como peca descolada.
SHIELD_LAY_POS = (9, 15)


def _lay(rows, material, dx=0, dy=0):
    return {'anchor': 'lay', 'grid': paint(rows, material), 'dx': dx, 'dy': dy}


def _layer(anchor, rows, material, dx=0, dy=0):
    return {'anchor': anchor, 'grid': paint(rows, material), 'dx': dx, 'dy': dy}


# Cada peca declara a versao de PE e, em `lay`, a versao do corpo caido.
# Sem isso a armadura sumia no quadro em que o goblin morre.
def helm(material):
    return [dict(_layer('head', HELM, material),
                 lay=_lay(HELM_LAY, material))]


def chest(material):
    return [
        dict(_layer('torso', CHEST, material), lay=_lay(CHEST_LAY, material)),
        dict(_layer('arm_l', PAULDRON_L, material),
             lay=_lay(PAULDRON_LAY_A, material)),
        dict(_layer('arm_r', PAULDRON_R, material),
             lay=_lay(PAULDRON_LAY_B, material)),
    ]


def pants(material):
    return [
        dict(_layer('torso', HIP, material), lay=_lay(HIP_LAY, material)),
        dict(_layer('leg_l', GREAVE_L, material),
             lay=_lay(GREAVE_LAY_A, material)),
        dict(_layer('leg_r', GREAVE_R, material),
             lay=_lay(GREAVE_LAY_B, material)),
    ]


def weapon(views, material):
    """Arma: uma vista por orientacao, escolhida pela pose do braco."""
    return [{'anchor': 'sword', 'material': material, 'by_kind': {
        k: (paint(rows, material), dx, dy) for k, (rows, dx, dy) in views.items()
    }}]


def shield(material):
    # Escudo no braco LIVRE (a adaga esta na mao direita, como na referencia).
    return [dict(_layer('arm_l', SHIELD, material,
                        dx=(len(R.ARM_L[0]) - SHIELD_W) // 2,
                        dy=(len(R.ARM_L) - SHIELD_H) // 2 + 1),
                 lay=_lay(SHIELD, material, *SHIELD_LAY_POS))]


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
    'wpn_adaga_pedra':   (weapon(ADAGA, 'pedra'), None),
    'wpn_adaga_metal':   (weapon(ADAGA, 'ferro'), None),
    'wpn_adaga_madeira': (weapon(ADAGA, 'madeira'), None),
    'wpn_espada': (weapon(ESPADA, 'ferro'), None),
    'wpn_clava':  (weapon(CLAVA, 'madeira'), None),
    'wpn_escudo': (shield('madeira'), None),
}

# Icones 16x16 do inventario: recorte da parte do corpo que a peca cobre.
ICONS = {
    'av_cap_icon': 'av_cap',
    'av_pei_icon': 'av_pei',
    'av_cal_icon': 'av_cal',
}


def resolve(layers, kind, lay=False):
    """Troca as camadas 'by_kind' pela orientacao certa da arma.

    `lay=True` devolve a versao moldada sobre o corpo caido, quando a peca
    tem uma. A arma nao precisa: ela so muda de orientacao e a mao do corpo
    caido e mais uma ancora como qualquer outra.
    """
    out = []
    for layer in layers:
        if 'by_kind' in layer:
            if kind not in layer['by_kind']:
                continue
            rows, dx, dy = layer['by_kind'][kind]
            out.append({'anchor': 'sword', 'grid': rows, 'dx': dx, 'dy': dy})
        elif lay and layer.get('lay'):
            out.append(layer['lay'])
        else:
            out.append({k: v for k, v in layer.items() if k != 'lay'})
    return out
