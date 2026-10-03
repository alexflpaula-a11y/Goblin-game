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

FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 12}

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
DEATH_FRAMES = 12

# --- como a morte foi montada ---------------------------------------------
# Nao ha queda nenhuma. O golpe final mata na hora: o PRIMEIRO quadro da
# animacao ja mostra o goblin no chao. Em cima dele estoura uma luz
# vermelha e a palavra GOBLINZED e escrita de tres em tres letras.
#
#   0      BAQUE     ele ja aparece caido, a luz no auge
#   1-3    ESCRITA   GOBLINZED entra em tres lances (3, 6 e 9 letras)
#   4-6    ESPERA    a palavra inteira, a luz comecando a esvaziar
#   7-11   APAGA     luz, palavra e corpo somem juntos
#
# Sao 12 quadros, metade do que era: o pedido foi que fosse mais rapido e
# que ele ja aparecesse no chao, sem agachar e sem tombar.

GOBLINZED = 'GOBLINZED'
GOBLINZED_DEITA = 0           # ele ja comeca caido: a morte e instantanea

# Quantas letras ja foram escritas em cada quadro — de tres em tres, para
# a palavra inteira estar na tela ja no quarto quadro.
GOBLINZED_LETRAS = [0, 3, 6, 9] + [9] * 8

# Opacidade da palavra: entra inteira com as primeiras letras e so apaga
# no fim, junto com o corpo.
GOBLINZED_ALPHA = [0] + [255] * 6 + [228, 188, 142, 94, 46]

# Forca da luz vermelha, de 0 a 1. Estoura no baque e vai esvaziando.
DEATH_GLOW = [1.0, 0.95, 0.90, 0.84, 0.74, 0.60, 0.48,
              0.36, 0.26, 0.17, 0.09, 0.0]

DEATH_ALPHA = ([255] * 8) + [226, 188, 144, 98]


def death_poses():
    """Todo quadro da morte ja e o corpo no chao. Nao ha pose de pe."""
    out = []
    for i in range(DEATH_FRAMES):
        p = {k: None for k in R.DRAW_ORDER}
        p['_lay'] = (0, 0)
        # a mao continua sendo uma ancora: a arma equipada cai junto
        p['sword'] = (0, 0)
        p['_sword'] = 'fwd'
        p['_eyes_shut'] = True
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
# O que transforma os quadros de pe em quadros de MORTE nao esta no rig:
# e a luz vermelha e a palavra GOBLINZED, as duas aplicadas aqui, depois
# de o corpo ja estar desenhado.
#
# As duas sao desenhadas de forma DETERMINISTICA — nao dependem da
# silhueta do quadro. Isso importa porque o gerador de equipamento monta
# cada overlay como a diferenca entre o quadro vestido e o quadro nu: se a
# luz seguisse o contorno, cada armadura levaria junto uma franja vermelha
# que nao e dela. Do jeito que esta, luz e letras se cancelam na subtracao
# e o overlay sai so com a peca.

VERMELHO = (255, 64, 48)          # a luz
LETRA = (236, 42, 42)             # o corpo da letra
LETRA_ALTO = (255, 138, 120)      # o brilho em cima da letra
LETRA_BORDA = (56, 6, 10)         # o contorno, para ler sobre qualquer fundo

GLOW_CENTRO = (32, 34)
GLOW_RAIO = 26
GLOW_FAIXAS = (140, 100, 62, 28)          # degraus de opacidade, do centro


def _halo():
    """Auréola vermelha, desenhada uma vez e reaproveitada.

    Em DEGRAUS chapados, nao em degrade continuo: alem de combinar com o
    resto da arte, um degrade de 64x64 em cada um dos 24 quadros de morte
    de cada variacao engordava o jogo em megabytes de pixel quase igual.
    """
    if _halo.cache is None:
        img = Image.new('RGBA', (R.SIZE, R.SIZE), (0, 0, 0, 0))
        px = img.load()
        cx, cy = GLOW_CENTRO
        n = len(GLOW_FAIXAS)
        for y in range(R.SIZE):
            for x in range(R.SIZE):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / GLOW_RAIO
                if d < 1.0:
                    px[x, y] = VERMELHO + (GLOW_FAIXAS[min(n - 1, int(d * n))],)
        _halo.cache = img
    return _halo.cache


_halo.cache = None


