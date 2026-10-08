#!/usr/bin/env python3
"""Tira o chuvisco da arte do goblin sem mexer em forma nenhuma.

POR QUE ISTO EXISTE
-------------------
O goblin novo foi tirado de uma foto pequena e borrada (um JPEG de
64x64). A conversao foi fiel demais: trouxe junto o RUIDO do JPEG. A
cabeca tem 443 pixels pintados com SEIS tons de verde salpicados um
no outro — na tela isso nao le como volume, le como mancha. O goblin
antigo do jogo usava tres ou quatro tons em faixas limpas, e por isso
se enxergava o olho, a orelha e o braco.

O QUE ESTA LIMPEZA FAZ E O QUE ELA NAO FAZ
------------------------------------------
NAO muda forma, nem pose, nem silhueta, nem a paleta: nenhum pixel
muda de lugar, nenhum pixel aparece ou some, nenhuma cor nova entra.
O que muda e QUAL dos tons ja existentes ocupa cada pixel.

1. MEDIANA (3x3) sobre a rampa de tons, por material. A mediana e o
   filtro que o pixel art pede: ela apaga o ponto solto e NAO borra a
   fronteira entre claro e escuro (a media borraria). O contorno 'k',
   o branco do olho e o fundo ficam de fora, intocados.
2. PONTO SOLTO: um tom que nao se repete em nenhum vizinho vira o tom
   dominante da vizinhanca. E o chuvisco propriamente dito.
3. O ROSTO NAO E TOCADO. As celulas do rosto (olhos, pupila, boca)
   saem da limpeza por nome — e a parte que menos pode ser mexida.
"""

import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
import goblin_rig as R                                      # noqa: E402

# As rampas de tom, do escuro para o claro. A limpeza so compara tons
# DENTRO da mesma rampa: pele com pele, couro com couro. Misturar as
# duas pintaria a tunica de verde.
RAMPAS = (
    ('e', 'd', 'n', 'j', 'g', 'l'),      # pele
    ('B', 'b', 'h'),                     # couro
)
# Fora da limpeza: contorno, brilho do olho e aco da adaga. Sao traços
# de UM pixel por natureza; uma mediana os apagaria.
INTOCAVEIS = frozenset({'k', 'f', 'w', 'z', 'q', '.'})

INDICE = {}
for _r, _rampa in enumerate(RAMPAS):
    for _i, _c in enumerate(_rampa):
        INDICE[_c] = (_r, _i)


def _protegido(nome):
    """Celulas do rosto, em coordenadas da peca. Nao se toca nelas."""
    if nome != 'head':
        return set()
    return {(x, y) for _, cells in R.FACE_CELLS.items() for (x, y) in cells}


def limpa(grid, nome=''):
    """Devolve a peca com o chuvisco tirado. Mesma forma, mesma paleta."""
    alt, larg = len(grid), len(grid[0])
    protege = _protegido(nome)
    out = [list(linha) for linha in grid]

    for _ in range(2):
        base = [list(linha) for linha in out]
        for y in range(alt):
            for x in range(larg):
                c = base[y][x]
                if c in INTOCAVEIS or c not in INDICE or (x, y) in protege:
                    continue
                rampa, _ = INDICE[c]
                vizinhos = []
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if not (0 <= ny < alt and 0 <= nx < larg):
                            continue
                        v = base[ny][nx]
                        if v in INDICE and INDICE[v][0] == rampa:
                            vizinhos.append(INDICE[v][1])
                if len(vizinhos) < 5:
                    # borda da peca: pouca vizinhanca para julgar, e
                    # mexer ali e justamente o que deforma a silhueta
                    continue
                vizinhos.sort()
                mediana = vizinhos[len(vizinhos) // 2]
                out[y][x] = RAMPAS[rampa][mediana]
    return [''.join(linha) for linha in out]


def limpa_tudo():
    """{nome: peca limpa} para todas as partes do corpo."""
    return {nome: limpa(R.DEFAULT_PART[nome], nome)
            for nome in ('head', 'torso', 'arm_l', 'arm_r',
                         'leg_l', 'leg_r')}


def quantos_mudaram():
    total = 0
    for nome, novo in limpa_tudo().items():
        velho = R.DEFAULT_PART[nome]
        total += sum(1 for y, linha in enumerate(novo)
                     for x, c in enumerate(linha) if c != velho[y][x])
    return total


if __name__ == '__main__':
    novo = limpa_tudo()
    for nome, peca in novo.items():
        velho = R.DEFAULT_PART[nome]
        mud = sum(1 for y, linha in enumerate(peca)
                  for x, c in enumerate(linha) if c != velho[y][x])
        pintados = sum(1 for linha in velho for c in linha if c != '.')
        area_nova = sum(1 for linha in peca for c in linha if c != '.')
        assert area_nova == pintados, f'{nome}: a silhueta mudou!'
        print(f'  {nome:7s} {mud:4d} de {pintados} pixels trocaram de tom')
