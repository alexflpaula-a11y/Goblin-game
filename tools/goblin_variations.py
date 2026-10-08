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
    # Tons escolhidos para bater com os sprites ORIGINAIS do repositorio:
    # albino rosado, tatuagem azul, queimadura avermelhada.
    # ALBINO: rampa de 7 tons na MESMA ordem de claridade dos 8 tons de
    # pele do original (k,e,d,n,j,g,l,f). Antes eram so 4 tons, entao o
    # sombreado do desenho desabava e o goblin virava uma mancha rosa
    # chapada sem rosto.
    'U': (58, 44, 46, 255),      # albino: contorno
    'F': (118, 86, 90, 255),     # albino: sombra funda
    'E': (164, 126, 128, 255),   # albino: sombra
    'C': (190, 154, 154, 255),   # albino: meio-tom
    'A': (210, 176, 176, 255),   # albino: pele
    'H': (226, 194, 192, 255),   # albino: pele clara
    'a': (240, 218, 214, 255),   # albino: luz
    # MARCA DE NASCENCA: vinho acinzentado. O roxo saturado nao parecia
    # pele nenhuma, parecia um adesivo colado na cara.
    'P': (108, 70, 96, 255),     # mancha de nascenca
    'V': (140, 98, 124, 255),    # mancha de nascenca luz
    'v': (70, 46, 72, 255),      # veias / borda da mancha
    'G': (188, 150, 46, 255),    # ouro sombra
    # QUEIMADURA: casca marrom-avermelhada, nao vermelho de sangue.
    'Q': (150, 74, 62, 255),     # queimadura (casca)
    'Z': (196, 110, 86, 255),    # queimadura viva (centro)
    'I': (48, 78, 150, 255),     # tatuagem azul
    'J': (28, 44, 96, 255),      # tatuagem azul escura
    't': (96, 138, 214, 255),    # tatuagem luz
    'X': (184, 180, 166, 255),   # sombra de atadura
    'u': (240, 206, 104, 255),   # ouro luz
    'x': (54, 54, 62, 255),      # couro do tapa-olho (brilho)
    # BRANCO PURO, so para o olho vazio. O 'w' do rig e um branco quente
    # (240,240,222): em cima de pele verde ele puxa para o creme e o olho
    # ainda lia como amarelado.
    '*': (255, 255, 255, 255),   # branco de olho vazio
})

# Mapa da cabeca (36x20), lido da arte de referencia em 64x64:
#   cranio cols 12..30 | orelha esquerda cols 0..13, direita cols 24..35
#   testa rows 8..12 | olhos rows 13-14 | focinho rows 15..17
#   boca/dente row 18 | queixo row 19
EYE_L = R.FACE_CELLS['eye_l']
EYE_R = R.FACE_CELLS['eye_r']
PUPIL_L = R.FACE_CELLS['pupil_l']
PUPIL_R = R.FACE_CELLS['pupil_r']
# A celula 'pupil_r' do rig vai ate x28, mas x27-28 sao a BORDA escura do
# lado direito da cabeca, nao pupila. Pintar aquilo de dourado estendia o
# olho num risco ate o fim da cara — era isso que dava cara de oculos.
# Para trocar a COR do olho usamos estas duas caixas compactas.
OLHO_E = [(16, 13), (17, 13), (18, 13), (16, 14), (17, 14), (18, 14)]
OLHO_D = [(25, 13), (26, 13), (25, 14), (26, 14)]
BROW_L = R.FACE_CELLS['brow_l']
BROW_R = R.FACE_CELLS['brow_r']
TUSK = R.FACE_CELLS['tusk']
FOREHEAD = [(x, y) for y in range(8, 13) for x in range(12, 28)]
CROWN = [(x, y) for y in range(1, 7) for x in range(13, 30)]
EAR_L_CORE = [(x, y) for y in (5, 6, 7) for x in range(2, 11)]
EAR_R_CORE = [(x, y) for y in (4, 5, 6, 7) for x in range(28, 34)]
EAR_L_LOBE = [(2, 8), (3, 8), (4, 8), (5, 8)]
EAR_R_LOBE = [(32, 7), (33, 7), (34, 7)]
CHEEK_L = [(12, 15), (12, 16), (12, 17), (13, 18)]
CHEEK_R = [(26, 15), (26, 16), (25, 17), (25, 18)]


def _put(buf, x, y, ch):
    if 0 <= x < R.SIZE and 0 <= y < R.SIZE and buf[y][x] is not None:
        buf[y][x] = ch


_MASK = set()

# Regra desta rodada: NENHUM traco tapa o olho. So o tapa-olho e o olho
# cego podem mexer ali, e passando sobre_olhos=True de proposito. Era isso
# que fazia metade das 45 variacoes ficarem sem olhar.
OLHOS = set(EYE_L + EYE_R + PUPIL_L + PUPIL_R + BROW_L + BROW_R)


def _head_paint(buf, ctx, cells, ch, over_outline=False, add=False,
                sobre_olhos=False):
    """Pinta celulas em coordenadas da CABECA, em qualquer quadro.

    `add=True` deixa o traco sair da silhueta — e o que permite pendurar um
    brinco ao lado da orelha ou deixar a ponta da bandana balancando. Sem
    isso, todo adorno tinha de caber dentro do desenho e acabava virando
    um ou dois pixels perdidos no meio da pele, que e exatamente o que
    deixava as 45 variacoes parecendo todas iguais.
    """
    if 'head' not in ctx:
        return
    hx, hy, flip = ctx['head']
    # se a cabeca inclinou neste quadro, a marca inclina com ela
    desl = ctx.get('_desl', {}).get('head')
    # se a ORELHA se mexeu, a marca que estava nela vai junto
    orelha = ctx.get('_orelha')
    for fx, fy in cells:
        if not sobre_olhos and (fx, fy) in OLHOS:
            continue
        if orelha and (fx, fy) in orelha:
            fx, fy = orelha[(fx, fy)]
        x = hx + (R.HEAD_W - 1 - fx if flip else fx)
        y = hy + fy
        if desl and 0 <= fy < len(desl):
            x += -desl[fy] if flip else desl[fy]
        if 0 <= x < R.SIZE and 0 <= y < R.SIZE and (x, y) not in _MASK:
            if buf[y][x] is None and not add:
                continue
            if buf[y][x] == 'o' and not over_outline:
                continue
            buf[y][x] = ch      # ch=None APAGA o pixel (corte na orelha)


