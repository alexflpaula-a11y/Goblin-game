#!/usr/bin/env python3
"""V12 — afastando o goblin do original pela ANATOMIA, sem equipamento.

O V11 disfarcava o original pondo coisas em cima dele: elmo,
ombreira, crista. Voce pediu o contrario — mudar o BICHO. Entao aqui
nada e vestido: o que muda e orelha, nariz, presa, cranio, ombro,
tronco, perna e garra. O corpo encouracado do V10 que voce escolheu
continua igual (as placas ja faziam parte dele, nao sao adicao).

Tres graus:

  A  SO A CARA. Orelhas compridas em ponta, nariz adunco descendo
     sobre a boca, presas da mandibula de baixo subindo. A cabeca
     e o que o olho reconhece primeiro; mexer nela ja tira o ar de
     copia.
  B  A + PROPORCAO. Cranio mais alto e estreito, ombros mais largos,
     corpo mais baixo. Deixa de ser o bonequinho de 2 cabecas e
     vira um bruto atarracado.
  C  B + CORCUNDA E GARRAS. Costas arqueadas com giba e dedos em
     garra nos pes e nas maos.

A animacao segue sendo a do original, quadro a quadro. Todo passe le
SO o proprio quadro, e os que mudam tamanho ancoram em ponto fixo (o
chao e o meio do quadro) ou no pescoco — nunca na caixa do quadro,
que mudaria de tamanho a cada passo e faria o bicho escorregar.

    python3 tools/goblin_v12.py
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goblin_v10 as T  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'art-source', 'goblin-v3')
VAZIO = (0, 0, 0, 0)


# ------------------------------------------------------------- leitura
def _mapa(im):
    px, larg, alt = im.load(), im.size[0], im.size[1]
    pele, metal = set(T.PELE), set(T.METAL)
    olho = {T.OLHO, T.PUPILA, (255, 255, 255, 255)}
    mapa = [[None] * larg for _ in range(alt)]
    for y in range(alt):
        for x in range(larg):
            c = px[x, y]
            if c[3] == 0:
                continue
            mapa[y][x] = ('pele' if c in pele else
                          'metal' if c in metal else
                          'olho' if c in olho else
                          'presa' if c == T.PRESA else 'contorno')
    return mapa, px, larg, alt


def _olhos(mapa, larg, alt):
    ys = [y for y in range(alt) for x in range(larg) if mapa[y][x] == 'olho']
    return (min(ys), max(ys)) if ys else None


def _corridas(mapa, y, larg, tipo='pele'):
    saida, inicio = [], None
    for x in range(larg + 1):
        dentro = x < larg and mapa[y][x] == tipo
        if dentro and inicio is None:
            inicio = x
        elif not dentro and inicio is not None:
            saida.append((inicio, x - 1))
            inicio = None
    return saida


def _meio_da_cabeca(mapa, larg, topo_olho):
    xs = [x for y in range(max(0, topo_olho - 2), topo_olho + 1)
          for x in range(larg) if mapa[y][x] is not None]
    return (min(xs) + max(xs)) // 2 if xs else None


# ----------------------------------------------------------- A: a cara
def orelhas_compridas(im, puxao=4):
    """Estica a ponta das orelhas para fora e para cima.

    Orelha e o trecho de pele da linha que NAO contem o meio da
    cabeca. A ponta sai em diagonal, um pixel por linha, afinando —
    e assim que uma orelha pontuda se desenha em pixel art; puxar
    reto daria um toco.
    """
    mapa, px, larg, alt = _mapa(im)
    olhos = _olhos(mapa, larg, alt)
    if not olhos:
        return im
    meio = _meio_da_cabeca(mapa, larg, olhos[0])
    if meio is None:
        return im
    pintar = []
    for y in range(0, olhos[0] + 2):
        for (a, b) in _corridas(mapa, y, larg):
            if a - 1 <= meio <= b + 1 or b - a > 8:
                continue
            esquerda = b < meio
            cor = px[a if esquerda else b, y]
            for k in range(1, puxao + 1):
                x = a - k if esquerda else b + k
                yy = y - (k + 1) // 2
                if 0 <= x < larg and 0 <= yy < alt:
                    pintar.append((x, yy, cor))
    for x, y, cor in pintar:
        if px[x, y][3] == 0 or px[x, y] == T.CONTORNO:
            px[x, y] = cor
    return T.contorno_externo(im)


def nariz_adunco(im):
    """Puxa o nariz para a frente e para baixo, em gancho.

    O nariz e a saliencia de pele mais a frente na altura dos
    olhos. Cresce um pixel por linha, entao ele desce curvando em
    vez de virar um bico reto.
    """
    mapa, px, larg, alt = _mapa(im)
    olhos = _olhos(mapa, larg, alt)
    if not olhos:
        return im
    y0, y1 = olhos
    pintar = []
    for n, y in enumerate(range(y1 + 1, min(alt, y1 + 5))):
        corridas = _corridas(mapa, y, larg)
        if not corridas:
            continue
        frente = max(corridas, key=lambda r: r[1])[1]
        cor = px[frente, y]
        for k in range(1, 3 - (n // 2) + 1):
            if frente + k < larg:
                pintar.append((frente + k, y, cor))
    for x, y, cor in pintar:
        if px[x, y][3] == 0 or px[x, y] == T.CONTORNO:
            px[x, y] = cor
    return T.contorno_externo(im)


def presas_da_mandibula(im):
    """As presas sobem pela frente da cara, de baixo para cima.

    No original elas sao dois pontinhos no meio da boca. Como presa
    de javali, nascendo do queixo, a cara deixa de ser a mesma.
    """
    mapa, px, larg, alt = _mapa(im)
    base = [(x, y) for y in range(alt) for x in range(larg)
            if mapa[y][x] == 'presa']
    if not base:
        return im
    pintar = []
    topo = min(y for _, y in base)
    for x, y in base:
        if y > topo:
            continue            # so a fileira de cima da presa cresce
        for k in (1, 2):
            if y - k >= 0:
                pintar.append((x, y - k))
    for x, y in pintar:
        if px[x, y][3] == 0 or px[x, y] == T.CONTORNO or \
                px[x, y] in set(T.PELE):
            px[x, y] = T.PRESA
    return T.contorno_externo(im)


# ------------------------------------------------------ B: a proporcao
def _caixa_cabeca(mapa, larg, alt):
    topo_metal = alt
    for y in range(alt):
        if any(mapa[y][x] == 'metal' for x in range(larg)):
            topo_metal = y
            break
    x0, x1, y0 = larg, -1, alt
    for y in range(topo_metal):
        for x in range(larg):
            if mapa[y][x] is not None:
                x0, x1, y0 = min(x0, x), max(x1, x), min(y0, y)
    return None if x1 < 0 else (x0, y0, x1 + 1, topo_metal)


def cranio_alto(im, fy=1.22, fx=0.92):
    """Cabeca mais alta e mais estreita, presa pelo pescoco.

    A ancora e a base da cabeca no proprio quadro: assim ela
    acompanha o corpo quando ele abaixa, em vez de flutuar.
    """
    mapa, px, larg, alt = _mapa(im)
    caixa = _caixa_cabeca(mapa, larg, alt)
    if not caixa:
        return im
    x0, y0, x1, y1 = caixa
    cab = im.crop(caixa)
    nl = max(1, round(cab.size[0] * fx))
    na = max(1, round(cab.size[1] * fy))
    cab = cab.resize((nl, na), Image.NEAREST)
    corpo = im.copy()
    corpo.paste(Image.new('RGBA', (x1 - x0, y1 - y0), VAZIO), (x0, y0))
    nova = Image.new('RGBA', im.size, VAZIO)
    nova.alpha_composite(corpo)
    nova.alpha_composite(cab, ((x0 + x1) // 2 - nl // 2, max(0, y1 - na)))
    return nova


def ombros_largos(im, k=2):
    """Alarga o tronco nas linhas logo abaixo da cabeca.

    So o tronco: dilatar o bicho inteiro engordaria tambem a cabeca
    e as pernas, e ai nada teria mudado de proporcao.
    """
    mapa, px, larg, alt = _mapa(im)
    caixa = _caixa_cabeca(mapa, larg, alt)
    if not caixa:
        return im
    topo = caixa[3]
    pintar = []
    for y in range(topo, min(alt, topo + 7)):
        corridas = [r for r in _corridas(mapa, y, larg) if r[1] - r[0] >= 3]
        corridas += [r for r in _corridas(mapa, y, larg, 'metal')
                     if r[1] - r[0] >= 3]
        if not corridas:
            continue
        a = min(r[0] for r in corridas)
        b = max(r[1] for r in corridas)
        for j in range(1, k + 1):
            pintar.append((a - j, y, px[a, y]))
            pintar.append((b + j, y, px[b, y]))
    for x, y, cor in pintar:
        if 0 <= x < larg and (px[x, y][3] == 0 or px[x, y] == T.CONTORNO):
            px[x, y] = cor
    return T.contorno_externo(im)


# -------------------------------------------------- C: costas e garras
def corcunda(im, k=4):
    """Giba nas costas: empurra a silhueta de tras para fora.

    Ele olha para a direita, entao 'costas' e o lado esquerdo das
    linhas de tronco. A giba e mais alta no meio e afina nas pontas.
    """
    mapa, px, larg, alt = _mapa(im)
    caixa = _caixa_cabeca(mapa, larg, alt)
    if not caixa:
        return im
    topo = caixa[3]
    linhas = list(range(topo, min(alt, topo + 8)))
    pintar = []
    for n, y in enumerate(linhas):
        corridas = [r for r in _corridas(mapa, y, larg) if r[1] - r[0] >= 3]
        corridas += [r for r in _corridas(mapa, y, larg, 'metal')
                     if r[1] - r[0] >= 3]
        if not corridas:
            continue
        a = min(r[0] for r in corridas)
        quanto = max(0, k - abs(n - 3) // 2)
        for j in range(1, quanto + 1):
            pintar.append((a - j, y, px[a, y]))
    for x, y, cor in pintar:
        if 0 <= x < larg and (px[x, y][3] == 0 or px[x, y] == T.CONTORNO):
            px[x, y] = cor
    return T.contorno_externo(im)


def garras(im):
    """Dedos em garra embaixo dos pes e na ponta das maos."""
    mapa, px, larg, alt = _mapa(im)
    chao = max((y for y in range(alt) for x in range(larg)
                if mapa[y][x] is not None), default=None)
    if chao is None:
        return im
    pintar = []
    for y in range(max(0, chao - 2), chao + 1):
        for (a, b) in _corridas(mapa, y, larg) + \
                _corridas(mapa, y, larg, 'metal'):
            if b - a < 2 or y < chao - 1:
                continue
            for x in (a, (a + b) // 2, b):
                if y + 1 < alt:
                    pintar.append((x, y + 1, px[x, y]))
    for x, y, cor in pintar:
        # Abaixo do pe nao ha vazio: ha a linha de contorno que fecha
        # a silhueta. A garra pinta por cima dela.
        if 0 <= x < larg and (px[x, y][3] == 0 or px[x, y] == T.CONTORNO):
            px[x, y] = cor
    return T.contorno_externo(im)


# -------------------------------------------------------------- graus
def grau_a(acao, i):
    im = T.quadro(acao, i)
    im = orelhas_compridas(im)
    im = nariz_adunco(im)
    return presas_da_mandibula(im)


def grau_b(acao, i):
    im = grau_a(acao, i)
    im = cranio_alto(im)
    im = ombros_largos(im)
    return im


def grau_c(acao, i):
    im = grau_b(acao, i)
    im = corcunda(im)
    return garras(im)


GRAUS = [('o V10 de agora', T.quadro),
         ('A  orelha, nariz e presa', grau_a),
         ('B  A + cranio alto e ombro largo', grau_b),
         ('C  B + corcunda e garras', grau_c)]


def _rotulo(pag, texto, x, y):
    d = ImageDraw.Draw(pag)
    d.rectangle([x, y, x + 8 * len(texto) + 10, y + 20], fill=(10, 12, 10, 220))
    d.text((x + 6, y + 5), texto, fill=(240, 236, 214, 255))


def main():
    os.makedirs(SAIDA, exist_ok=True)
    tira = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
    lado = 64 * 4
    paginas = []
    for i in range(17):
        pag = Image.new('RGBA', (len(tira) * lado, len(GRAUS) * lado),
                        (26, 28, 24, 255))
        for linha, (nome, func) in enumerate(GRAUS):
            for col, (acao, n) in enumerate(tira):
                im = func(acao, i % n).resize((lado, lado), Image.NEAREST)
                pag.alpha_composite(im, (col * lado, linha * lado))
            _rotulo(pag, nome, 6, linha * lado + 6)
        paginas.append(pag.convert('RGB').convert('P', palette=Image.ADAPTIVE,
                                                  colors=128))
    destino = os.path.join(SAIDA, 'v12-anatomia.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    print(destino, os.path.getsize(destino) // 1024, 'kB')

    Z = 8
    folha = Image.new('RGBA', (len(GRAUS) * 64 * Z, 64 * Z), (26, 28, 24, 255))
    for n, (nome, func) in enumerate(GRAUS):
        folha.alpha_composite(func('idle', 0).resize((64 * Z, 64 * Z),
                                                     Image.NEAREST),
                              (n * 64 * Z, 0))
        _rotulo(folha, nome, n * 64 * Z + 8, 8)
    folha.save(os.path.join(SAIDA, 'v12-anatomia-parado.png'))


if __name__ == '__main__':
    main()


# ==================================================================
# SEGUNDA RODADA — mudar o esqueleto, nao so os enfeites
#
# Os graus A-C ainda mantinham o plano do corpo do original: duas
# cabecas e meia de altura, bracos curtos, cranio em cupula. O que
# faz um personagem parecer COPIA e justamente esse plano. Aqui ele
# e refeito: perna curta, braco longo, cranio achatado, mandibula
# larga. A pose de cada quadro continua sendo a do original — o que
# muda e o corpo que executa a pose.
# ==================================================================
def _fundo_do_desenho(mapa, larg, alt):
    return max((y for y in range(alt) for x in range(larg)
                if mapa[y][x] is not None), default=None)


def _topo_do_metal(mapa, larg, alt):
    for y in range(alt):
        if any(mapa[y][x] == 'metal' for x in range(larg)):
            return y
    return None


def pernas_curtas(im, f=0.72):
    """Encolhe so do quadril para baixo e desce o resto junto.

    O corte segue a linha do metal LIDA NO QUADRO, nao uma altura
    fixa: o cinto sobe e desce quando ele agacha, e um corte fixo
    cortaria a coxa num quadro e o joelho no outro.
    """
    mapa, px, larg, alt = _mapa(im)
    quadril = _topo_do_metal(mapa, larg, alt)
    chao = _fundo_do_desenho(mapa, larg, alt)
    if quadril is None or chao is None or chao <= quadril + 2:
        return im
    pernas = im.crop((0, quadril, larg, chao + 1))
    na = max(2, round(pernas.size[1] * f))
    pernas = pernas.resize((larg, na), Image.NEAREST)
    tronco = im.crop((0, 0, larg, quadril))
    desce = (chao + 1 - quadril) - na
    nova = Image.new('RGBA', im.size, VAZIO)
    nova.alpha_composite(tronco, (0, desce))
    nova.alpha_composite(pernas, (0, quadril + desce))
    return nova


def bracos_longos(im, f=1.5):
    """Estica cada braco para baixo, pendurado no ombro.

    Braco, na maioria dos quadros do original, e um pedaco solto do
    desenho — da para pegar um por um. A ancora e o topo do pedaco
    (o ombro), entao a mao desce e o ombro fica no lugar.
    """
    mapa, px, larg, alt = _mapa(im)
    comps = _componentes(mapa, larg, alt)
    if len(comps) < 2:
        return im
    comps.sort(key=len, reverse=True)
    nova = im.copy()
    for grupo in comps[1:]:
        if not 10 <= len(grupo) <= 300:
            continue
        xs = [x for x, _ in grupo]
        ys = [y for _, y in grupo]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if y1 - y0 < 3:
            continue
        recorte = im.crop((x0, y0, x1 + 1, y1 + 1))
        na = min(round(recorte.size[1] * f), alt - y0 - 1)
        if na <= recorte.size[1]:
            continue
        esticado = recorte.resize((recorte.size[0], na), Image.NEAREST)
        for x, y in grupo:
            nova.putpixel((x, y), VAZIO)
        nova.alpha_composite(esticado, (x0, y0))
    return contorno_limpo(nova)


def contorno_limpo(im):
    return T.contorno_externo(im)


def _componentes(mapa, larg, alt):
    visto = [[False] * larg for _ in range(alt)]
    comps = []
    for y in range(alt):
        for x in range(larg):
            if visto[y][x] or mapa[y][x] is None:
                continue
            pilha, grupo = [(x, y)], []
            visto[y][x] = True
            while pilha:
                cx, cy = pilha.pop()
                grupo.append((cx, cy))
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < larg and 0 <= ny < alt
                            and not visto[ny][nx]
                            and mapa[ny][nx] is not None):
                        visto[ny][nx] = True
                        pilha.append((nx, ny))
            comps.append(grupo)
    return comps


def cranio_achatado(im, fx=1.14, fy=0.84):
    """Cabeca baixa e larga — o oposto da cupula do original."""
    return cranio_alto(im, fy=fy, fx=fx)


def testa_pesada(im):
    """Barra de sombra logo acima dos olhos: sobrancelha de osso."""
    mapa, px, larg, alt = _mapa(im)
    olhos = _olhos(mapa, larg, alt)
    if not olhos:
        return im
    for y in (olhos[0] - 1, olhos[0] - 2):
        if y < 0:
            continue
        for x in range(larg):
            if mapa[y][x] == 'pele':
                px[x, y] = T.PELE[0]
    return im


def mandibula_larga(im, k=2):
    """Alarga a cara da linha dos olhos para baixo: queixo de bruto."""
    mapa, px, larg, alt = _mapa(im)
    caixa = _caixa_cabeca(mapa, larg, alt)
    olhos = _olhos(mapa, larg, alt)
    if not caixa or not olhos:
        return im
    pintar = []
    for y in range(olhos[1] + 1, caixa[3]):
        corridas = _corridas(mapa, y, larg)
        if not corridas:
            continue
        a = min(r[0] for r in corridas)
        b = max(r[1] for r in corridas)
        for j in range(1, k + 1):
            pintar.append((a - j, y, px[a, y]))
            pintar.append((b + j, y, px[b, y]))
    for x, y, cor in pintar:
        if 0 <= x < larg and (px[x, y][3] == 0 or px[x, y] == T.CONTORNO):
            px[x, y] = cor
    return T.contorno_externo(im)


def grau_d(acao, i):
    im = grau_c(acao, i)
    im = pernas_curtas(im)
    return bracos_longos(im)


def grau_e(acao, i):
    # A ORDEM IMPORTA: achatar o cranio ANTES de puxar as orelhas.
    # Na primeira tentativa a orelha ja comprida era esticada junto
    # com a cabeca e virava uma asa atravessada na tela.
    im = T.quadro(acao, i)
    im = cranio_achatado(im)
    im = testa_pesada(im)
    im = mandibula_larga(im)
    im = orelhas_compridas(im, 3)
    im = nariz_adunco(im)
    im = presas_da_mandibula(im)
    im = pernas_curtas(im)
    im = bracos_longos(im)
    return corcunda(im)


def grau_f(acao, i):
    im = grau_e(acao, i)
    im = ombros_largos(im, 3)
    im = pernas_curtas(im, 0.8)
    return garras(im)


GRAUS2 = [('o V10 de agora', T.quadro),
          ('D  C + perna curta e braco longo', grau_d),
          ('E  cranio achatado, testa e mandibula', grau_e),
          ('F  E + ombro de touro e garras', grau_f)]


def folha2():
    tira = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
    lado = 64 * 4
    paginas = []
    for i in range(17):
        pag = Image.new('RGBA', (len(tira) * lado, len(GRAUS2) * lado),
                        (26, 28, 24, 255))
        for linha, (nome, func) in enumerate(GRAUS2):
            for col, (acao, n) in enumerate(tira):
                im = func(acao, i % n).resize((lado, lado), Image.NEAREST)
                pag.alpha_composite(im, (col * lado, linha * lado))
            _rotulo(pag, nome, 6, linha * lado + 6)
        paginas.append(pag.convert('RGB').convert('P', palette=Image.ADAPTIVE,
                                                  colors=128))
    destino = os.path.join(SAIDA, 'v13-esqueleto.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    print(destino, os.path.getsize(destino) // 1024, 'kB')
    Z = 8
    folha = Image.new('RGBA', (len(GRAUS2) * 64 * Z, 64 * Z), (26, 28, 24, 255))
    for n, (nome, func) in enumerate(GRAUS2):
        folha.alpha_composite(func('idle', 0).resize((64 * Z, 64 * Z),
                                                     Image.NEAREST),
                              (n * 64 * Z, 0))
        _rotulo(folha, nome, n * 64 * Z + 8, 8)
    folha.save(os.path.join(SAIDA, 'v13-esqueleto-parado.png'))
