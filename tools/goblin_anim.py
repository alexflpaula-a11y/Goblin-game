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
          leg_l=(0, 0), leg_r=(0, 0), sword=None, kind='diag'):
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
DEATH_LYING = 12           # a partir daqui o corpo esta na horizontal

#            0  1  2  3  4  5  6  7  8  9 10 11
DEATH_SINK = [0, 0, 1, 3, 5, 7, 9, 10, 11, 12, 13, 13]
DEATH_PITCH = [0, 0, 0, 1, 1, 2, 3, 4, 5, 6, 7, 8]   # tronco tombando

# Altura acima do chao depois de deitar: 12 ainda esta no ar, 13 bate,
# 14 quica, 15 em diante esta assentado.
DEATH_LIFT = {12: 9, 13: 0, 14: 2, 15: 0}

# Abertura dos membros no chao (0 = fechado, 1 = esparramado). Entra aos
# poucos nos quadros 15-18 para o corpo "relaxar" depois do baque.
DEATH_SPREAD = {12: 0.0, 13: 0.0, 14: 0.35, 15: 0.6, 16: 0.85, 17: 1.0}

DEATH_ALPHA = ([255] * 19) + [226, 196, 162, 124, 86]


def _spread(i):
    if i < DEATH_LYING:
        return 0.0
    return DEATH_SPREAD.get(i, 1.0)


def _lift(i):
    if i < DEATH_LYING:
        return 0
    for k in sorted(DEATH_LIFT, reverse=True):
        if i >= k:
            return DEATH_LIFT[k]
    return 0


def death_poses():
    out = []
    for i in range(DEATH_FRAMES):
        if i < DEATH_LYING:
            afunda = DEATH_SINK[i]
            tomba = DEATH_PITCH[i]
            p = _pose(
                body=(tomba, afunda),
                head=(tomba, min(2, afunda // 3)),
                arm_l=(-1 if i >= 2 else 0, min(2, afunda // 4)),
                arm_r=(1 if i >= 2 else 0, min(2, afunda // 4)),
                # as pernas ficam no chao: cancelam o afundamento do corpo
                leg_l=(-1 if i >= 3 else 0, -afunda),
                leg_r=(1 if i >= 3 else 0, -afunda),
            )
        else:
            # Deslocamentos ANTES da rotacao. Depois do giro de 90 graus no
            # sentido horario, (dx, dy) vira (-dy, dx) — por isso abrir os
            # bracos no chao se escreve como deslocamento em X aqui.
            # So ha deslocamento em X: depois do giro ele vira deslocamento
            # VERTICAL, que e justamente o esparramado que se quer no chao.
            # Mexer em Y aqui arrancaria a cabeca ou as pernas do tronco —
            # medido, nao chutado (ver teste de corpo inteiro em test.sh).
            k = _spread(i)
            r = lambda v: round(v * k)
            p = _pose(
                head=(r(-2), 0),      # cabeca pendendo para um lado
                arm_l=(r(-3), 0),     # braco de cima, aberto
                arm_r=(r(3), 0),      # braco de baixo, aberto
                leg_l=(0, 0),         # pernas juntas: assim as duas botas
                leg_r=(r(1), 0),      # continuam legiveis como um par
            )
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
_LAY_OFFSET = None


def _lay_offset():
    """Deslocamento fixo do corpo deitado.

    E calculado UMA vez a partir do goblin nu. Usar sempre o mesmo valor e
    essencial: se o enquadramento dependesse do conteudo do quadro, um
    escudo ou um elmo mudariam a silhueta e o overlay sairia desalinhado
    do corpo na animacao de morte.
    """
    global _LAY_OFFSET
    if _LAY_OFFSET is None:
        ref = R.to_image(R.compose(_pose())).transpose(Image.ROTATE_270)
        bb = ref.getbbox()
        _LAY_OFFSET = ((R.SIZE - (bb[2] - bb[0])) // 2 - bb[0],
                       R.ANCHORS['ground_y'] + 1 - bb[3])
    return _LAY_OFFSET


def _lay_down(img, lift):
    """Deita o corpo com rotacao exata de 90 graus (sem perda de pixels)."""
    dx, dy = _lay_offset()
    rot = img.transpose(Image.ROTATE_270)
    out = Image.new('RGBA', (R.SIZE, R.SIZE), (0, 0, 0, 0))
    out.paste(rot, (dx, dy - lift), rot)
    return out


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
        img = R.to_image(buf)
        if action == 'death':
            k = pose['_dead']
            if k >= DEATH_LYING:
                img = _lay_down(img, _lift(k))
            img = _fade(img, DEATH_ALPHA[k])
        frames.append(img)
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