def _part_paint(buf, ctx, part, cells, ch, add=False, over_outline=False):
    """Pinta celulas em coordenadas da PARTE (torso, pernas, bracos).

    `add=True` deixa o traco sair da silhueta — e o que permite pendurar
    um fiapo de pano abaixo da bainha do macacao.
    """
    if part not in ctx:
        return
    ax, ay, flip = ctx[part]
    w = len(R.DEFAULT_PART[part][0])
    desl = ctx.get('_desl', {}).get(part)
    for rx, ry in cells:
        x = ax + (w - 1 - rx if flip else rx)
        y = ay + ry
        if desl and 0 <= ry < len(desl):
            x += -desl[ry] if flip else desl[ry]
        if not (0 <= x < R.SIZE and 0 <= y < R.SIZE) or (x, y) in _MASK:
            continue
        if buf[y][x] is None and not add:
            continue
        if buf[y][x] == 'o' and not over_outline:
            continue
        buf[y][x] = ch


def _arm_paint(buf, ctx, part, rows, ch, cols=None):
    if part not in ctx:
        return
    ax, ay, flip = ctx[part]
    cols = cols if cols is not None else range(len(R.DEFAULT_PART[part][0]))
    desl = ctx.get('_desl', {}).get(part)
    for ry in rows:
        d = desl[ry] if desl and 0 <= ry < len(desl) else 0
        for rx in cols:
            x, y = ax + rx + (-d if flip else d), ay + ry
            if (0 <= x < R.SIZE and 0 <= y < R.SIZE
                    and buf[y][x] not in (None, 'o') and (x, y) not in _MASK):
                buf[y][x] = ch


# --------------------------------------------------------------- tracos ----
# Regra destas 45 aparencias: a marca tem de ser reconhecida de longe, no
# tamanho em que o jogo desenha o goblin. Na primeira versao quase todas
# eram 1 ou 2 pixels e, lado a lado, as 45 pareciam o mesmo goblin. Agora
# cada traco tem corpo, luz e sombra — e os que sao adorno (brinco, ponta
# da bandana) podem sair da silhueta, que e o que faz eles aparecerem.


def t_gold_tooth(buf, ctx):
    """Presa de ouro: uma lasca grande subindo do labio, nao um ponto."""
    # Presa de ouro saindo do labio de baixo. A versao anterior ocupava
    # 3x5 no meio da cara e virava um bico amarelo.
    # A presa de ouro E a presa que o goblin ja tem (x21-22, linha 18):
    # ela so troca de material. Com o vao escuro dos dois lados, o olho le
    # um dente. Antes era um amassado amarelo solto no meio do focinho.
    _head_paint(buf, ctx, [(21, 17), (21, 18)], 'u')
    _head_paint(buf, ctx, [(22, 17), (22, 18)], 'Y')
    _head_paint(buf, ctx, [(21, 19), (22, 19)], 'G')
    # o vao escuro dos dois lados e o que transforma a mancha em dente
    _head_paint(buf, ctx, [(20, 17), (20, 18), (23, 17), (23, 18)], 'k')


def t_eyepatch(buf, ctx):
    """Tapa-olho: a placa cobre o olho inteiro e a tira atravessa a cabeca."""
    # A placa cobre SO o olho direito, com as quinas cortadas. Antes era
    # um retangulo 7x4 que comia meia cara.
    placa = ([(x, 12) for x in range(23, 28)]
             + [(x, 13) for x in range(23, 29)]
             + [(x, 14) for x in range(23, 29)]
             + [(x, 15) for x in range(24, 28)])
    _head_paint(buf, ctx, placa, 'K', over_outline=True, sobre_olhos=True)
    # tira de 1 px subindo em escada ate a orelha, acima da sobrancelha
    _head_paint(buf, ctx, [(25, 13), (26, 13)], 'x',
                over_outline=True, sobre_olhos=True)
    tira = [(22, 12), (22, 11), (21, 11), (20, 11), (20, 10), (19, 10),
            (18, 10), (17, 10), (16, 10), (16, 9), (15, 9), (14, 9),
            (13, 9), (12, 9), (12, 8), (11, 8), (10, 8), (9, 8)]
    _head_paint(buf, ctx, tira, 'K', over_outline=True, sobre_olhos=True)


def _hoop(cx, y0):
    """Argola de ouro 3x4 pendurada do lobo, com o furo escuro no meio.

    A versao anterior era um bloco 4x4 de ouro solto dois pixels abaixo da
    orelha: na tela virava um cubinho dourado flutuando. Agora o pino sai
    DO lobo (y0 encosta na orelha) e o miolo fica em 'k', que e o que faz
    o olho ler um anel e nao um quadrado.
    """
    return ([(cx, y0, 'u')]                                   # pino no lobo
            + [(cx - 1, y0 + 1, 'Y'), (cx, y0 + 1, 'k'),
               (cx + 1, y0 + 1, 'Y')]
            + [(cx - 1, y0 + 2, 'Y'), (cx, y0 + 2, 'k'),
               (cx + 1, y0 + 2, 'Y')]
            + [(cx - 1, y0 + 3, 'G'), (cx, y0 + 3, 'Y'),
               (cx + 1, y0 + 3, 'G')])


def _put_hoop(buf, ctx, cx, y0):
    for x, y, ch in _hoop(cx, y0):
        _head_paint(buf, ctx, [(x, y)], ch, over_outline=True, add=True)


def t_ear_ring(buf, ctx):
    """Uma argola, na orelha esquerda. Pendurada do lobo."""
    _head_paint(buf, ctx, EAR_L_LOBE, 'G', over_outline=True)
    _put_hoop(buf, ctx, 3, 9)


def t_earring(buf, ctx):
    """Um par de argolas, uma em cada orelha."""
    _head_paint(buf, ctx, EAR_L_LOBE + EAR_R_LOBE, 'G', over_outline=True)
    _put_hoop(buf, ctx, 3, 9)
    _put_hoop(buf, ctx, 33, 8)


