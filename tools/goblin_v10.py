#!/usr/bin/env python3
"""O V10 ENCOURACADO, maior e com mais pixels de verdade.

De onde ele vem
---------------
O v10 que voce escolheu era o quadro original dobrado (cada pixel
virava um bloco 2x2) com as placas de metal por cima. Ou seja: ele
tinha o tamanho de 64, mas a QUANTIDADE DE PIXELS do original — 2x2
iguais nao sao dois pixels de informacao, sao um so, gordo.

Aqui o goblin passa a ter pixel de verdade:

  1. SCALE3X em cima do quadro original. Nao e um "resize": e o
     algoritmo de pixel art que olha os oito vizinhos e so arredonda
     onde existe uma diagonal, deixando reto o que era reto. Uma
     orelha que subia em escada de degrau gordo passa a subir em
     degrau fino. Sao 9 pixels no lugar de 1, e a silhueta nao muda.
  2. O bicho fica MAIOR: ocupa ~42x48 do quadro de 64, contra 28x32
     de antes.
  3. Os acabamentos sao redesenhados nessa grade fina — no 2x eles
     tinham que ter meio bloco de espessura; aqui tem um terco, que
     e o que deixa a sombra parecer sombra e nao uma faixa.

O que nao muda e o movimento: cada quadro continua derivado do
quadro correspondente de `art-source/goblins-originais/`, e todo
tratamento depende so do quadro, nunca da posicao dele na sequencia.
Por isso a animacao segue fluida.

    python3 tools/goblin_v10.py        # folha + gif de conferencia
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goblin_v3 as V  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'art-source', 'goblin-v3')

LADO = 64            # o quadro do pipeline
CHAO = 62            # onde os pes encostam dentro do quadro

# Caixa que a animacao INTEIRA ocupa depois do scale3x, medida nos 62
# quadros de uma vez: x 18..75, y 39..96 (57x57 numa tela de 96).
# Dai sai o deslocamento fixo que centra o bicho e poe os pes no
# chao do quadro de 64. Esta medida nao muda, por isso e constante.
UNIAO = (18, 39, 75, 96)
ANCORA = (LADO // 2 - (UNIAO[0] + UNIAO[2]) // 2, CHAO - UNIAO[3])

# ----------------------------------------------------------- as cores
# Inspiradas no original, nao copiadas dele: a pele ganhou um tom a
# mais em cada ponta e o metal e novo.
CONTORNO = (18, 20, 22, 255)
PELE = [(30, 78, 48, 255),      # 0 sombra funda
        (52, 120, 72, 255),     # 1 sombra
        (70, 150, 92, 255),     # 2 base
        (102, 182, 120, 255),   # 3 luz
        (142, 212, 158, 255)]   # 4 brilho
METAL = [(58, 64, 72, 255),     # 0 sombra funda
         (92, 98, 108, 255),    # 1 sombra
         (126, 132, 140, 255),  # 2 base
         (176, 182, 190, 255),  # 3 luz
         (222, 226, 232, 255)]  # 4 brilho
COURO = [(52, 34, 22, 255), (82, 54, 34, 255), (118, 82, 54, 255)]
OLHO = (238, 242, 252, 255)
PUPILA = (26, 34, 40, 255)
PRESA = (232, 236, 196, 255)

VAZIO = (0, 0, 0, 0)


# ------------------------------------------------------------ scale3x
def scale3x(origem):
    """Triplica no estilo pixel art (AdvMAME3x/EPX).

    A regra: um pixel so se divide quando os vizinhos indicam uma
    DIAGONAL. Em area chapada e em linha reta nada muda — por isso a
    silhueta continua a mesma e nada fica borrado, ao contrario de um
    redimensionamento comum, que inventaria tons intermediarios.
    """
    larg, alt = origem.size
    px = origem.load()
    destino = Image.new('RGBA', (larg * 3, alt * 3), VAZIO)
    dp = destino.load()

    def em(x, y):
        x = min(max(x, 0), larg - 1)
        y = min(max(y, 0), alt - 1)
        return px[x, y]

    for y in range(alt):
        for x in range(larg):
            e = em(x, y)
            a, b, c = em(x - 1, y - 1), em(x, y - 1), em(x + 1, y - 1)
            d, f = em(x - 1, y), em(x + 1, y)
            g, h, i = em(x - 1, y + 1), em(x, y + 1), em(x + 1, y + 1)
            if b != h and d != f:
                e0 = d if d == b else e
                e1 = b if (d == b and e != c) or (b == f and e != a) else e
                e2 = f if b == f else e
                e3 = d if (d == b and e != g) or (d == h and e != a) else e
                e4 = e
                e5 = f if (b == f and e != i) or (h == f and e != c) else e
                e6 = d if d == h else e
                e7 = h if (d == h and e != i) or (h == f and e != g) else e
                e8 = f if h == f else e
            else:
                e0 = e1 = e2 = e3 = e4 = e5 = e6 = e7 = e8 = e
            for k, cor in enumerate((e0, e1, e2, e3, e4, e5, e6, e7, e8)):
                dp[x * 3 + k % 3, y * 3 + k // 3] = cor
    return destino


# ------------------------------------------------------- base do v10
def _sem_arma(im):
    px, larg, alt = im.load(), im.size[0], im.size[1]
    for y in range(alt):
        for x in range(larg):
            if px[x, y] == V.ACO:
                px[x, y] = VAZIO
    return im


def base(acao, i):
    """Quadro original -> scale3x -> encaixado no quadro de 64.

    O encaixe usa um deslocamento FIXO, nunca a caixa do quadro. Os
    62 quadros originais ja estao alinhados entre si dentro do seu
    quadro de 32; recortar cada um pela propria caixa jogaria o
    goblin para os lados sempre que um braco esticasse — a animacao
    pareceria escorregar. Com deslocamento fixo, o movimento
    relativo entre os quadros e exatamente o do original.
    """
    grande = scale3x(_sem_arma(V._carrega(acao, i).copy()))
    quadro = Image.new('RGBA', (LADO, LADO), VAZIO)
    quadro.alpha_composite(grande, ANCORA)
    return quadro


# ------------------------------------------------- mapa de materiais
def _classifica(im):
    """Diz, para cada pixel, de que material ele e.

    O original so tem dez cores, entao da para saber pelo valor: os
    verdes sao pele, os marrons sao a roupa (que aqui vira placa), o
    branco e olho, o creme e presa.
    """
    px, larg, alt = im.load(), im.size[0], im.size[1]
    mapa = [[None] * larg for _ in range(alt)]
    for y in range(alt):
        for x in range(larg):
            c = px[x, y]
            if c[3] == 0:
                continue
            if c == V.CONTORNO:
                mapa[y][x] = 'contorno'
            elif c in V.PELE:
                mapa[y][x] = 'pele'
            elif c in V.PANO:
                mapa[y][x] = 'metal'
            elif c == V.OLHO:
                mapa[y][x] = 'olho'
            elif c == V.PRESA:
                mapa[y][x] = 'presa'
    return mapa, px, larg, alt


def _nivel_original(c, rampa):
    """Qual degrau da rampa nova corresponde ao tom antigo."""
    return rampa.index(c) if c in rampa else 1


def pinta(im):
    """Troca as cores do original pelas rampas novas, mais longas."""
    mapa, px, larg, alt = _classifica(im)
    for y in range(alt):
        for x in range(larg):
            m = mapa[y][x]
            if m is None:
                continue
            c = px[x, y]
            if m == 'contorno':
                px[x, y] = CONTORNO
            elif m == 'pele':
                px[x, y] = PELE[1 + _nivel_original(c, list(V.PELE))]
            elif m == 'metal':
                px[x, y] = METAL[_nivel_original(c, list(V.PANO))]
            elif m == 'olho':
                px[x, y] = OLHO
            elif m == 'presa':
                px[x, y] = PRESA
    return im


def _rampa_de(c):
    for rampa in (PELE, METAL, COURO):
        if c in rampa:
            return rampa
    return None


def _desloca(px, x, y, rampa, passo):
    i = rampa.index(px[x, y])
    px[x, y] = rampa[min(max(i + passo, 0), len(rampa) - 1)]


def volume(im):
    """Luz em cima e a esquerda, sombra embaixo e a direita.

    Na grade fina isto tem UM terco da espessura do pixel velho: e a
    diferenca entre uma sombra e uma tarja.
    """
    px, larg, alt = im.load(), im.size[0], im.size[1]
    base_px = [[px[x, y] for x in range(larg)] for y in range(alt)]

    def fora(x, y):
        return (not (0 <= x < larg and 0 <= y < alt)
                or base_px[y][x][3] == 0
                or base_px[y][x] == CONTORNO)

    for y in range(alt):
        for x in range(larg):
            rampa = _rampa_de(base_px[y][x])
            if rampa is None:
                continue
            sombra = fora(x, y + 1) or fora(x + 1, y)
            luz = fora(x, y - 1) or fora(x - 1, y)
            if sombra and luz:
                continue    # parte fina: escurecer E clarear so sujaria
            if sombra:
                _desloca(px, x, y, rampa, -1)
            elif luz:
                _desloca(px, x, y, rampa, +1)
    return im


def separa_materiais(im):
    """Linha de sombra onde a pele encosta no metal.

    Sem isso braco, peito e placa viram uma mancha so quando o sprite
    encolhe na tela.
    """
    mapa, px, larg, alt = _classifica(im)
    marca = []
    for y in range(alt):
        for x in range(larg):
            if mapa[y][x] != 'pele':
                continue
            if any(0 <= x + dx < larg and 0 <= y + dy < alt
                   and mapa[y + dy][x + dx] == 'metal'
                   for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))):
                marca.append((x, y))
    for x, y in marca:
        rampa = _rampa_de(px[x, y])
        if rampa:
            _desloca(px, x, y, rampa, -2)
    return im


def placas(im):
    """Acabamento da armadura: aresta clara em cima, breu embaixo.

    E o que faz o metal parecer chapa e nao pano pintado de cinza.
    """
    mapa, px, larg, alt = _classifica(im)
    topo, fundo = [], []
    for y in range(alt):
        for x in range(larg):
            if mapa[y][x] != 'metal':
                continue
            if y == 0 or mapa[y - 1][x] != 'metal':
                topo.append((x, y))
            if y + 1 >= alt or mapa[y + 1][x] != 'metal':
                fundo.append((x, y))
    for x, y in topo:
        px[x, y] = METAL[4]
    for x, y in fundo:
        px[x, y] = METAL[0]
    return im


def olhos(im):
    """Pupila e reflexo. No 2x nao cabia: o olho tinha 2x2.

    Com 3x o olho tem area para branco, pupila e um brilho de um
    pixel — e e o brilho que da vida para a cara.
    """
    mapa, px, larg, alt = _classifica(im)
    cels = [(x, y) for y in range(alt) for x in range(larg)
            if mapa[y][x] == 'olho']
    if not cels:
        return im
    olho = set(cels)
    for x, y in cels:
        # So o canto de baixo e da frente. Escurecer a fileira
        # inteira (primeira tentativa) dava cara de olho fechado.
        if (x, y + 1) not in olho and (x + 1, y) not in olho:
            px[x, y] = PUPILA
    for x, y in cels:
        if (x - 1, y) not in cels and (x, y - 1) not in cels:
            px[x, y] = (255, 255, 255, 255)
    return im


def contorno_externo(im):
    """Fecha a silhueta com uma linha escura de 1 px.

    Com o sprite maior, sem isso ele encosta no cenario e some.
    """
    px, larg, alt = im.load(), im.size[0], im.size[1]
    borda = [(x, y) for y in range(alt) for x in range(larg)
             if px[x, y][3] == 0
             and any(0 <= x + dx < larg and 0 <= y + dy < alt
                     and px[x + dx, y + dy][3] != 0
                     for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in borda:
        px[x, y] = CONTORNO
    return im


PASSES = (pinta, volume, separa_materiais, placas, olhos, contorno_externo)


def quadro(acao, i):
    im = base(acao, i)
    for passe in PASSES:
        im = passe(im)
    return im


# ------------------------------------------------------- conferencia
def main():
    os.makedirs(SAIDA, exist_ok=True)
    import goblin_versoes as W

    Z, lado = 5, 64 * 5
    tira = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
    paginas = []
    for i in range(17):
        pag = Image.new('RGBA', (len(tira) * lado, 2 * lado), (26, 28, 24, 255))
        for col, (acao, n) in enumerate(tira):
            velho = W.v10_encouracado(acao, i % n)
            novo = quadro(acao, i % n)
            pag.alpha_composite(velho.resize((lado, lado), Image.NEAREST),
                                (col * lado, 0))
            pag.alpha_composite(novo.resize((lado, lado), Image.NEAREST),
                                (col * lado, lado))
        paginas.append(pag.convert('RGB').convert('P', palette=Image.ADAPTIVE,
                                                  colors=96))
    destino = os.path.join(SAIDA, 'v10-maior.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    print(destino, os.path.getsize(destino) // 1024, 'kB')

    # Lado a lado parado, bem grande, para ver pixel por pixel.
    Z = 9
    folha = Image.new('RGBA', (2 * 64 * Z, 64 * Z), (26, 28, 24, 255))
    folha.alpha_composite(W.v10_encouracado('idle', 0).resize(
        (64 * Z, 64 * Z), Image.NEAREST), (0, 0))
    folha.alpha_composite(quadro('idle', 0).resize(
        (64 * Z, 64 * Z), Image.NEAREST), (64 * Z, 0))
    folha.save(os.path.join(SAIDA, 'v10-maior-parado.png'))


if __name__ == '__main__':
    main()
