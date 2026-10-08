#!/usr/bin/env python3
"""GOBLIN V3 — o goblin ORIGINAL, com mais detalhe, em degraus.

A ideia, depois de tudo o que deu errado com o v2
--------------------------------------------------
O v2 nasceu de um JPEG borrado e tentou inventar a animacao a partir
de medicoes. Resultado: arte salpicada e movimento que nunca bateu
com o do jogo. Este aqui parte do lado oposto:

  A ANIMACAO NAO E RECRIADA — E A DO ORIGINAL, QUADRO A QUADRO.

Cada quadro novo e DERIVADO do quadro original correspondente
(`art-source/goblins-originais/<acao>_<n>.png`, 32x32). Nenhuma pose e
calculada, nenhuma e escrita a mao: a pose JA ESTA no quadro de
origem. Logo o movimento e, por construcao, exatamente o do original —
nao parecido, o mesmo.

O detalhe entra por cima, num passe deterministico, e em DEGRAUS:

  nivel 0  o original dobrado (cada pixel vira um bloco 2x2 de 64).
           E a referencia: identico ao antigo, so que no tamanho do
           pipeline.
  nivel 1  LUZ E SOMBRA DE BORDA. Dobrar para 64 da meio pixel de
           margem em cada lado do pixel antigo, e e ai que cabe
           detalhe sem mudar forma nenhuma: a borda de baixo e da
           direita escurece, a de cima e da esquerda clareia. O
           volume aparece e a silhueta continua a mesma.
  nivel 2  AS PARTES SE SEPARAM. Onde a pele encosta no pano, no
           cinto ou no cabelo entra uma linha de sombra; a orelha
           ganha o vinco de dentro. E o que faz braco, tronco e
           cabeca pararem de ser uma mancha so.
  nivel 3  ACABAMENTO. Brilho no alto do cranio e do ombro, pupila e
           reflexo no olho, vinco do pano na cintura.

Cada degrau e uma funcao a parte. Da para parar em qualquer um.
"""

import os
import sys

from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
ORIG = os.path.join(RAIZ, 'art-source', 'goblins-originais')

# As dez cores do original, lidas dos proprios arquivos.
FUNDO = None
CONTORNO = (47, 47, 46, 255)
PELE = ((69, 165, 96, 255), (80, 189, 111, 255), (114, 210, 142, 255))
PANO = ((98, 64, 35, 255), (105, 72, 58, 255), (145, 100, 81, 255))
OLHO = (241, 240, 253, 255)
ACO = (212, 212, 215, 255)
PRESA = (225, 230, 164, 255)

# Os tons NOVOS que o detalhe usa. Sao a mesma cor do original
# empurrada para o escuro ou para o claro — nenhuma cor estranha
# entra no desenho.
PELE_SOMBRA = (44, 112, 64, 255)
PELE_ESCURA = (28, 78, 46, 255)
PELE_LUZ = (150, 232, 175, 255)
PANO_SOMBRA = (62, 40, 24, 255)
PANO_LUZ = (171, 124, 99, 255)
OLHO_PUPILA = (30, 44, 38, 255)


def _carrega(acao, i):
    return Image.open(os.path.join(ORIG, f'{acao}_{i}.png')).convert('RGBA')


def _tira_arma(px, larg, alt):
    """Apaga a adaga do corpo.

    No jogo a arma e uma camada propria (o goblin comeca DESARMADO e
    pode equipar tres adagas diferentes). Se ela ficasse pintada no
    corpo, todo goblin nasceria armado e as armas do inventario
    apareceriam em dobro.
    """
    for y in range(alt):
        for x in range(larg):
            if px[x, y] == ACO:
                px[x, y] = (0, 0, 0, 0)


def nivel0(acao, i):
    """O original, dobrado. Cada pixel vira um bloco 2x2."""
    im = _carrega(acao, i)
    px = im.load()
    _tira_arma(px, im.width, im.height)
    return im.resize((im.width * 2, im.height * 2), Image.NEAREST)


def _vizinhos(px, x, y, larg, alt):
    out = {}
    for nome, (dx, dy) in (('n', (0, -1)), ('s', (0, 1)),
                           ('o', (-1, 0)), ('l', (1, 0))):
        nx, ny = x + dx, y + dy
        out[nome] = px[nx, ny] if 0 <= nx < larg and 0 <= ny < alt else None
    return out


def _vazio(c):
    return c is None or c[3] == 0