def t_scar(buf, ctx):
    """Cicatriz costurada descendo da testa ate a bochecha."""
    # passa POR FORA do olho (coluna 12-13), nunca por cima dele
    # Corte comprido, do alto da tempora ate o queixo, em escada e sempre
    # por FORA do olho. Cinco pares de pontos de costura cruzando.
    corte = [(12, 8), (12, 9), (12, 10), (12, 11),
             (13, 12), (13, 13), (13, 14), (13, 15),
             (14, 16), (14, 17), (14, 18)]
    _head_paint(buf, ctx, corte, 'f', over_outline=True)
    pontos = [(11, 9), (13, 9), (11, 11), (13, 11),
              (12, 13), (14, 13), (12, 15), (14, 15),
              (13, 17), (15, 17)]
    # Pontos em 'k': costura verde-escura sobre pele verde nao aparecia, e
    # sem os pontos atravessando o corte ele ficava um fio claro de 1 px
    # pendurado na cara, parecendo um risco na imagem.
    _head_paint(buf, ctx, pontos, 'k')
    _head_paint(buf, ctx, [(12, 7), (13, 19), (11, 13), (15, 15),
                           (11, 10), (14, 14), (15, 18)], 'd')


def t_burns(buf, ctx):
    """Queimadura: mancha grande e viva no rosto, no ombro e no braco."""
    # Mancha na tempora/bochecha DIREITA, longe da boca e do olho. Antes
    # ela cobria o focinho inteiro e parecia sangue escorrendo.
    # Casca de queimadura: borda rasgada, crosta escura em volta e so um
    # ponto de carne viva no meio. Um retangulo vermelho chapado nao le
    # como queimadura, le como um cubo de sangue colado na cara.
    _head_paint(buf, ctx, [(23, 14), (24, 14),
                           (22, 15), (23, 15), (24, 15), (25, 15),
                           (22, 16), (23, 16), (24, 16), (25, 16), (26, 16),
                           (22, 17), (23, 17), (24, 17), (25, 17), (26, 17),
                           (23, 18), (24, 18), (25, 18)], 'Q')
    _head_paint(buf, ctx, [(23, 16), (24, 17), (23, 15)], 'Z')
    _head_paint(buf, ctx, [(22, 14), (25, 14), (21, 15), (26, 15),
                           (21, 17), (27, 17), (22, 18), (26, 18),
                           (24, 19), (23, 19)], 'R')
    # respingo no ombro: escorrido, nao um tijolo
    _arm_paint(buf, ctx, 'arm_l', (2,), 'Q', cols=range(6, 9))
    _arm_paint(buf, ctx, 'arm_l', (3,), 'Q', cols=range(5, 10))
    _arm_paint(buf, ctx, 'arm_l', (4,), 'Q', cols=range(4, 10))
    _arm_paint(buf, ctx, 'arm_l', (5,), 'Q', cols=range(4, 9))
    _arm_paint(buf, ctx, 'arm_l', (6,), 'Q', cols=range(4, 8))
    _arm_paint(buf, ctx, 'arm_l', (7,), 'Q', cols=range(5, 7))
    _arm_paint(buf, ctx, 'arm_l', (4,), 'Z', cols=range(5, 7))
    _arm_paint(buf, ctx, 'arm_l', (3,), 'R', cols=range(8, 10))
    _arm_paint(buf, ctx, 'arm_l', (7,), 'R', cols=range(4, 5))
    _arm_paint(buf, ctx, 'arm_l', (8,), 'R', cols=range(5, 7))


# Faixas na cabeca: ficam na TESTA, acima dos olhos, e seguem a largura do
# cranio linha a linha. Antes eram um retangulo chapado que cobria os olhos e
# transbordava pelas orelhas — parecia um bone, nao uma faixa.
# Elas ficam no CRANIO (colunas 12..29), nunca atravessando as orelhas:
# a faixa larga de ponta a ponta era o que virava uma tabua na cara.
# Nas linhas 7-9 a orelha e o cranio sao o MESMO trecho continuo de
# pixels, entao medir a largura da linha inteira esticava a faixa por
# dentro das orelhas: a ponta direita subia e saia em bico por cima da
# orelha, que e o que fazia a bandana parecer um trapo jogado na cabeca
# em vez de amarrada nela. Os limites do cranio sao fixos (9..30) e a
# borda de cima entra em diagonal, enrolando pela tempora esquerda.
BANDAGE_ROWS = {7: (20, 29), 8: (16, 30), 9: (13, 30),
                10: (10, 29), 11: (10, 29)}
# A BANDANA e diferente da atadura: ela e amarrada, entao e uma faixa
# RETA de tres linhas. Com a borda em diagonal (que fica boa na atadura)
# o vermelho subia por cima da orelha de um lado so e o pano parecia uma
# bandeira pendurada na cabeca.
BANDANA_ROWS = {9: (10, 29), 10: (10, 29), 11: (10, 29)}


def _band(spans):
    return [(x, y) for y, (a, b) in spans.items() for x in range(a, b)
            if R.HEAD[y][x] != '.']


def _weave(spans, claro, escuro):
    """Divide a faixa em voltas diagonais de pano.

    Uma faixa de uma cor so vira uma tabua branca atravessada na cara. Com
    as voltas em diagonal o olho le tecido enrolado.
    """
    a, b = [], []
    for x, y in _band(spans):
        (a if (x + 2 * y) % 5 < 3 else b).append((x, y))
    return (a, claro), (b, escuro)


# As pontas da bandana caem em ESCADA, nunca em diagonal pura: um pixel
# que so encosta pela quina fica solto na tela e o teste de corpo inteiro
# reprova (foi assim que a ponta antiga saiu voando ao lado da cabeca).
BANDANA_TAIL = [(10, 12), (11, 12), (10, 13), (11, 13), (10, 14),
                (10, 15)]
BANDANA_TAIL_SHADOW = [(12, 13), (11, 14), (11, 15), (10, 16)]


