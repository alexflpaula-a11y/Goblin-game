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

FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15}
ACTIONS = ('idle', 'walk', 'attack', 'hurt', 'death')


def _pose(body=(0, 0), head=(0, 0), arm_l=(0, 0), arm_r=(0, 0),
          leg_l=(0, 0), leg_r=(0, 0), sword=(0, 0), kind='diag'):
    """Monta a pose somando o deslocamento global `body` a cada parte."""
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
IDLE_BOB = [0, 0, 1, 1, 0]


def idle_poses():
    out = []
    for i in range(5):
        b = IDLE_BOB[i]
        out.append(_pose(head=(0, b), arm_l=(0, b), arm_r=(0, b),
                         sword=(0, b), body=(0, 0)))
        out[-1]['torso'] = (0, b)
    return out


# --------------------------------------------------------------- walk ------
# Ciclo de 8 quadros: pernas em contratempo, tronco sobe no meio do passo,
# bracos balancando ao contrario das pernas.
WALK_LX = [0, 0, 0, 0, 0, 0, 0, 0]
WALK_LY = [0, -1, -2, -1, 0, 0, 0, 0]
WALK_RX = [0, 0, 0, 0, 0, 0, 0, 0]
WALK_RY = [0, 0, 0, 0, 0, -1, -2, -1]
WALK_BOB = [0, -1, -1, 0, 0, -1, -1, 0]
WALK_SWAY = [0, 0, 1, 0, 0, 0, -1, 0]


def walk_poses():
    out = []
    for i in range(8):
        bob = WALK_BOB[i]
        out.append(_pose(
            body=(0, bob),
            head=(WALK_SWAY[i], 0),
            arm_l=(0, -WALK_RY[i]),
            arm_r=(0, -WALK_LY[i]),
            leg_l=(WALK_LX[i], WALK_LY[i] - bob),
            leg_r=(WALK_RX[i], WALK_RY[i] - bob),
            sword=(0, -WALK_RY[i]),
        ))
    return out


# ------------------------------------------------------------- attack ------
# 0-4 recuo e espada erguida | 5-7 corte | 8-11 extensao | 12-16 retorno.
ATTACK = [
    # (dx corpo, dy corpo, dx braco, dy braco, tipo de adaga)
    (0, 0, 0, 0, 'diag'),
    (-1, 0, 0, -1, 'diag'),
    (-1, 0, 0, -2, 'up'),
    (-2, 0, 0, -3, 'up'),
    (-2, 0, 0, -3, 'up'),
    (-1, 0, 1, -3, 'up'),
    (1, 0, 1, -1, 'diag'),
    (2, -1, 2, 0, 'fwd'),
    (2, 0, 2, 1, 'fwd'),
    (2, 0, 2, 1, 'fwd'),
    (1, 0, 2, 1, 'fwd'),
    (1, 0, 1, 1, 'diag'),
    (0, 0, 1, 0, 'diag'),
    (0, 0, 1, 0, 'diag'),
    (0, 0, 0, 0, 'diag'),
    (0, 0, 0, 0, 'diag'),
    (0, 0, 0, 0, 'diag'),
]


def attack_poses():
    out = []
    for dx, dy, ax, ay, kind in ATTACK:
        out.append(_pose(
            body=(dx, dy),
            head=(dx // 2, 0),
            arm_l=(ax, ay),
            arm_r=(-dx // 2, 0),
            leg_l=(-dx, 0),
            leg_r=(-dx, 0),
            sword=(ax, ay),
            kind=kind,
        ))
    return out


# --------------------------------------------------------------- hurt ------
# Impacto: recuo forte, cabeca jogada para tras e tremor amortecido.
HURT_DX = [0, -1, -2, -2, -2, -1, -1, -1, 0, -1, 0, 0, 1, 0, 0, 0, 0]
HURT_HEAD = [0, -1, -1, -1, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
HURT_DY = [0, -1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
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
            sword=(-1 if i < 6 else 0, 1 if i < 8 else 0),
        )
        p['_flash'] = i in HURT_FLASH
        out.append(p)
    return out


# -------------------------------------------------------------- death ------
# 0-2 cambaleia | 3-6 as pernas cedem e o corpo afunda | 7-14 caido no chao.
# A queda final usa rotacao de exatamente 90 graus (sem perda de pixels);
# os quadros intermediarios usam agachamento, que fica bem mais limpo que
# rotacoes arbitrarias em 32x32.
DEATH_SINK = [0, 0, 1, 2, 3, 4, 5, 0, 0, 0, 0, 0, 0, 0, 0]
DEATH_LIFT = [0, 0, 0, 0, 0, 0, 0, 3, 1, 0, 0, 0, 0, 0, 0]
DEATH_ALPHA = [255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 236, 208, 176, 140, 100]
DEATH_LYING = 7   # a partir deste quadro o corpo esta deitado


def death_poses():
    out = []
    for i in range(15):
        sink = DEATH_SINK[i]
        lying = i >= DEATH_LYING
        p = _pose(
            body=(0, sink) if not lying else (0, 0),
            head=(-1 if i >= 2 else 0, 0),
            arm_l=(-1 if i >= 2 else 0, 0),
            arm_r=(1 if i >= 2 else 0, 0),
            leg_l=(-1 if i >= 3 else 0, -sink),
            leg_r=(1 if i >= 3 else 0, -sink),
            sword=(-1 if i >= 2 else 0, 1 if i >= 2 else 0),
        )
        if lying:
            p = _pose(head=(-1, 0), arm_l=(-1, 1), arm_r=(1, 0),
                      leg_l=(-1, 0), leg_r=(1, 0))
            p['sword'] = None
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
                img = _lay_down(img, DEATH_LIFT[k])
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
