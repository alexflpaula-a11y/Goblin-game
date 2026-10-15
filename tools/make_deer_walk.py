"""Gera os 8 quadros de caminhada do veado a partir do repouso (sem IA).

Só as pernas se movem: as faixas das pernas traseiras e dianteiras são deslocadas
horizontalmente, com o deslocamento crescendo do quadril (y=Y0) até os cascos.
As duas faixas ficam em fases opostas, então o corpo, a cabeça e as hastes
não mudam. Uso: python3 tools/make_deer_walk.py
"""
import math
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAID = ROOT / 'assets' / 'sprites' / 'raid'
Y0 = 64            # linha do quadril: acima dela nada se move
AMP = 2            # deslocamento máximo, em px, no casco
FRAMES = 8
# faixas de colunas medidas no repouso (pernas traseiras e dianteiras)
BACK = (8, 33)
FRONT = (40, 58)


def shift_band(im, x0, x1, dxf):
    """Desloca as colunas x0..x1 de cada linha y>=Y0 por dxf(y) pixels."""
    out = im.copy()
    w, h = im.size
    src = im.load()
    dst = out.load()
    for y in range(Y0, h):
        dx = round(dxf(y))
        row = [src[x, y] for x in range(x0, x1 + 1)]
        for x in range(x0, x1 + 1):
            dst[x, y] = (0, 0, 0, 0)
        for i, px in enumerate(row):
            nx = x0 + i + dx
            if 0 <= nx < w and px[3]:
                dst[nx, y] = px
    return out


def main():
    rest = Image.open(RAID / 'animal_deer.png').convert('RGBA')
    h = rest.height
    for k in range(FRAMES):
        phi = 2 * math.pi * k / FRAMES
        ramp = lambda y: (y - Y0) / (h - 1 - Y0)
        back = lambda y, p=phi + math.pi: AMP * math.sin(p) * ramp(y)
        front = lambda y, p=phi: AMP * math.sin(p) * ramp(y)
        im = shift_band(rest, BACK[0], BACK[1], back)
        im = shift_band(im, FRONT[0], FRONT[1], front)
        out = RAID / f'animal_deer_walk_{k}.png'
        im.save(out)
        print('wrote', out.name)


if __name__ == '__main__':
    main()