def t_bandana(buf, ctx):
    """Bandana vermelha cobrindo a testa, com no e a ponta caida."""
    # Pano LISO: tres linhas de vermelho, luz em cima e sombra embaixo.
    # Com o tear diagonal o vermelho ficava malhado e parecia uma cobra.
    # Faixa RETA logo acima da sobrancelha. Quando ela acompanhava o alto
    # do cranio (que e inclinado) o vermelho descia pela orelha e virava
    # uma cobra atravessada na cabeca.
    _head_paint(buf, ctx, _band(BANDANA_ROWS), 'r')
    _head_paint(buf, ctx, [(x, 9) for x in range(13, 26)], 'Z')    # luz
    a, b = BANDANA_ROWS[11]
    _head_paint(buf, ctx, [(x, 11) for x in range(a, b)], 'R')     # borda
    _head_paint(buf, ctx, [(10, 10), (11, 10), (10, 11)], 'r')     # no
    _head_paint(buf, ctx, [(11, 11), (12, 10)], 'R')
    _head_paint(buf, ctx, BANDANA_TAIL, 'r', over_outline=True, add=True)
    _head_paint(buf, ctx, BANDANA_TAIL_SHADOW, 'R', over_outline=True, add=True)


def t_arm_bandage(buf, ctx):
    """Atadura enrolada do cotovelo ao punho, com a dobra escura entre voltas."""
    for linha, ch in ((2, 'W'), (3, 'W'), (4, 'X'), (5, 'W'),
                      (6, 'W'), (7, 'X'), (8, 'W'), (9, 'W')):
        _arm_paint(buf, ctx, 'arm_r', (linha,), ch, cols=range(1, 8))
    _arm_paint(buf, ctx, 'arm_r', (3, 6), 'w', cols=range(2, 4))


def t_hand_wrap(buf, ctx):
    """Maos enfaixadas: a atadura passa do punho e cobre os nos dos dedos.

    As duas maos, para o goblin nao ficar com uma enfaixada e a outra nao.
    A dobra escura (X) entre as voltas e o que impede a mao de virar uma
    luva branca lisa.
    """
    # mao do braco de baixo (a que fica solta ao lado do corpo)
    for linha, ch in ((10, 'W'), (11, 'X'), (12, 'W'), (13, 'W')):
        _arm_paint(buf, ctx, 'arm_l', (linha,), ch, cols=range(1, 7))
    _arm_paint(buf, ctx, 'arm_l', (12,), 'w', cols=range(3, 5))
    # mao do braco da arma
    for linha, ch in ((8, 'W'), (9, 'X'), (10, 'W'), (11, 'W')):
        _arm_paint(buf, ctx, 'arm_r', (linha,), ch, cols=range(2, 8))
    _arm_paint(buf, ctx, 'arm_r', (10,), 'w', cols=range(4, 6))


def t_birthmark(buf, ctx):
    """Marca de nascenca: mancha roxa larga sobre metade da testa."""
    # Mancha na tempora direita, acima da sobrancelha. Antes era um bloco
    # 6x5 roxo chapado cobrindo meia testa.
    # Contorno irregular de proposito: um retangulo roxo vira um cubo
    # colado na cara, uma mancha de nascenca tem borda rasgada.
    # Fica no MAXILAR ESQUERDO, descendo pela lateral do rosto. Logo
    # abaixo do olho ela competia com o olhar e lia como um decalque
    # colado no meio da cara.
    _head_paint(buf, ctx, [(11, 15), (12, 15),
                           (10, 16), (11, 16), (12, 16), (13, 16),
                           (10, 17), (11, 17), (12, 17), (13, 17),
                           (11, 18), (12, 18), (13, 18),
                           (12, 19)], 'P')
    _head_paint(buf, ctx, [(11, 16), (11, 17)], 'V')
    _head_paint(buf, ctx, [(13, 15), (14, 17), (10, 18), (14, 18),
                           (13, 19)], 'v')


def t_head_bandage(buf, ctx):
    """Cabeca enfaixada: a atadura da a volta e uma ponta desce pela tempora."""
    for cells, ch in _weave(BANDAGE_ROWS, 'W', 'X'):
        _head_paint(buf, ctx, cells, ch)
    _head_paint(buf, ctx, [(x, 8) for x in range(21, 28)], 'w')    # luz
    _head_paint(buf, ctx, [(x, 9) for x in range(16, 22)], 'w')
    a, b = BANDAGE_ROWS[11]
    _head_paint(buf, ctx, [(x, 11) for x in range(a, b)], 'X')     # borda
    # SEGUNDA volta: desce em diagonal pela bochecha esquerda e fecha por
    # baixo do queixo. E ela que faz a cabeca parecer ENFAIXADA, e nao so
    # com uma tira na testa.
    diag = [(10, 12), (11, 12), (10, 13), (11, 13), (11, 14), (12, 14),
            (12, 15), (13, 15), (13, 16), (14, 16), (14, 17), (15, 17),
            (15, 18), (16, 18), (17, 18), (18, 18), (19, 18)]
    _head_paint(buf, ctx, diag, 'W', over_outline=True)
    _head_paint(buf, ctx, [(12, 12), (12, 13), (13, 14), (14, 15),
                           (15, 16), (16, 17), (16, 19), (17, 19),
                           (18, 19), (19, 19)], 'X', over_outline=True)
    _head_paint(buf, ctx, [(11, 12), (13, 15), (15, 17)], 'w')
    # No na tempora e a ponta solta descendo COLADA na lateral do rosto.
    # Solta no ar ela virava um fiapo branco flutuando ao lado da cabeca:
    # nas linhas 13-15 a coluna 9 e vazio, nao cabeca.
    _head_paint(buf, ctx, [(10, 10), (11, 10), (10, 11), (11, 11),
                           (10, 12), (11, 12), (10, 13), (11, 13),
                           (10, 14), (11, 14)], 'W', over_outline=True)
    _head_paint(buf, ctx, [(12, 11), (12, 13), (10, 15), (11, 15)], 'X',
                over_outline=True)


# Regra dos olhos: a esclera continua sendo a do desenho original. So a
# PUPILA troca de cor. Pintar o olho inteiro de uma cor so apagava o olhar e
# deixava um retangulo colorido no lugar do olho.
def t_blind_eye(buf, ctx):
    """Olho cego: a pupila fica leitosa e um corte atravessa a palpebra."""
    # o olho inteiro vira leitoso: a pupila some, e isso que le "cego"
    _head_paint(buf, ctx, OLHO_E, 'w',
                over_outline=True, sobre_olhos=True)
    _head_paint(buf, ctx, [(16, 14), (18, 14), (18, 13)], 'X',
                sobre_olhos=True)
    # corte fundo passando por cima e por baixo da palpebra
    _head_paint(buf, ctx, [(16, 9), (16, 10), (16, 11),
                           (16, 16), (16, 17), (16, 18)], 'f',
                over_outline=True)
    _head_paint(buf, ctx, [(15, 11), (17, 10), (15, 17), (17, 16)], 'e')


