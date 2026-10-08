#!/usr/bin/env python3
"""DEZ GOBLINS DIFERENTES, todos com a animacao do original.

A tentativa anterior mexeu so em paleta e as dez versoes sairam
iguais umas as outras. Aqui cada versao muda o goblin de verdade:
proporcao, contorno, pele, olho, presa, roupa, textura.

O que NAO muda em nenhuma delas e o movimento. Todo quadro e
derivado do quadro correspondente de `art-source/goblins-originais/`
(32x32, 62 arquivos), dobrado para 64. Ou seja: a animacao nao e
recriada, E a do original — por construcao ela continua fluida em
todas as dez, por mais diferente que o bicho fique.

As transformacoes sao deterministicas e dependem so do quadro, nunca
de qual quadro da sequencia e. E isso que impede tremelique: o mesmo
pixel recebe o mesmo tratamento no quadro 1 e no quadro 8.

    python3 tools/goblin_versoes.py

Escreve art-source/goblin-v3/versoes/<nome>.gif e um index.html.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import goblin_v3 as V  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAIDA = os.path.join(RAIZ, 'art-source', 'goblin-v3', 'versoes')

TIRA = [('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17)]
QUADROS = 17
Z = 5
FUNDO = (26, 28, 24, 255)

PELE = list(V.PELE)
PANO = list(V.PANO)
TODA_PELE = PELE + [V.PELE_SOMBRA, V.PELE_ESCURA, V.PELE_LUZ]
TODO_PANO = PANO + [V.PANO_SOMBRA, V.PANO_LUZ]


# ----------------------------------------------------------------- base
def base(acao, i, nivel=0):
    im = V.nivel0(acao, i)
    for passe in V.PASSES[:nivel]:
        im = passe(im)
    return im


def _px(im):
    return im.load(), im.size[0], im.size[1]


def vazio(c):
    return c[3] == 0


# ---------------------------------------------------------- ferramentas
def troca(im, mapa):
    """Troca cores exatas. O que nao esta no mapa fica como esta."""
    px, larg, alt = _px(im)
    for y in range(alt):
        for x in range(larg):
            c = px[x, y]
            if c in mapa:
                px[x, y] = mapa[c]
    return im


def paleta(pele=None, pano=None, olho=None, contorno=None, presa=None):
    """Monta o mapa de troca a partir de rampas novas.

    `pele` e `pano` sao trincas escuro->claro. Os tons extras que o
    detalhe inventou (sombra, escura, luz) sao derivados das pontas
    da rampa nova, para a versao continuar coerente mesmo no nivel 3.
    """
    m = {}
    if pele:
        for velho, novo in zip(PELE, pele):
            m[velho] = novo
        m[V.PELE_SOMBRA] = _mistura(pele[0], (0, 0, 0, 255), 0.35)
        m[V.PELE_ESCURA] = _mistura(pele[0], (0, 0, 0, 255), 0.62)
        m[V.PELE_LUZ] = _mistura(pele[2], (255, 255, 255, 255), 0.35)
    if pano:
        for velho, novo in zip(PANO, pano):
            m[velho] = novo
        m[V.PANO_SOMBRA] = _mistura(pano[0], (0, 0, 0, 255), 0.35)
        m[V.PANO_LUZ] = _mistura(pano[2], (255, 255, 255, 255), 0.3)
    if olho:
        m[V.OLHO] = olho
    if contorno:
        m[V.CONTORNO] = contorno
    if presa:
        m[V.PRESA] = presa
    return m


def _mistura(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)) + (255,)


def contorno_grosso(im, cor=(16, 16, 18, 255)):
    """Borda de 1 px em volta da silhueta inteira — leitura de desenho."""
    px, larg, alt = _px(im)
    fora = [(x, y) for y in range(alt) for x in range(larg)
            if vazio(px[x, y])
            and any(0 <= x + dx < larg and 0 <= y + dy < alt
                    and not vazio(px[x + dx, y + dy])
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
    for x, y in fora:
        px[x, y] = cor
    return im


def sem_contorno(im):
    """Tira a linha preta: cada pixel de contorno vira o vizinho mais
    escuro de dentro. Fica um goblin sem borda, mais macio."""
    px, larg, alt = _px(im)
    alvo = {}
    for y in range(alt):
        for x in range(larg):
            if px[x, y] != V.CONTORNO:
                continue
            dentro = [px[x + dx, y + dy]
                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                                     (1, 1), (-1, -1), (1, -1), (-1, 1))
                      if 0 <= x + dx < larg and 0 <= y + dy < alt
                      and not vazio(px[x + dx, y + dy])
                      and px[x + dx, y + dy] != V.CONTORNO]
            if dentro:
                alvo[(x, y)] = min(dentro, key=lambda c: sum(c[:3]))
    for (x, y), c in alvo.items():
        px[x, y] = c
    return im


def chapa(im, ramp):
    """Reduz uma rampa de tres tons a dois — visual de desenho animado."""
    return troca(im, {ramp[1]: ramp[2]})


def _caixa_cabeca(im):
    """Onde comeca o pano e onde acaba a cabeca.

    A cabeca e tudo que esta acima do pixel de pano mais alto. Como
    a regra le o proprio quadro, ela acompanha a cabeca quando ela
    abaixa no golpe ou na pancada.
    """
    px, larg, alt = _px(im)
    topo_pano = alt
    for y in range(alt):
        for x in range(larg):
            if px[x, y] in TODO_PANO:
                topo_pano = y
                break
        if topo_pano != alt:
            break
    cx0, cx1, cy0 = larg, 0, alt
    for y in range(topo_pano):
        for x in range(larg):
            if not vazio(px[x, y]):
                cx0, cx1, cy0 = min(cx0, x), max(cx1, x), min(cy0, y)
    if cx1 < cx0:
        return None
    return (cx0, cy0, cx1 + 1, topo_pano)


def cabeca_grande(im, fator=1.35):
    """Aumenta so a cabeca, presa pelo pescoco."""
    caixa = _caixa_cabeca(im)
    if not caixa:
        return im
    x0, y0, x1, y1 = caixa
    cab = im.crop(caixa)
    larg, alt = cab.size
    nl, na = max(1, round(larg * fator)), max(1, round(alt * fator))
    cab = cab.resize((nl, na), Image.NEAREST)
    nova = Image.new('RGBA', im.size, (0, 0, 0, 0))
    corpo = im.copy()
    apaga = Image.new('RGBA', (larg, alt), (0, 0, 0, 0))
    corpo.paste(apaga, (x0, y0))
    nova.alpha_composite(corpo)
    meio = (x0 + x1) // 2
    nova.alpha_composite(cab, (meio - nl // 2, y1 - na))
    return nova


def estica(im, fx=1.0, fy=1.0):
    """Estica o bicho inteiro ancorado no chao e no meio da tela.

    A ancora e fixa (x=32, base da arte), nao a caixa do quadro: se
    fosse a caixa, cada quadro escalaria de um jeito e a animacao
    tremeria.
    """
    larg, alt = im.size
    nl, na = max(1, round(larg * fx)), max(1, round(alt * fy))
    red = im.resize((nl, na), Image.NEAREST)
    nova = Image.new('RGBA', im.size, (0, 0, 0, 0))
    nova.alpha_composite(red, (larg // 2 - nl // 2, alt - na))
    return nova


def presas_grandes(im, cor=None):
    """Puxa a presa um pixel para baixo — cara mais bruta."""
    px, larg, alt = _px(im)
    cor = cor or V.PRESA
    alvo = [(x, y + 1) for y in range(alt - 1) for x in range(larg)
            if px[x, y] == V.PRESA and px[x, y + 1] != V.PRESA]
    for x, y in alvo:
        px[x, y] = cor
    return im


def pintura_de_guerra(im, cor=(168, 44, 40, 255)):
    """Faixa atravessando os olhos, pintada so na pele."""
    px, larg, alt = _px(im)
    linhas = sorted({y for y in range(alt) for x in range(larg)
                     if px[x, y] == V.OLHO})
    if not linhas:
        return im
    for y in (linhas[0] - 1, linhas[-1] + 1):
        if 0 <= y < alt:
            for x in range(larg):
                if px[x, y] in TODA_PELE:
                    px[x, y] = cor
    return im


def textura_pontilhada(im, cor):
    """Xadrez de um tom so na metade de baixo: pele de pedra/casca."""
    px, larg, alt = _px(im)
    meio = alt // 2 + 6
    for y in range(meio, alt):
        for x in range(larg):
            if px[x, y] in TODA_PELE and (x + y) % 2 == 0:
                px[x, y] = cor
    return im


def placas(im, metal=(126, 132, 140, 255), luz=(176, 182, 190, 255)):
    """O pano vira placa de metal, com a fileira de cima brilhando."""
    px, larg, alt = _px(im)
    for y in range(alt):
        for x in range(larg):
            if px[x, y] in TODO_PANO:
                de_cima = y > 0 and px[x, y - 1] not in TODO_PANO
                px[x, y] = luz if de_cima else metal
    return im


# -------------------------------------------------------------- versoes
def v01_fiel(acao, i):
    return base(acao, i, 0)


def v02_detalhado(acao, i):
    return base(acao, i, 3)


def v03_desenho(acao, i):
    im = base(acao, i, 0)
    im = chapa(im, PELE)
    im = chapa(im, PANO)
    return contorno_grosso(troca(im, {V.CONTORNO: (16, 16, 18, 255)}))


def v04_macio(acao, i):
    im = sem_contorno(base(acao, i, 2))
    return troca(im, paleta(pele=((96, 178, 118, 255), (124, 204, 142, 255),
                                  (166, 226, 178, 255)),
                            pano=((122, 94, 66, 255), (150, 118, 88, 255),
                                  (184, 152, 120, 255))))


def v05_cabecudo(acao, i):
    return cabeca_grande(base(acao, i, 2), 1.35)


def v06_esguio(acao, i):
    return estica(base(acao, i, 2), 0.88, 1.18)


def v07_selvagem(acao, i):
    im = base(acao, i, 2)
    im = troca(im, paleta(pele=((74, 104, 44, 255), (102, 138, 58, 255),
                                (138, 172, 82, 255)),
                          pano=((72, 42, 30, 255), (104, 64, 44, 255),
                                (142, 96, 64, 255)),
                          olho=(248, 224, 120, 255),
                          contorno=(28, 26, 20, 255)))
    im = presas_grandes(im)
    return pintura_de_guerra(im)


def v08_caverna(acao, i):
    im = base(acao, i, 3)
    im = troca(im, paleta(pele=((78, 88, 104, 255), (104, 116, 134, 255),
                                (140, 152, 170, 255)),
                          pano=((44, 46, 54, 255), (66, 70, 80, 255),
                                (96, 102, 114, 255)),
                          olho=(252, 236, 160, 255),
                          contorno=(22, 24, 30, 255),
                          presa=(236, 232, 214, 255)))
    return textura_pontilhada(im, (88, 98, 116, 255))


def v09_xama(acao, i):
    im = base(acao, i, 3)
    im = troca(im, paleta(pele=((92, 62, 126, 255), (124, 86, 162, 255),
                                (162, 124, 198, 255)),
                          pano=((158, 148, 118, 255), (196, 186, 152, 255),
                                (226, 218, 188, 255)),
                          olho=(146, 244, 232, 255),
                          contorno=(34, 24, 44, 255)))
    return im


def v10_encouracado(acao, i):
    im = base(acao, i, 3)
    im = placas(im)
    im = troca(im, paleta(pele=((52, 120, 72, 255), (70, 150, 92, 255),
                                (102, 182, 120, 255)),
                          olho=(240, 240, 252, 255),
                          contorno=(18, 20, 22, 255)))
    return contorno_grosso(im, (18, 20, 22, 255))


VERSOES = [
    ('v01-fiel', 'O original, so dobrado de tamanho (referencia)', v01_fiel),
    ('v02-detalhado', 'O original com luz, sombra e pupila', v02_detalhado),
    ('v03-desenho', 'Cores chapadas e contorno preto grosso', v03_desenho),
    ('v04-macio', 'Sem contorno nenhum, pele clara', v04_macio),
    ('v05-cabecudo', 'Cabeca 35% maior (proporcao de mascote)', v05_cabecudo),
    ('v06-esguio', 'Alto e magro, 18% mais esticado', v06_esguio),
    ('v07-selvagem', 'Pele oliva, presas maiores, pintura de guerra',
     v07_selvagem),
    ('v08-caverna', 'Pele de pedra cinza, olho amarelo, textura pontilhada',
     v08_caverna),
    ('v09-xama', 'Pele roxa, panos de osso, olho ciano', v09_xama),
    ('v10-encouracado', 'Pano virou placa de metal, contorno grosso',
     v10_encouracado),
]


def gif(nome, func):
    tiras = {acao: [func(acao, i) for i in range(n)] for acao, n in TIRA}
    lado = 64 * Z
    paginas = []
    for i in range(QUADROS):
        pag = Image.new('RGBA', (len(TIRA) * lado, lado), FUNDO)
        for col, (acao, n) in enumerate(TIRA):
            im = tiras[acao][i % n]
            pag.alpha_composite(im.resize((lado, lado), Image.NEAREST),
                                (col * lado, 0))
        paginas.append(pag.convert('RGB').convert(
            'P', palette=Image.ADAPTIVE, colors=64))
    destino = os.path.join(SAIDA, nome + '.gif')
    paginas[0].save(destino, save_all=True, append_images=paginas[1:],
                    duration=120, loop=0, optimize=True)
    return destino


def folha():
    """Uma imagem parada com as dez, numeradas, para comparar sem GIF."""
    lado = 64 * 4
    pag = Image.new('RGBA', (5 * lado, 2 * lado), FUNDO)
    for n, (nome, _, func) in enumerate(VERSOES):
        im = func('idle', 0).resize((lado, lado), Image.NEAREST)
        pag.alpha_composite(im, ((n % 5) * lado, (n // 5) * lado))
    pag.save(os.path.join(SAIDA, 'as-dez.png'))


def main():
    os.makedirs(SAIDA, exist_ok=True)
    for antigo in os.listdir(SAIDA):
        if antigo.endswith('.gif') and antigo.startswith('v0') \
                and '-' not in antigo:
            os.remove(os.path.join(SAIDA, antigo))
    for nome, titulo, func in VERSOES:
        caminho = gif(nome, func)
        print(nome, '-', titulo, os.path.getsize(caminho) // 1024, 'kB')
    folha()
    blocos = '\n'.join(
        f'''  <figure>
    <figcaption><b>{nome.split('-')[0].upper()}</b> — {titulo}</figcaption>
    <img src="{nome}.gif" alt="{nome}">
  </figure>''' for nome, titulo, _ in VERSOES)
    html = f'''<!doctype html>
<meta charset="utf-8">
<title>Goblin — 10 versoes diferentes</title>
<style>
 body {{ background:#15170f; color:#e8e4d0; font:15px/1.5 monospace;
        margin:0; padding:24px 16px; }}
 h1 {{ font-size:20px; margin:0 0 4px; }}
 p.ajuda {{ color:#9aa08a; margin:0 0 20px; }}
 figure {{ margin:0 0 26px; }}
 figcaption {{ margin-bottom:6px; }}
 img {{ width:100%; max-width:1280px; image-rendering:pixelated;
        border:1px solid #2c3024; background:#1a1c18; display:block; }}
</style>
<h1>Goblin — 10 versoes diferentes</h1>
<p class="ajuda">Colunas: parado · andando · batendo · levando pancada.
Todas usam a animacao do goblin original, quadro a quadro.</p>
{blocos}
'''
    with open(os.path.join(SAIDA, 'index.html'), 'w') as fh:
        fh.write(html)


if __name__ == '__main__':
    main()
