#!/usr/bin/env python3
"""
Animacoes do goblin v2.

Cada animacao e uma lista de poses geradas a partir do rig de
`goblin_rig.py`. A contagem de quadros e exatamente a que o jogo ja usa:

    idle 5 | walk 8 | attack 17 | hurt 17 | death 15   (62 no total)

Nenhum quadro e desenhado a mao: todos saem das mesmas partes, so mudando
deslocamento, troca de espada e, na morte, rotacao em torno dos pes.
"""

from PIL import Image

import goblin_rig as R

FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 24}

# Nenhuma parte pode andar mais que isto de um quadro para o outro. Era esse
# o defeito do ataque antigo: o braco saltava 6 px de uma vez e parecia que
# soltava do ombro e voltava. `_interp` abaixo garante o limite.
MAX_STEP = 2


def _interp(keys, n):
    """Interpola linearmente entre quadros-chave {indice: (valores...)}.

    Trabalhar com quadros-chave em vez de tabela escrita a mao e o que
    mantem o movimento continuo: entre duas chaves o deslocamento e sempre
    dividido pelo numero de quadros, entao nunca aparece um salto.
    """
    marcos = sorted(keys)
    out = []
    for i in range(n):
        a = max(m for m in marcos if m <= i)
        b = min((m for m in marcos if m >= i), default=a)
        if a == b:
            out.append(tuple(keys[a]))
            continue
        t = (i - a) / (b - a)
        out.append(tuple(round(va + (vb - va) * t)
                         for va, vb in zip(keys[a], keys[b])))
    return out
ACTIONS = ('idle', 'walk', 'attack', 'hurt', 'death')


def _pose(body=(0, 0), head=(0, 0), arm_l=(0, 0), arm_r=(0, 0),
          leg_l=(0, 0), leg_r=(0, 0), sword=None, kind='diag', squash=0):
    """Monta a pose somando o deslocamento global `body` a cada parte.

    `sword` nao e uma parte do corpo: e a ANCORA da mao que segura a arma.
    Por padrao ela acompanha o braco da arma — se cada animacao repetisse o
    valor na mao, bastaria esquecer de atualizar um deles para a arma
    equipada flutuar longe do punho (ja aconteceu na animacao de morte).
    """
    if sword is None:
        sword = arm_l
    bx, by = body
    # Na referencia a adaga esta na mao DIREITA (lado direito do espectador),
    # entao `arm_l` das tabelas de animacao e o braco da arma -> parte arm_r.
    return {
        'head':  (head[0] + bx, head[1] + by),
        'torso': (bx, by),
        'arm_r': (arm_l[0] + bx, arm_l[1] + by),
        'arm_l': (arm_r[0] + bx, arm_r[1] + by),
        'leg_l': (leg_l[0] + bx, leg_l[1] + by),
        'leg_r': (leg_r[0] + bx, leg_r[1] + by),
        'sword': (sword[0] + bx, sword[1] + by),
        '_sword': kind,
        # quanto o tronco comprime neste quadro (agachar); ver
        # goblin_rig.squash_rows
        '_squash': {'torso': squash} if squash else None,
    }


# --------------------------------------------------------------- idle ------
# Respiracao: o corpo inteiro afunda 1px e volta; as pernas ficam plantadas.
IDLE_BOB = [0, 0, 2, 2, 0]


def idle_poses():
    out = []
    for i in range(5):
        b = IDLE_BOB[i]
        out.append(_pose(head=(0, b), arm_l=(0, b), arm_r=(0, b),
                         body=(0, 0)))
        out[-1]['torso'] = (0, b)
    return out


# --------------------------------------------------------------- walk ------
# Ciclo de 8 quadros: pernas em contratempo, tronco sobe no meio do passo,
# bracos balancando ao contrario das pernas.
WALK_LX = [0, 0, 0, 0, 0, 0, 0, 0]
WALK_LY = [0, -2, -3, -2, 0, 0, 0, 0]
WALK_RX = [0, 0, 0, 0, 0, 0, 0, 0]
WALK_RY = [0, 0, 0, 0, 0, -2, -3, -2]
WALK_BOB = [0, -2, -2, 0, 0, -2, -2, 0]
WALK_SWAY = [0, 0, 2, 0, 0, 0, -2, 0]