def t_ruby_eye(buf, ctx):
    """Olho de rubi: pupila acesa, com o brilho em volta."""
    # a esclera continua branca: so a pupila acende. Pintar o olho todo
    # de vermelho apagava o olhar e virava um quadradinho colorido.
    _head_paint(buf, ctx, OLHO_E, 'R',
                over_outline=True, sobre_olhos=True)
    _head_paint(buf, ctx, [(17, 13), (17, 14)], 'r',
                over_outline=True, sobre_olhos=True)
    # o brilho bate na pele em volta do olho
    _head_paint(buf, ctx, [(15, 13), (15, 14), (19, 13), (19, 14),
                           (15, 15), (16, 15), (17, 15), (18, 15)], 'Q')


def t_wart(buf, ctx):
    """Verruga grande no focinho, com volume."""
    # Caroco pequeno no focinho, na cor da pele (verruga nao e roxa) com
    # sombra embaixo para dar volume. Antes ocupava 3x3+ e virava mancha.
    # Uma verruga so se le quando ela DEFORMA a silhueta. Pintada dentro
    # da bochecha, na cor da pele, ela sumia; pintada de outra cor, virava
    # mancha. Entao ela sai para fora do contorno, com contorno proprio.
    _head_paint(buf, ctx, [(7, 16), (7, 17)], 'l', over_outline=True, add=True)
    _head_paint(buf, ctx, [(8, 16), (8, 17), (7, 18), (8, 18)], 'd',
                over_outline=True, add=True)
    _head_paint(buf, ctx, [(6, 16), (6, 17), (6, 18), (7, 15), (8, 15),
                           (7, 19), (8, 19)], 'k', over_outline=True, add=True)
    # segunda verruga, menor, na saliencia da testa
    _head_paint(buf, ctx, [(13, 10), (14, 10)], 'n')
    _head_paint(buf, ctx, [(13, 11), (14, 11)], 'k')


# Sardas de 1 px desaparecem no sombreado da pele. Cada sarda e um par de
# pixels, com um ponto mais escuro ao lado, para virar mancha e nao ruido.
# Sardas espalhadas aos pares pelas duas bochechas e pelo nariz. Em 1 px
# elas somem no mosqueado da pele; os pares ficam nas linhas 14-18, que e
# onde a bochecha e lisa o bastante para a sarda aparecer.
# Pixels SOLTOS, em alturas diferentes. Em pares horizontais elas viravam
# tracinhos enfileirados, parecia bigode e nao sarda.
FRECKLES = [(11, 16), (12, 14), (13, 17), (11, 18), (14, 15),
            (19, 14), (20, 16),
            (23, 16), (24, 14), (25, 17), (23, 18), (26, 15)]
FRECKLES_FRACAS = [(12, 17), (15, 17), (24, 17), (21, 14)]


def t_freckles(buf, ctx):
    """Sardas: pares de pixels espalhados pelas duas bochechas e pelo nariz."""
    # Marrom, nao verde escuro: sarda verde sobre pele verde sumia no
    # mosqueado do desenho e a variacao ficava identica ao goblin limpo.
    _head_paint(buf, ctx, FRECKLES, 'c')
    _head_paint(buf, ctx, FRECKLES_FRACAS, 'B')


def t_tattoo(buf, ctx):
    """Tatuagem facial: tracos largos em azul descendo pelas duas faces."""
    # dois tracos finos nas temporas, por FORA dos olhos, e marcas na
    # bochecha. A versao larga descia por cima da sobrancelha.
    # Duas riscas por face: uma descendo a tempora (por fora do olho) e
    # uma na bochecha. Antes eram barras largas pintadas sobre as orelhas.
    # Pintura de guerra: duas riscas verticais de 1 px em cada bochecha e
    # um chevron na testa. Barras largas e chapadas pareciam adesivos.
    # Duas faixas de 2 px em cada bochecha, descendo da macã do rosto ate
    # o maxilar, mais um chevron grande na testa.
    for x in (11, 12, 14, 15, 22, 23, 25, 26):
        _head_paint(buf, ctx, [(x, y) for y in (15, 16, 17)], 'I')
    for x in (11, 14, 22, 25):
        _head_paint(buf, ctx, [(x, 15)], 't')
    for x in (12, 15, 23, 26):
        _head_paint(buf, ctx, [(x, 18)], 'J')
    # chevron na testa, de orelha a orelha
    chevron = [(16, 8), (17, 9), (18, 10), (19, 11), (20, 11),
               (21, 10), (22, 9), (23, 8)]
    _head_paint(buf, ctx, chevron, 'I')
    _head_paint(buf, ctx, [(x, y + 1) for x, y in chevron], 'J')
    # risca atravessando o cavalete do nariz
    _head_paint(buf, ctx, [(x, 14) for x in range(18, 22)], 'I')
    _head_paint(buf, ctx, [(19, 14), (20, 14)], 't')


def t_double_fangs(buf, ctx):
    """Presas duplas: dois caninos saindo da BOCA, um de cada canto.

    A boca e a linha 18 da cabeca (15-17 sao focinho). As presas antigas
    comecavam na 16 e subiam ate quase os olhos: ficavam duas lascas
    brancas no meio da cara, ACIMA da boca, e de longe pareciam um segundo
    par de olhos claros. Agora nascem na linha da boca, sobem uma linha so
    — como a presa que o goblin ja tem — e tem sombra embaixo.
    """
    # abre a boca: apaga a presa unica do meio para sobrarem DUAS
    _head_paint(buf, ctx, [(21, 18), (22, 18), (23, 18)], 'e')
    # canino esquerdo e direito, nos cantos da boca
    _head_paint(buf, ctx, [(19, 18), (20, 18), (20, 17)], 'w')
    _head_paint(buf, ctx, [(25, 18), (24, 18), (24, 17)], 'w')
    # ponta mais clara e sombra do dente contra o labio
    _head_paint(buf, ctx, [(20, 17), (24, 17)], 'q')
    _head_paint(buf, ctx, [(19, 19), (20, 19), (24, 19), (25, 19)], 'k')


