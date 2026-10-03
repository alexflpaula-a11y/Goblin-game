#!/usr/bin/env python3
"""
Converte a arte do goblin CAIDO em sprite de verdade.

A pose do corpo caido — DE BRUCOS, de costas para a camera, na diagonal,
botas embaixo a esquerda e cabeca em cima a direita, membros abertos — nao
sai de rotacao: girar o goblin de pe num angulo quebrado arrebenta o
contorno, e de qualquer forma continuaria mostrando o rosto, que deitado
assim esta enfiado no chao. Ela foi desenhada a parte, em
`art-source/goblins-v2/caido-gerado.png`, e este script transforma aquele
desenho grande no sprite 64x64 que o jogo usa:

  1. reduz pela grade (a arte vem com celulas de N px, uma celula = um pixel)
  2. tira o fundo magenta por preenchimento a partir da borda — recortar por
     cor em toda a imagem comeria os pixels escuros do contorno
  3. troca cada cor pela MAIS PROXIMA da paleta do goblin, para o corpo
     caido ser feito exatamente das mesmas cores do corpo de pe
  4. remove pixels soltos e fecha buracos
  5. devolve o relevo que a reducao achatou (quina clara do lado da
     luz, quina escura do lado oposto)
  6. encosta o corpo no chao e centra no quadro de 64x64

    python3 tools/import_caido.py
"""

import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))

import goblin_rig as R                                      # noqa: E402

ENTRADA = ROOT / 'art-source' / 'goblins-v2' / 'caido-gerado.png'
SAIDA = ROOT / 'art-source' / 'goblins-v2' / 'caido-limpa.png'

# Cores que o corpo do goblin usa. A arte caida e remapeada SO para elas,
# entao nao entra nenhum tom novo no jogo por causa desta pose.
CORPO = ('k', 'e', 'd', 'n', 'j', 'g', 'l', 'f', 'B', 'b', 'h', 'z', 'q')