def walk_poses():
    out = []
    for i in range(8):
        bob = WALK_BOB[i]
        out.append(_pose(
            body=(0, bob),
            head=(WALK_SWAY[i], 0),
            # Balanco limitado: o ombro precisa continuar encostado no tronco.
            arm_l=(0, min(2, -WALK_RY[i])),
            arm_r=(0, min(2, -WALK_LY[i])),
            leg_l=(WALK_LX[i], WALK_LY[i] - bob),
            leg_r=(WALK_RX[i], WALK_RY[i] - bob),
        ))
    return out


# ------------------------------------------------------------- attack ------
# Quadros-chave: recuo e guarda alta -> corte -> estocada -> volta.
# O braco NUNCA se afasta mais que 2 px do tronco, senao o ombro descola da
# silhueta e a animacao parece quebrada.
ATTACK_KEYS = {
    #   corpo dx, corpo dy, braco dx, braco dy
    0:  (0, 0, 0, 0),
    3:  (-2, 0, 0, -2),
    5:  (-2, 0, 1, -2),
    7:  (0, 0, 2, -1),
    9:  (3, -1, 2, 0),
    11: (4, 0, 2, 1),
    13: (2, 0, 1, 1),
    16: (0, 0, 0, 0),
}
# Orientacao da arma em cada quadro (a arma e equipamento; isto so diz ao
# equipamento qual das quatro vistas usar).
ATTACK_KIND = (['diag'] * 2 + ['up'] * 5 + ['diag'] * 2
               + ['fwd'] * 4 + ['diag'] * 4)


def attack_poses():
    out = []
    for i, (dx, dy, ax, ay) in enumerate(_interp(ATTACK_KEYS, 17)):
        out.append(_pose(
            body=(dx, dy),
            head=(0, 0),
            arm_l=(ax, ay),
            arm_r=(-round(dx / 3), 0),
            leg_l=(-dx, 0),
            leg_r=(-dx, 0),
            kind=ATTACK_KIND[i],
        ))
    return out