def t_glow_eyes(buf, ctx):
    """Olhos em branco: os dois ficam brancos lisos, SEM pupila."""
    # esclera dourada + pupila clara: o olho continua tendo DUAS cores,
    # entao ainda se le um olho, so que aceso.
    # Olho ACESO nao tem pupila: a luz toma o olho inteiro. Pintar o miolo
    # mais claro que a volta deixava um pontinho dourado no lugar do olho,
    # que e o que fazia o goblin parecer de oculos em vez de iluminado.
    # So o olho acende — NADA de luz derramada na pele em volta. O halo
    # alargava o dourado para os lados e os dois olhos viravam um par de
    # barras, que e o que dava cara de oculos.
    # Branco liso e SEM pupila: o olho fica vazio, que e o que da o ar de
    # possuido. Em dourado com o miolo mais claro ele virava um par de
    # pecinhas de metal pregadas no rosto.
    _head_paint(buf, ctx, OLHO_E + OLHO_D, '*',
                over_outline=True, sobre_olhos=True)
    # Nada de brilho espalhado na pele: os pingos claros entre um olho e
    # o outro emendavam os dois numa faixa branca so, atravessada na cara.
    # So a sombra de baixo, para o branco assentar na orbita.
    _head_paint(buf, ctx, [(16, 15), (17, 15), (18, 15),
                           (25, 15), (26, 15)], 'e')


def t_dark_veins(buf, ctx):
    """Veias amaldicoadas: grossas, subindo da testa para o alto do cranio."""
    # As veias ficam DENTRO do cranio (linhas 7..11). Quando subiam ate a
    # linha 5 elas saiam pelo alto da cabeca e viravam antenas roxas.
    esq = [(15, 8), (15, 9), (16, 9), (16, 10), (16, 11),
           (14, 10), (13, 11), (18, 10), (19, 11)]
    dir_ = [(27, 8), (27, 9), (26, 9), (26, 10), (26, 11),
            (28, 10), (29, 11), (24, 10), (23, 11)]
    _head_paint(buf, ctx, esq + dir_, 'v')
    _head_paint(buf, ctx, [(15, 9), (26, 10), (16, 10), (27, 9)], 'P')


def t_dirt(buf, ctx):
    """Encardido: barro borrado na cara, no queixo e nos dois bracos."""
    # Borroes esparsos na testa e no queixo. Preenchendo as bochechas
    # inteiras ficava parecendo barba, nao sujeira.
    # Sujeira e PELICULA, nao pingos. Pontinhos marrons escuros soltos
    # pela cara viravam cascalho (ou barba por fazer); agora sao borroes
    # conectados num marrom claro que so embaca a pele, com o nucleo
    # escuro apenas no meio de cada borrao.
    testa = [(x, 10) for x in range(12, 18)] + [(x, 11) for x in range(13, 17)]
    face_e = [(10, 15), (11, 15), (10, 16), (11, 16), (12, 16), (11, 17)]
    face_d = [(24, 15), (24, 16), (25, 16), (26, 16), (25, 17), (26, 17)]
    queixo = [(x, 19) for x in range(15, 22)] + [(16, 18), (17, 18)]
    _head_paint(buf, ctx, testa + face_e + face_d + queixo, 'h')
    _head_paint(buf, ctx, [(14, 10), (15, 10), (11, 16), (25, 16),
                           (17, 19), (18, 19)], 'c')
    _head_paint(buf, ctx, [(15, 11), (11, 17), (25, 17)], 'B')
    t_grime(buf, ctx)
    _arm_paint(buf, ctx, 'arm_l', range(7, 11), 'c', cols=range(1, 7))
    _arm_paint(buf, ctx, 'arm_r', range(8, 12), 'c', cols=range(2, 7))


# Tracos que SAO o olho: so eles podem pintar sobre a esclera.
OLHO_PROPRIO = ('eyepatch', 'blind_eye', 'ruby_eye', 'glow_eyes')

# ------------------------------------------------------- roupa gasta ----
# O macacao de couro e a peca mais larga do sprite e estava igual nos 45.
# Estes quatro tracos vivem SO nele (e nas botas), entao combinam com
# qualquer marca de rosto sem disputar espaco com ela.

def t_torn(buf, ctx):
    """Cortes no couro: talho escuro com o labio claro virado para cima."""
    # talho grande, em diagonal, no peito do macacao
    talho = [(6, 11), (6, 12), (7, 12), (7, 13), (8, 13), (8, 14), (9, 14)]
    _part_paint(buf, ctx, 'torso', talho, 'K', over_outline=True)
    _part_paint(buf, ctx, 'torso', [(x, y - 1) for x, y in talho], 'h')
    # segundo corte, menor, do outro lado
    talho2 = [(18, 13), (18, 14), (19, 14), (19, 15)]
    _part_paint(buf, ctx, 'torso', talho2, 'K', over_outline=True)
    _part_paint(buf, ctx, 'torso', [(17, 13), (18, 15)], 'h')
    # canto da bainha levantado, deixando ver a perna
    _part_paint(buf, ctx, 'torso', [(3, 16), (4, 16), (3, 15)], 'K',
                over_outline=True)


def t_frayed(buf, ctx):
    """Fiapos soltos pendurados na bainha e na alca do macacao."""
    for col, fundo in ((3, 2), (6, 3), (20, 2), (23, 3)):
        fios = [(col, 17 + i) for i in range(fundo)]
        _part_paint(buf, ctx, 'torso', fios, 'b', add=True,
                    over_outline=True)
        _part_paint(buf, ctx, 'torso', [(col, 17 + fundo)], 'B', add=True,
                    over_outline=True)
    # bainha desfiada: dentes de serra na borda de baixo
    _part_paint(buf, ctx, 'torso', [(2, 16), (5, 16), (8, 16),
                                    (19, 16), (22, 16)], 'B')
    # fio solto na alca do ombro
    _part_paint(buf, ctx, 'torso', [(20, 3), (21, 4), (21, 5)], 'b',
                add=True, over_outline=True)