def _brilho(img, k):
    """Banha o quadro em luz vermelha: halo por tras e tinta no corpo."""
    if k <= 0:
        return img
    halo = _halo().copy()
    # o k tambem anda em degraus, para os quadros se repetirem mais
    passo = max(1, int(round(k * 8)))
    halo.putalpha(halo.getchannel('A').point(lambda v: v * passo // 8))
    fundo = Image.new('RGBA', img.size, (0, 0, 0, 0))
    fundo.alpha_composite(halo)
    # tinta: mistura cada pixel do corpo com o vermelho, sem mexer no alfa
    corpo = img.convert('RGBA')
    chapa = Image.new('RGBA', img.size, VERMELHO + (255,))
    chapa.putalpha(corpo.getchannel('A'))
    # a tinta tambem anda em degraus: quadros vizinhos saem iguais e o
    # arquivo unico do jogo nao engorda com 24 vermelhos quase iguais
    corpo = Image.blend(corpo, chapa, round(min(0.62, 0.62 * k) * 4) / 4)
    corpo.putalpha(img.getchannel('A'))
    fundo.alpha_composite(corpo)
    return fundo


# Fonte 4x5 so com as letras de GOBLINZED. E o maior tamanho que deixa a
# palavra inteira (9 letras = 44 px) caber nos 64 px do quadro.
FONTE = {
    'G': ['####', '#...', '#.##', '#..#', '####'],
    'O': ['####', '#..#', '#..#', '#..#', '####'],
    'B': ['###.', '#..#', '###.', '#..#', '###.'],
    'L': ['#...', '#...', '#...', '#...', '####'],
    'I': ['####', '.##.', '.##.', '.##.', '####'],
    'N': ['#..#', '##.#', '#.##', '#..#', '#..#'],
    'Z': ['####', '...#', '.##.', '#...', '####'],
    'E': ['####', '#...', '###.', '#...', '####'],
    'D': ['###.', '#..#', '#..#', '#..#', '###.'],
}
LETRA_W, LETRA_H, LETRA_GAP = 4, 5, 1
TEXTO_Y = 7


def _escrever(img, letras, alpha):
    """Escreve GOBLINZED por cima do quadro, da esquerda para a direita."""
    if letras <= 0 or alpha <= 0:
        return img
    passo = LETRA_W + LETRA_GAP
    largura = len(GOBLINZED) * passo - LETRA_GAP
    x0 = (R.SIZE - largura) // 2
    marcados = set()
    for n, ch in enumerate(GOBLINZED[:letras]):
        bx = x0 + n * passo
        for dy, linha in enumerate(FONTE[ch]):
            for dx, c in enumerate(linha):
                if c == '#':
                    marcados.add((bx + dx, TEXTO_Y + dy))
    camada = Image.new('RGBA', img.size, (0, 0, 0, 0))
    px = camada.load()
    # contorno primeiro, para a palavra ler sobre o corpo e sobre o fundo
    for (x, y) in marcados:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                q = (x + ox, y + oy)
                if q not in marcados and 0 <= q[0] < R.SIZE and 0 <= q[1] < R.SIZE:
                    px[q] = LETRA_BORDA + (255,)
    for (x, y) in marcados:
        # a linha de cima de cada letra e mais clara: da relevo
        px[x, y] = (LETRA_ALTO if (x, y - 1) not in marcados else LETRA) + (255,)
    camada.putalpha(camada.getchannel('A').point(lambda v: v * alpha // 255))
    out = img.copy()
    out.alpha_composite(camada)
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


def post(img, pose, efeitos=True):
    """Pos-processo da morte: luz vermelha, desvanecer e a palavra.

    `efeitos=False` devolve so o corpo, sem luz nem letras. E o que os
    testes usam: a palavra GOBLINZED e, de proposito, um pedaco solto do
    desenho, e sem esta chave ela seria reprovada como membro descolado.
    """
    k = pose.get('_dead')
    if k is None:
        return img
    if efeitos:
        img = _brilho(img, DEATH_GLOW[k])
    img = _fade(img, DEATH_ALPHA[k])
    if efeitos:
        img = _escrever(img, GOBLINZED_LETRAS[k], GOBLINZED_ALPHA[k])
    return img


def render_action(action, variation=None, efeitos=True):
    """Retorna a lista de Images de uma animacao, ja com a variacao aplicada."""
    frames = []
    swap = variation.get('swap') if variation else None
    parts = variation.get('parts') if variation else None
    detail = variation.get('detail') if variation else None
    for i, pose in enumerate(POSES[action]()):
        buf = R.compose(pose, variation=detail, swap=swap, extra_parts=parts)
        if pose.get('_flash'):
            _flash(buf)
        frames.append(post(R.to_image(buf), pose, efeitos))
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