def reduzir(img, n=R.SIZE):
    """Reduz pela grade: a cor de cada celula e a mediana do miolo dela."""
    a = np.array(img.convert('RGB')).astype(int)
    cel = img.size[0] // n
    margem = max(1, cel // 4)
    out = np.zeros((n, n, 3), int)
    for y in range(n):
        for x in range(n):
            bloco = a[y * cel + margem:(y + 1) * cel - margem,
                      x * cel + margem:(x + 1) * cel - margem]
            out[y, x] = np.median(bloco.reshape(-1, 3), axis=0)
    return out


def tirar_fundo(rgb):
    """Fundo = o que esta ligado a borda e tem a cor do fundo.

    Preencher a partir da borda (e nao recortar por cor) e o que preserva
    um pixel de fundo que tenha ficado preso dentro do desenho.
    """
    h, w = rgb.shape[:2]
    fundo = rgb[0, 0]
    perto = (np.abs(rgb - fundo).sum(axis=2) < 150)
    vistos = np.zeros((h, w), bool)
    fila = deque([(x, y) for x in range(w) for y in (0, h - 1)]
                 + [(x, y) for y in range(h) for x in (0, w - 1)])
    while fila:
        x, y = fila.popleft()
        if not (0 <= x < w and 0 <= y < h) or vistos[y, x] or not perto[y, x]:
            continue
        vistos[y, x] = True
        fila.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return ~vistos


def para_paleta(rgb, massa):
    """Troca cada cor pela mais proxima da paleta do goblin."""
    nomes = list(CORPO)
    pal = np.array([R.C[c][:3] for c in nomes], int)
    out = [[None] * rgb.shape[1] for _ in range(rgb.shape[0])]
    for y in range(rgb.shape[0]):
        for x in range(rgb.shape[1]):
            if not massa[y, x]:
                continue
            d = ((pal - rgb[y, x]) ** 2).sum(axis=1)
            out[y][x] = nomes[int(d.argmin())]
    return out


def _vizinhos(m):
    h, w = m.shape
    p = np.zeros((h + 2, w + 2), bool)
    p[1:-1, 1:-1] = m
    return (p[:-2, 1:-1].astype(int) + p[2:, 1:-1] + p[1:-1, :-2] + p[1:-1, 2:])


def limpar(buf):
    """Tira pixel solto, fecha buraco e redesenha o contorno."""
    h = len(buf)
    m = np.array([[c is not None for c in linha] for linha in buf])
    for _ in range(2):
        buraco = (~m) & (_vizinhos(m) >= 3)
        for y, x in zip(*np.nonzero(buraco)):
            perto = [buf[y + dy][x + dx] for dy, dx in
                     ((-1, 0), (1, 0), (0, -1), (0, 1))
                     if 0 <= y + dy < h and 0 <= x + dx < h and m[y + dy, x + dx]]
            cheio = [c for c in perto if c != 'k'] or perto
            buf[y][x] = cheio[0]
        m |= buraco
        solto = m & (_vizinhos(m) <= 1)
        for y, x in zip(*np.nonzero(solto)):
            buf[y][x] = None
        m &= ~solto
    for y, x in zip(*np.nonzero(m & (_vizinhos(m) < 4))):
        buf[y][x] = 'k'
    return buf


# Luz vindo de cima a esquerda, igual a do goblin de pe.
LUZ = (-0.62, -0.78)
CLARO = {'e': 'd', 'd': 'n', 'n': 'j', 'j': 'g', 'g': 'l', 'l': 'f', 'f': 'f',
         'B': 'b', 'b': 'h', 'h': 'h', 'z': 'q', 'q': 'q'}
ESCURO = {'d': 'e', 'n': 'd', 'j': 'n', 'g': 'j', 'l': 'g', 'f': 'l',
          'e': 'e', 'b': 'B', 'h': 'b', 'B': 'B', 'q': 'z', 'z': 'z'}


def retocar(buf):
    """Devolve volume ao desenho reduzido.

    A reducao por mediana achata tudo: o corpo caido saia com a cabeca e os
    bracos chapados, sem o relevo que o goblin de pe tem. Aqui cada pixel
    olha dois passos na direcao da luz e dois na direcao contraria: se do
    lado da luz ja acabou o corpo, ele esta na quina iluminada e sobe um
    tom; se quem acabou foi o lado oposto, esta na quina de sombra e desce.
    E a mesma regra de sempre, so que aplicada depois da reducao.
    """
    n = R.SIZE

    def vazio(x, y):
        return not (0 <= x < n and 0 <= y < n) or buf[y][x] in (None, 'k')

    novo = [linha[:] for linha in buf]
    for y in range(n):
        for x in range(n):
            ch = buf[y][x]
            if ch is None or ch == 'k' or ch not in CLARO:
                continue
            luz = vazio(round(x + LUZ[0] * 2), round(y + LUZ[1] * 2))
            sombra = vazio(round(x - LUZ[0] * 2), round(y - LUZ[1] * 2))
            if luz and not sombra:
                novo[y][x] = CLARO[ch]
            elif sombra and not luz:
                novo[y][x] = ESCURO[ch]
    return novo


def encostar_no_chao(buf):
    """Centra na horizontal e encosta a base do corpo no chao do quadro."""
    cheios = [(x, y) for y in range(R.SIZE) for x in range(R.SIZE)
              if buf[y][x] is not None]
    xs = [x for x, _ in cheios]
    ys = [y for _, y in cheios]
    dx = (R.SIZE - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    dy = R.ANCHORS['ground_y'] - max(ys)
    novo = [[None] * R.SIZE for _ in range(R.SIZE)]
    for x, y in cheios:
        nx, ny = x + dx, y + dy
        if 0 <= nx < R.SIZE and 0 <= ny < R.SIZE:
            novo[ny][nx] = buf[y][x]
    return novo


def main():
    rgb = reduzir(Image.open(ENTRADA))
    buf = limpar(para_paleta(rgb, tirar_fundo(rgb)))
    buf = encostar_no_chao(retocar(buf))
    img = R.to_image(buf)
    R.save_png(img, SAIDA)
    cheios = sum(1 for linha in buf for c in linha if c is not None)
    print(f'OK -> {SAIDA.relative_to(ROOT)}  ({cheios} px, caixa {img.getbbox()})')


if __name__ == '__main__':
    main()