def t_patched(buf, ctx):
    """Remendo de couro mais claro, costurado com pontos escuros."""
    remendo = [(x, y) for y in (12, 13, 14) for x in range(14, 19)]
    _part_paint(buf, ctx, 'torso', remendo, 'h')
    _part_paint(buf, ctx, 'torso', [(15, 12), (16, 12)], 'z')     # luz
    # costura em volta
    _part_paint(buf, ctx, 'torso', [(14, 11), (16, 11), (18, 11),
                                    (13, 13), (19, 13),
                                    (14, 15), (16, 15), (18, 15)], 'B')
    # remendo menor na perna
    _part_paint(buf, ctx, 'leg_r', [(4, 4), (5, 4), (6, 4),
                                    (4, 5), (5, 5), (6, 5)], 'h')
    _part_paint(buf, ctx, 'leg_r', [(3, 4), (7, 5)], 'B')


def t_grime(buf, ctx):
    """Barro seco no macacao e nas botas."""
    _part_paint(buf, ctx, 'torso', [(x, 15) for x in range(3, 9)]
                + [(x, 16) for x in range(2, 10)]
                + [(x, 16) for x in range(16, 23)]
                + [(10, 19), (11, 19), (12, 19), (13, 20)], 'B')
    _part_paint(buf, ctx, 'torso', [(4, 16), (7, 16), (18, 16)], 'c')
    for perna in ('leg_l', 'leg_r'):
        _part_paint(buf, ctx, perna, [(x, 5) for x in range(1, 9)]
                    + [(2, 4), (5, 4), (7, 4)], 'B')


def t_ear_holes(buf, ctx):
    """Orelhas furadas: pequenos furos escuros, com a borda levantada."""
    furos = [(4, 6), (7, 5), (6, 7), (30, 4), (32, 6), (29, 7)]
    _head_paint(buf, ctx, furos, 'k', over_outline=True)
    # o anel de pele levantada em volta do furo e o que o faz ler como
    # buraco, e nao como sujeira
    _head_paint(buf, ctx, [(x + 1, y) for x, y in furos], 'l')
    _head_paint(buf, ctx, [(x, y - 1) for x, y in furos], 'e')


def t_ear_nick(buf, ctx):
    """Orelha cortada: um pedaco FALTANDO na borda, com o coto escuro.

    O corte apaga pixels de verdade (ch=None). Um risco escuro pintado em
    cima da orelha seria so uma linha; tirando o pedaco, a silhueta muda
    e o corte se ve mesmo pequeno.
    """
    # mordida na borda de cima da orelha direita
    _head_paint(buf, ctx, [(30, 3), (31, 3), (30, 4), (31, 4), (31, 5)],
                None, over_outline=True)
    _head_paint(buf, ctx, [(29, 3), (29, 4), (30, 5), (32, 5), (31, 6)],
                'k', over_outline=True)
    # talho menor na ponta da orelha esquerda
    _head_paint(buf, ctx, [(3, 5), (4, 5)], None, over_outline=True)
    _head_paint(buf, ctx, [(2, 5), (3, 6), (4, 6), (5, 5)], 'k',
                over_outline=True)


DETAILS = {
    'ear_holes': t_ear_holes, 'ear_nick': t_ear_nick,
    'torn': t_torn, 'frayed': t_frayed, 'patched': t_patched,
    'grime': t_grime,
    'gold_tooth': t_gold_tooth, 'eyepatch': t_eyepatch, 'ear_ring': t_ear_ring,
    'earring': t_earring, 'scar': t_scar, 'burns': t_burns, 'bandana': t_bandana,
    'arm_bandage': t_arm_bandage, 'birthmark': t_birthmark,
    'head_bandage': t_head_bandage, 'blind_eye': t_blind_eye,
    'hand_wrap': t_hand_wrap,
    'ruby_eye': t_ruby_eye, 'wart': t_wart, 'freckles': t_freckles,
    'tattoo': t_tattoo, 'double_fangs': t_double_fangs, 'glow_eyes': t_glow_eyes,
    'dark_veins': t_dark_veins, 'dirt': t_dirt,
}

SWAPS = {
    # Trocas de paleta: respeitam os 8 tons de pele do original, entao o
    # volume do desenho continua la — muda so a matiz.
    # O contorno NAO vira pele. Antes 'k' virava rosa junto com o resto e o
    # goblin perdia a silhueta inteira — ficava um borrao. Agora a linha de
    # contorno so esquenta de tom e continua sendo a mais escura do desenho.
    # O contorno 'k' NAO entra na troca: alem de segurar a silhueta, ele
    # e a linha do macacao de couro. Quando virava marrom claro, o macacao
    # desbotava junto com a pele e o goblin ficava rosa inteiro — nos
    # sprites antigos o albino sempre manteve o couro marrom.
    'albino': {'k': 'U', 'e': 'F', 'd': 'E', 'n': 'C', 'j': 'A',
               'g': 'H', 'l': 'a', 'f': 'w'},
    # 'f' fica de fora: e o branco do olho. Escurecido junto com a pele, o
    # olho ficava verde e a pupila sumia dentro dele.
    'grizzled': {'l': 'g', 'g': 'j', 'j': 'n', 'n': 'd', 'd': 'e'},
    # Encardido: a pele inteira perde um tom e o couro escurece, senao a
    # variacao ficava igual ao goblin limpo.
    'sooty': {'l': 'j', 'g': 'j', 'j': 'n', 'n': 'd',
              'h': 'b', 'b': 'B', 'q': 'z', 'z': 'h'},
}


# Onde a orelha direita comeca em cada linha da cabeca. Os valores saem do
# proprio desenho (a coluna escura que separa cranio e orelha), por isso o
# corte tira a orelha inteira sem comer o cranio.
EAR_R_CUT = {0: 23, 1: 23, 2: 23, 3: 23, 4: 24, 5: 24, 6: 25, 7: 27, 8: 27, 9: 27}


def _head_without_right_ear():
    head = copy.deepcopy(R.HEAD)
    w = len(head[0])
    for y, cut in EAR_R_CUT.items():
        for x in range(cut, w):
            head[y][x] = '.'
        if head[y][cut - 1] != '.':   # fecha o coto com contorno escuro
            head[y][cut - 1] = 'k'
    return head


PARTS = {
    'missing_ear': lambda: {'head': _head_without_right_ear()},
}