# --------------------------------------------------------------- hurt ------
# Impacto: recuo forte, cabeca jogada para tras e tremor amortecido.
HURT_DX = [0, -2, -3, -4, -4, -3, -2, -1, 0, -1, 0, 1, 1, 0, 0, 0, 0]
HURT_HEAD = [0, 0, 0, -1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
HURT_DY = [0, -1, -2, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
HURT_FLASH = {1, 2, 3, 6, 7}


def hurt_poses():
    out = []
    for i in range(17):
        p = _pose(
            body=(HURT_DX[i], HURT_DY[i]),
            head=(HURT_HEAD[i], 0),
            arm_l=(-1 if i < 6 else 0, 0),
            arm_r=(1 if i < 6 else 0, 0),
            leg_l=(-HURT_DX[i], 0),
            leg_r=(-HURT_DX[i], 0),
        )
        p['_flash'] = i in HURT_FLASH
        out.append(p)
    return out


# -------------------------------------------------------------- death ------
# Antes a morte tinha 15 quadros e, no quadro 7, o goblin simplesmente
# APARECIA deitado — teleportava para o chao. Agora sao 24 quadros e a
# queda acontece:
#
#   0-2    cambaleia, perde o equilibrio
#   3-8    os joelhos cedem: o corpo afunda 11 px, a cabeca pende
#   9-11   de joelhos, o tronco tomba para a frente
#   12     perde o contato com o chao (quadro de queda, corpo no ar)
#   13-14  bate no chao e quica uma vez
#   15-18  acomoda: os membros se ABREM, como na referencia
#   19-23  imovel, sumindo
#
# LIMITE HONESTO: pixel art nao aceita rotacao em angulo qualquer — girar
# 45 graus reamostra e destroi o desenho. O corpo deitado usa rotacao de
# exatos 90 graus (sem perder um pixel) e o esparramado da referencia e
# reproduzido ABRINDO os membros: cada parte ganha um deslocamento antes da
# rotacao, entao no chao o goblin fica com a cabeca num extremo, os bracos
# abertos (um para cima, outro para baixo) e as pernas afastadas.
DEATH_FRAMES = 24

# --- como a morte foi montada ---------------------------------------------
# O defeito antigo era duplo: o goblin "afundava" dentro das proprias botas
# (o tronco descia por cima das pernas, sem nada dobrar) e depois trocava
# de pose de uma vez para o corpo deitado. Agora sao tres tempos:
#
#   0-6    AGACHA   as coxas comprimem de verdade (squash_rows), o quadril
#                   continua no chao e o ombro desce junto com a cabeca.
#   7-9    DESABA   o joelho larga: as pernas voltam a esticar enquanto o
#                   corpo despenca para a frente. E o contrario do
#                   agachamento, e e o que liga o agachar ao tombo.
#   10-12  TOMBA    entra o DESENHO do corpo caido, girado para tras, e ele
#                   vai se assentando no chao.
#   13-23  CAIDO    bate, quica uma vez e desaparece.

# Do quadro 10 em diante o quadro nao e mais o corpo de pe: e o desenho do
# corpo caido (R.LAY). Quem TOMBA e esse desenho — ele entra girado para
# tras e vai se assentando no chao. Girar o corpo caido (e nao trocar de
# pose de uma vez) e o que faz a queda terminar exatamente na pose da
# imagem de referencia sem nenhum corte seco.
DEATH_LYING = 10
DEATH_LAY_TURN = [-40, -26, -13] + [0] * 11     # a partir do quadro 10
LAY_PIVOT_CAIDO = (30, 50)                      # quadril, onde ele pivota
DEATH_TOPPLE = DEATH_LYING    # o quadro em que ele deixa de estar de pe

# Compressao do tronco quadro a quadro: o joelho dobra ate o 6 e larga do
# 7 ao 9 — e nesses tres quadros, com o corpo ja despencando para a
# frente, que ele deixa de estar de pe.
DEATH_SQUASH = [0, 0, 2, 4, 6, 7, 7, 5, 2, 0] + [0] * 14

# Inclinacao para a frente e afundamento do corpo durante o agachamento.
DEATH_FALL = [0, 0, 0, 1, 2, 2, 3, 4, 5, 6] + [0] * 14
DEATH_DROP = [0, 0, 0, 1, 1, 2, 2, 2, 1, 0] + [0] * 14

DEATH_ALPHA = ([255] * 19) + [226, 196, 162, 124, 86]


# Assentamento do corpo caido: bate, quica uma vez e para. Sao os unicos
# deslocamentos depois da queda — um corpo morto nao se mexe mais.
DEATH_SETTLE = {13: (0, -3), 14: (0, -1), 15: (0, 0)}


def _settle(i):
    for k in sorted(DEATH_SETTLE, reverse=True):
        if i >= k:
            return DEATH_SETTLE[k]
    return (0, 0)


def death_poses():
    out = []
    for i in range(DEATH_FRAMES):
        dobra = DEATH_SQUASH[i]
        if i < DEATH_LYING:
            # De pe (ou tombando): o que o quadro desenha e sempre o goblin
            # agachado. Quem deita o corpo e a rotacao, depois.
            # alem de dobrar o joelho ele desaba para a frente: a cabeca
            # cai um pouco mais que o ombro e os bracos ficam soltos
            cai = DEATH_FALL[i]
            # o braco acompanha o tronco, mas nunca mais que 3 px: passando
            # disso ele descola do ombro e vira um pedaco solto no ar.
            solto = min(3, cai)
            p = _pose(
                body=(0, DEATH_DROP[i]),
                head=(cai, dobra + min(2, cai)),
                arm_l=(solto, dobra),         # bracos pendurados
                arm_r=(-solto, dobra),
                leg_l=(0, -DEATH_DROP[i]),    # as botas ficam plantadas
                leg_r=(0, -DEATH_DROP[i]),
                squash=dobra,
            )
        else:
            # Caido: o desenho proprio do corpo no chao.
            p = {k: None for k in R.DRAW_ORDER}
            p['_lay'] = _settle(i)
            p['_lay_turn'] = DEATH_LAY_TURN[i - DEATH_LYING]
            # a mao continua sendo uma ancora: a arma equipada cai junto
            p['sword'] = (0, 0)
            p['_sword'] = 'fwd'
        # o goblin fecha os olhos ja no meio do agachamento
        p['_eyes_shut'] = i >= 5
        p['_dead'] = i
        out.append(p)
    return out


POSES = {
    'idle': idle_poses,
    'walk': walk_poses,
    'attack': attack_poses,
    'hurt': hurt_poses,
    'death': death_poses,
}


# ---------------------------------------------------------- pos-processo ----
# Girar pixel art num angulo quebrado estraga o desenho: o contorno de 1 px
# vira pontilhado e abrem-se buracos no meio do corpo. Por isso o giro vem
# sempre acompanhado de `_mend`, que remonta a silhueta depois da rotacao.
# E so com ele que a diagonal da referencia fica possivel — em 90 graus
# exatos o corpo ficava deitado na horizontal, que nao e a imagem pedida.

_PAD = 80


def _mend(img):
    """Reconstroi a silhueta depois de uma rotacao em angulo quebrado.

    1. tapa os buracos abertos pelo giro, com a cor de um vizinho;
    2. apaga os pixels soltos que ficaram pendurados na borda;
    3. redesenha o contorno, que a rotacao tinha deixado pontilhado.
    """
    import numpy as np

    a = np.array(img).astype(int)
    m = a[:, :, 3] > 0
    h, w = m.shape
    k = R.C['k'][:3]

    def vizinhos(mask):
        p = np.zeros((h + 2, w + 2), bool)
        p[1:-1, 1:-1] = mask
        return (p[:-2, 1:-1].astype(int) + p[2:, 1:-1]
                + p[1:-1, :-2] + p[1:-1, 2:])

    for _ in range(2):
        buraco = (~m) & (vizinhos(m) >= 3)
        for y, x in zip(*np.nonzero(buraco)):
            perto = [a[y + dy, x + dx] for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if 0 <= y + dy < h and 0 <= x + dx < w and m[y + dy, x + dx]]
            cheio = [c for c in perto if tuple(c[:3]) != k] or perto
            a[y, x] = cheio[0]
        m |= buraco
        solto = m & (vizinhos(m) <= 1)
        a[solto] = 0
        m &= ~solto

    borda = m & (vizinhos(m) < 4)
    a[borda, :3] = k
    a[borda, 3] = 255
    return Image.fromarray(a.astype(np.uint8))


def _tombar(img, ang):
    """Gira o corpo CAIDO de volta para tras, em torno do quadril.

    E assim que a queda e desenhada: nos ultimos quadros de pe o corpo vem
    inclinado e vai assentando. Como o giro e do desenho que ja esta na
    pose final, o movimento termina exatamente nela.
    """
    if not ang:
        return img
    px, py = LAY_PIVOT_CAIDO
    big = Image.new('RGBA', (_PAD * 2, _PAD * 2), (0, 0, 0, 0))
    big.paste(img, (_PAD - px, _PAD - py))
    big = _mend(big.rotate(-ang, resample=Image.NEAREST, center=(_PAD, _PAD)))
    return big.crop((_PAD - px, _PAD - py, _PAD - px + R.SIZE,
                     _PAD - py + R.SIZE))


def _fade(img, alpha):
    if alpha >= 255:
        return img
    a = img.getchannel('A').point(lambda v: v * alpha // 255)
    img = img.copy()
    img.putalpha(a)
    return img


def _flash(buf):
    """Clareia a pele no quadro de impacto (dano visivel)."""
    hit = {'e': 'd', 'd': 'j', 'j': 'g', 'g': 'l', 'l': 'f',
           'B': 'b', 'b': 'h'}
    for y in range(R.SIZE):
        for x in range(R.SIZE):
            c = buf[y][x]
            if c in hit:
                buf[y][x] = hit[c]


def post(img, pose):
    """Pos-processo da morte (giro + desvanecer). O gerador de equipamento
    usa exatamente esta funcao, senao o overlay sai de um quadro e o corpo
    de outro."""
    k = pose.get('_dead')
    if k is None:
        return img
    if pose.get('_lay') is not None:
        img = _tombar(img, pose['_lay_turn'])
    return _fade(img, DEATH_ALPHA[k])


def render_action(action, variation=None):
    """Retorna a lista de Images de uma animacao, ja com a variacao aplicada."""
    frames = []
    swap = variation.get('swap') if variation else None
    parts = variation.get('parts') if variation else None
    detail = variation.get('detail') if variation else None
    for i, pose in enumerate(POSES[action]()):
        buf = R.compose(pose, variation=detail, swap=swap, extra_parts=parts)
        if pose.get('_flash'):
            _flash(buf)
        frames.append(post(R.to_image(buf), pose))
    assert len(frames) == FRAME_COUNTS[action], (action, len(frames))
    return frames


def render_all(variation=None):
    return {a: render_action(a, variation) for a in ACTIONS}


if __name__ == '__main__':
    import os
    os.makedirs('/tmp/prev', exist_ok=True)
    all_frames = render_all()
    rows = [all_frames[a] for a in ACTIONS]
    w = max(len(r) for r in rows)
    sheet = Image.new('RGBA', (32 * w, 32 * len(rows)), (26, 26, 30, 255))
    for j, r in enumerate(rows):
        for i, im in enumerate(r):
            sheet.alpha_composite(im, (i * 32, j * 32))
    sheet.resize((sheet.width * 5, sheet.height * 5), Image.NEAREST).save('/tmp/prev/anim.png')
    print('ok')
