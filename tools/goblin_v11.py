#!/usr/bin/env python3
"""V11 — o goblin encouracado deixando de parecer o original.

O V10 maior ainda era, no fundo, o goblin do jogo antigo com placas:
mesma cabeca, mesma cara, mesma cor. Aqui ele vira outro personagem,
em tres graus, para voce dizer ate onde ir:

  A  ELMO E OMBREIRAS. O soldado. A metade de cima da cabeca vira
     metal com aba, os bracos ganham ombreira. As orelhas continuam
     verdes e saem por fora do elmo — e o que ainda lembra goblin.
  B  A + CARA E COR NOVAS. Pele de jade frio em vez do verde-grama
     do original, ferro azulado, OLHO AMBAR (o olho branco era a
     marca mais reconhecivel do original) e crista no alto do elmo.
  C  B + ANATOMIA. Orelhas puxadas em ponta, presas maiores,
     rebites no metal. Aqui nao sobra parentesco a nao ser a pose.

O que nenhum grau toca e a ANIMACAO. Todo quadro continua derivado
do quadro correspondente de `art-source/goblins-originais/` via
scale3x, com deslocamento fixo. As transformacoes leem so o proprio
quadro — nunca a posicao dele na sequencia — entao o mesmo pixel
recebe o mesmo tratamento em todos os quadros e nada treme.

    python3 tools/goblin_v11.py
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goblin_v10 as T  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'art-source', 'goblin-v3')

# ---------------------------------------------------------- cores novas
# Nenhuma delas e do original: a pele e jade frio, o metal e ferro
# azulado e o olho e ambar. Juntas, mudam o personagem mesmo de longe.
JADE = [(22, 62, 58, 255), (38, 92, 82, 255), (56, 124, 104, 255),
        (86, 160, 130, 255), (124, 196, 160, 255)]
FERRO = [(40, 44, 56, 255), (66, 72, 88, 255), (96, 104, 124, 255),
         (142, 150, 172, 255), (196, 202, 220, 255)]
AMBAR = (248, 176, 56, 255)
AMBAR_PUPILA = (92, 44, 12, 255)
CRISTA = (168, 56, 44, 255)
CRISTA_LUZ = (208, 96, 72, 255)
PRESA = (236, 234, 206, 255)


def _mapa(im):
    """Classifica cada pixel por material, ja nas cores do v10."""
    px, larg, alt = im.load(), im.size[0], im.size[1]
    # As duas paletas ao mesmo tempo: a do v10 e a nova. Os passes
    # rodam antes E depois da repintura, e um mapa que so conhecesse
    # uma delas classificaria metade do bicho como contorno.
    pele = set(T.PELE) | set(JADE)
    metal = set(T.METAL) | set(FERRO)
    presa = {T.PRESA, PRESA}
    olho = {T.OLHO, T.PUPILA, (255, 255, 255, 255),
            AMBAR, AMBAR_PUPILA, (255, 230, 170, 255)}
    mapa = [[None] * larg for _ in range(alt)]
    for y in range(alt):
        for x in range(larg):
            c = px[x, y]
            if c[3] == 0:
                continue
            if c in pele:
                mapa[y][x] = 'pele'
            elif c in metal:
                mapa[y][x] = 'metal'
            elif c in olho:
                mapa[y][x] = 'olho'
            elif c in presa:
                mapa[y][x] = 'presa'
            else:
                mapa[y][x] = 'contorno'
    return mapa, px, larg, alt


def _linhas_do_olho(mapa, larg, alt):
    ys = [y for y in range(alt) for x in range(larg) if mapa[y][x] == 'olho']
    return (min(ys), max(ys)) if ys else None


def _corridas(mapa, y, larg, tipo='pele'):
    """Os trechos continuos de um material numa linha."""
    saida, inicio = [], None
    for x in range(larg + 1):
        dentro = x < larg and mapa[y][x] == tipo
        if dentro and inicio is None:
            inicio = x
        elif not dentro and inicio is not None:
            saida.append((inicio, x - 1))
            inicio = None
    return saida


def elmo(im, metal=None):
    """A metade de cima da cabeca vira capacete, com aba escura.

    A divisa e a linha dos olhos, lida do proprio quadro: assim o
    elmo desce junto quando a cabeca abaixa no golpe.

    Em cada linha, o trecho de pele que contem o MEIO da cabeca e o
    cranio e vira metal; os outros trechos da mesma linha sao as
    orelhas e ficam verdes, saindo por fora do elmo.
    """
    mapa, px, larg, alt = _mapa(im)
    olhos = _linhas_do_olho(mapa, larg, alt)
    if not olhos:
        return im
    topo_olho = olhos[0]
    metal = metal or T.METAL
    cabeca_x = [x for y in range(max(0, topo_olho - 2), topo_olho + 1)
                for x in range(larg) if mapa[y][x] == 'pele']
    if not cabeca_x:
        return im
    meio = (min(cabeca_x) + max(cabeca_x)) // 2
    for y in range(0, topo_olho):
        for (a, b) in _corridas(mapa, y, larg):
            if not (a - 1 <= meio <= b + 1):
                continue        # orelha: nao recebe elmo
            borda = y == topo_olho - 1
            for x in range(a, b + 1):
                if borda:
                    px[x, y] = metal[0]           # aba, sombra dura
                elif y == 0 or mapa[y - 1][x] != 'pele':
                    px[x, y] = metal[4]           # cume, brilho
                else:
                    px[x, y] = metal[2 if (x + y) % 7 else 3]
    return im


def _componentes(mapa, larg, alt):
    """Separa os pedacos soltos do desenho (os bracos costumam ser)."""
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
                            and not visto[ny][nx] and mapa[ny][nx] is not None):
                        visto[ny][nx] = True
                        pilha.append((nx, ny))
            comps.append(grupo)
    return comps


def ombreiras(im, metal=None):
    """Chapa no alto de cada braco.

    Os bracos aparecem como pedacos separados do corpo na maioria
    dos quadros do original; nos quadros em que estao colados, a
    ombreira so nao entra — e melhor faltar num quadro do que uma
    chapa pousar no meio do peito.
    """
    mapa, px, larg, alt = _mapa(im)
    metal = metal or T.METAL
    comps = _componentes(mapa, larg, alt)
    if len(comps) < 2:
        return im
    comps.sort(key=len, reverse=True)
    for grupo in comps[1:]:
        if not 12 <= len(grupo) <= 260:
            continue
        pele = [(x, y) for x, y in grupo if mapa[y][x] == 'pele']
        if len(pele) < 6:
            continue
        topo = min(y for _, y in pele)
        for x, y in pele:
            if y <= topo + 1:
                px[x, y] = metal[4] if y == topo else metal[2]
            elif y == topo + 2:
                px[x, y] = metal[0]
    return im


def repinta(im):
    """Troca as rampas do v10 pelas novas: jade, ferro, ambar."""
    px, larg, alt = im.load(), im.size[0], im.size[1]
    de_pele = {c: JADE[i] for i, c in enumerate(T.PELE)}
    de_metal = {c: FERRO[i] for i, c in enumerate(T.METAL)}
    extra = {T.OLHO: AMBAR, (255, 255, 255, 255): (255, 230, 170, 255),
             T.PUPILA: AMBAR_PUPILA, T.PRESA: PRESA}
    for y in range(alt):
        for x in range(larg):
            c = px[x, y]
            if c in de_pele:
                px[x, y] = de_pele[c]
            elif c in de_metal:
                px[x, y] = de_metal[c]
            elif c in extra:
                px[x, y] = extra[c]
    return im


def crista(im):
    """Penacho vermelho no alto do elmo — o que o original jamais teve."""
    mapa, px, larg, alt = _mapa(im)
    metal = [(x, y) for y in range(alt) for x in range(larg)
             if mapa[y][x] == 'metal']
    if not metal:
        return im
    topo = min(y for _, y in metal)
    linha = [x for x, y in metal if y <= topo + 1]
    if len(linha) < 4:
        return im
    a, b = min(linha), max(linha)
    for x in range(a + 1, b):
        altura = 2 if (x - a) % 3 else 3
        for k in range(1, altura + 1):
            y = topo - k
            # Acima do elmo nao ha vazio e sim a linha de contorno
            # que fecha a silhueta; o penacho pinta por cima dela e
            # o contorno e refeito no fim.
            if y >= 0 and (px[x, y][3] == 0 or px[x, y] == T.CONTORNO):
                px[x, y] = CRISTA_LUZ if k == altura else CRISTA
    return T.contorno_externo(im)


def orelhas_em_ponta(im):
    """Puxa a ponta das orelhas para fora e para cima.

    Orelha e o trecho de pele da linha que NAO contem o meio da
    cabeca — a mesma regra do elmo, so que agora para esticar.
    """
    mapa, px, larg, alt = _mapa(im)
    olhos = _linhas_do_olho(mapa, larg, alt)
    if not olhos:
        return im
    topo_olho = olhos[0]
    todos = [x for y in range(max(0, topo_olho - 2), topo_olho + 1)
             for x in range(larg) if mapa[y][x] is not None]
    if not todos:
        return im
    meio = (min(todos) + max(todos)) // 2
    pintar = []
    for y in range(0, topo_olho + 1):
        for (a, b) in _corridas(mapa, y, larg):
            if a - 1 <= meio <= b + 1 or b - a > 7:
                continue
            esquerda = b < meio
            for k in (1, 2):
                x = a - k if esquerda else b + k
                yy = y - k
                if 0 <= x < larg and 0 <= yy < alt and px[x, yy][3] == 0:
                    pintar.append((x, yy, px[a if esquerda else b, y]))
    for x, y, cor in pintar:
        px[x, y] = cor
    return T.contorno_externo(im)


def presas_maiores(im):
    mapa, px, larg, alt = _mapa(im)
    novos = [(x, y + 1) for y in range(alt - 1) for x in range(larg)
             if mapa[y][x] == 'presa' and mapa[y + 1][x] != 'presa']
    for x, y in novos:
        if px[x, y][3] != 0:
            px[x, y] = PRESA
    return im


def rebites(im):
    """Ponto de luz a cada quatro pixels na borda de cima das chapas."""
    mapa, px, larg, alt = _mapa(im)
    for y in range(alt):
        for x in range(larg):
            if mapa[y][x] != 'metal' or x % 4:
                continue
            if y == 0 or mapa[y - 1][x] != 'metal':
                px[x, y] = FERRO[4]
    return im


# ------------------------------------------------------------- graus
def grau_a(acao, i):
    im = T.quadro(acao, i)
    im = elmo(im)
    return ombreiras(im)


def grau_b(acao, i):
    im = grau_a(acao, i)
    im = repinta(im)
    return crista(im)


def grau_c(acao, i):
    im = grau_b(acao, i)
    im = orelhas_em_ponta(im)
    im = presas_maiores(im)
    return rebites(im)


GRAUS = [('v10 maior (o de agora)', T.quadro),
         ('A — elmo e ombreiras', grau_a),
         ('B — A + jade, ferro e olho ambar, com crista', grau_b),
         ('C — B + orelhas em ponta, presas e rebites', grau_c)]


def main():
    os.makedirs(SAIDA, exist_ok=True)
    tira = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
    Z, lado = 4, 64 * 4
    paginas = []
    for i in range(17):
        pag = Image.new('RGBA', (len(tira) * lado, len(GRAUS) * lado),
                        (26, 28, 24, 255))
        for linha, (_, func) in enumerate(GRAUS):
            for col, (acao, n) in enumerate(tira):
                im = func(acao, i % n).resize((lado, lado), Image.NEAREST)
                pag.alpha_composite(im, (col * lado, linha * lado))
        paginas.append(pag.convert('RGB').convert('P', palette=Image.ADAPTIVE,
                                                  colors=128))
    destino = os.path.join(SAIDA, 'v11-graus.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    print(destino, os.path.getsize(destino) // 1024, 'kB')

    Z = 8
    folha = Image.new('RGBA', (len(GRAUS) * 64 * Z, 64 * Z), (26, 28, 24, 255))
    for n, (_, func) in enumerate(GRAUS):
        folha.alpha_composite(func('idle', 0).resize((64 * Z, 64 * Z),
                                                     Image.NEAREST),
                              (n * 64 * Z, 0))
    folha.save(os.path.join(SAIDA, 'v11-graus-parado.png'))


if __name__ == '__main__':
    main()