# ------------------------------------------------------------- receitas ----
# Mesma ordem e mesmos ids que js/goblin.js espera.
RECIPES = {
    '01_dente_dourado':        ['gold_tooth', 'frayed', 'ear_holes'],
    '02_tapa_olho':            ['eyepatch'],
    '04_orelha_furada':        ['ear_ring', 'patched'],
    '07_cicatriz':             ['scar', 'torn'],
    '08_albinismo':            ['albino'],
    '09_queimaduras':          ['burns', 'torn', 'ear_nick'],
    '10_corsario':             ['bandana', 'eyepatch'],
    '13_sobrevivente':         ['scar', 'arm_bandage', 'hand_wrap',
                                'frayed', 'ear_nick'],
    '14_anel':                 ['earring', 'patched'],
    '15_marca_de_nascenca':    ['birthmark', 'grime'],
    '16_sem_orelha':           ['missing_ear', 'torn', 'frayed'],
    '17_enfaixado':            ['head_bandage'],
    '18_ileso':                [],
    '19_olho_cego':            ['blind_eye', 'patched', 'ear_holes'],
    '20_verruga':              ['wart', 'grime'],
    '21_sardas':               ['freckles', 'frayed', 'ear_holes'],
    '22_tatuagem_facial':      ['tattoo', 'torn'],
    '23_presas_duplas':        ['double_fangs', 'torn', 'ear_nick'],
    '24_olho_rubi':            ['ruby_eye', 'patched'],
    '26_veterano':             ['scar', 'grizzled', 'frayed',
                                'patched', 'ear_nick'],
    '27_queimado_enfaixado':   ['burns', 'head_bandage', 'torn', 'grime'],
    '28_albino_rubi':          ['albino', 'ruby_eye', 'earring'],
    '29_guerreiro_marcado':    ['scar', 'tattoo', 'patched', 'ear_holes'],
    '30_sobrevivente_ferido':  ['scar', 'arm_bandage', 'blind_eye',
                                'hand_wrap', 'frayed'],
    '31_mistico':              ['tattoo', 'glow_eyes', 'patched'],
    '32_brigao':               ['missing_ear', 'scar', 'torn', 'ear_nick'],
    '33_amaldicoado':          ['birthmark', 'dark_veins', 'grime'],
    '34_sardento':             ['freckles', 'wart', 'frayed', 'ear_holes'],
    '35_cacador_marcado':      ['tattoo', 'earring', 'patched', 'ear_holes'],
    '36_pirata_queimado':      ['bandana', 'eyepatch', 'burns',
                                'torn', 'frayed'],
    '37_albino_cicatrizado':   ['albino', 'scar'],
    '38_guerreiro_enfaixado':  ['head_bandage', 'arm_bandage', 'scar',
                                'hand_wrap', 'patched'],
    # o rubi vem DEPOIS do brilho: um olho fica dourado e o outro
    # vermelho, senao o oraculo saia identico ao mistico
    '39_oraculo_rubi':         ['tattoo', 'glow_eyes', 'ruby_eye'],
    '40_presas_douradas':      ['double_fangs', 'gold_tooth',
                                'patched', 'ear_holes'],
    '41_veterano_enfaixado':   ['scar', 'grizzled', 'head_bandage',
                                'hand_wrap', 'frayed', 'grime'],
    '42_queimado_tatuado':     ['burns', 'tattoo', 'torn', 'ear_nick'],
    '43_albino_sardento':      ['albino', 'freckles'],
    '44_brigao_cego':          ['missing_ear', 'blind_eye', 'torn',
                                'frayed', 'ear_nick'],
    '45_fanatico':             ['tattoo', 'glow_eyes', 'head_bandage',
                                'hand_wrap'],
    '46_marcado_rubi':         ['birthmark', 'ruby_eye',
                                'grime', 'ear_holes'],
    '47_sobrevivente_sujo':    ['arm_bandage', 'dirt', 'sooty',
                                'hand_wrap'],
    '48_corsario_tatuado':     ['bandana', 'eyepatch', 'tattoo', 'torn'],
    '49_guerreiro_dourado':    ['gold_tooth', 'earring', 'scar',
                                'patched', 'ear_holes'],
    '50_amaldicoado_enfaixado': ['birthmark', 'dark_veins',
                                 'head_bandage', 'grime'],
    '51_mutilado':             ['missing_ear', 'blind_eye', 'scar',
                                'burns', 'torn', 'frayed'],
}

ORDER = list(RECIPES)
assert len(ORDER) == 45, len(ORDER)


# O branco do olho e o tom 'f' da propria arte. As trocas de paleta que
# escurecem a pele (grizzled, sooty) tambem pegavam esse 'f' e o olho do
# goblin ficava com o fundo VERDE, sem contraste com a pupila. O branco do
# olho nao e pele: ele nao acompanha a troca.
SCLERA = R.FACE_CELLS['eye_l'] + R.FACE_CELLS['eye_r']
# ordem de preferencia: o tom original primeiro; se a troca mexer nele,
# cai para o proximo claro que a troca NAO toca (senao o swap final, que
# roda depois dos detalhes, escureceria o olho de novo)
SCLERA_TONS = ('f', 'q', 'W', 'w')


def _sclera_livre(swap):
    """Primeiro tom claro que a troca de paleta nao altera."""
    for ch in SCLERA_TONS:
        if ch not in swap:
            return ch
    return 'w'


def t_eye_white(ch):
    """Devolve um detalhe que repinta o branco dos dois olhos com `ch`."""
    def aplicar(buf, ctx):
        _head_paint(buf, ctx, SCLERA, ch, over_outline=True, sobre_olhos=True)
    return aplicar


def build(variation_id):
    """Converte a receita no dicionario que goblin_anim.render_action espera."""
    traits = RECIPES[variation_id]
    swap, parts, details = {}, {}, []
    olho_coberto = False
    for t in traits:
        if t in SWAPS:
            swap.update(SWAPS[t])
        elif t in PARTS:
            parts.update(PARTS[t]())
        elif t in DETAILS:
            details.append(DETAILS[t])
            olho_coberto = olho_coberto or t in OLHO_PROPRIO
        else:
            raise KeyError(f'traco desconhecido: {t} ({variation_id})')

    # Se a troca de paleta mexeu no branco do olho, devolve o branco. Vai
    # na FRENTE dos detalhes de olho (tapa-olho, rubi, cego, acesos), que
    # tem o direito de pintar por cima.
    if 'f' in swap and not olho_coberto:
        details.insert(0, t_eye_white(_sclera_livre(swap)))

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