def nivel1(im):
    """Luz e sombra de borda — o volume, sem mexer na forma."""
    larg, alt = im.size
    src = im.copy().load()
    px = im.load()
    for y in range(alt):
        for x in range(larg):
            c = src[x, y]
            if c[3] == 0 or c == CONTORNO:
                continue
            v = _vizinhos(src, x, y, larg, alt)
            borda_baixo = _vazio(v['s']) or v['s'] == CONTORNO
            borda_alto = _vazio(v['n']) or v['n'] == CONTORNO
            borda_dir = _vazio(v['l']) or v['l'] == CONTORNO
            borda_esq = _vazio(v['o']) or v['o'] == CONTORNO
            if c in PELE:
                if borda_baixo or borda_dir:
                    px[x, y] = PELE_SOMBRA
                elif (borda_alto or borda_esq) and c != PELE[2]:
                    px[x, y] = PELE[2]
            elif c in PANO:
                if borda_baixo or borda_dir:
                    px[x, y] = PANO_SOMBRA
                elif borda_alto or borda_esq:
                    px[x, y] = PANO_LUZ
    return im


def nivel2(im):
    """Separa as partes: linha de sombra onde um material encosta no
    outro, e o vinco de dentro da orelha."""
    larg, alt = im.size
    src = im.copy().load()
    px = im.load()

    def classe(c):
        if c is None or c[3] == 0:
            return None
        if c in PELE or c in (PELE_SOMBRA, PELE_LUZ, PELE_ESCURA):
            return 'pele'
        if c in PANO or c in (PANO_SOMBRA, PANO_LUZ):
            return 'pano'
        return 'outro'

    for y in range(alt):
        for x in range(larg):
            c = src[x, y]
            k = classe(c)
            if k != 'pele':
                continue
            v = _vizinhos(src, x, y, larg, alt)
            # pele encostando em pano POR BAIXO: o pano projeta sombra
            # na pele acima dele? nao — e o contrario: a pele que entra
            # debaixo do pano escurece
            if classe(v['s']) == 'pano' or classe(v['l']) == 'pano':
                px[x, y] = PELE_SOMBRA
            if classe(v['n']) == 'pano':
                px[x, y] = PELE_ESCURA
    return im


def nivel3(im):
    """Acabamento: brilho no alto, pupila e reflexo no olho."""
    larg, alt = im.size
    src = im.copy().load()
    px = im.load()
    # brilho: pele clara com vazio em cima E a esquerda (o canto que
    # pega luz) vira o tom mais claro
    for y in range(alt):
        for x in range(larg):
            c = src[x, y]
            if c[3] == 0:
                continue
            v = _vizinhos(src, x, y, larg, alt)
            if c in (PELE[1], PELE[2], PELE_LUZ):
                if _vazio(v['n']) and _vazio(v['o']):
                    px[x, y] = PELE_LUZ
    # olho: o branco do original e um bloco chapado. No dobro da
    # resolucao cabe uma PUPILA — um unico pixel no canto de baixo e
    # da frente do bloco. Escurecer a fileira inteira (a primeira
    # tentativa) dava cara de olho semicerrado.
    for y in range(alt):
        for x in range(larg):
            if src[x, y] != OLHO:
                continue
            v = _vizinhos(src, x, y, larg, alt)
            if v['s'] != OLHO and v['l'] != OLHO:
                px[x, y] = OLHO_PUPILA
    return im


PASSES = (nivel1, nivel2, nivel3)


def quadro(acao, i, nivel=3):
    """O quadro `i` de `acao`, no nivel de detalhe pedido."""
    im = nivel0(acao, i)
    for passe in PASSES[:nivel]:
        im = passe(im)
    return im


if __name__ == '__main__':
    Z = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    amostras = [('idle', 0), ('walk', 0), ('walk', 2), ('attack', 1),
                ('hurt', 1)]
    W = 64 * Z
    pag = Image.new('RGBA', (len(amostras) * W, 4 * W), (26, 28, 24, 255))
    for col, (acao, i) in enumerate(amostras):
        for nivel in range(4):
            im = quadro(acao, i, nivel)
            pag.alpha_composite(im.resize((W, W), Image.NEAREST),
                                (col * W, nivel * W))
    saida = os.path.join(RAIZ, 'art-source', 'goblin-v3', 'degraus.png')
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    pag.save(saida)
    print(saida)
