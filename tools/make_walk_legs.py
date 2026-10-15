"""Gera os 8 quadros de caminhada de animais de quatro patas a partir do repouso (sem IA).

Só as patas se movem: as faixas de patas traseiras e dianteiras são deslocadas
horizontalmente, com o deslocamento crescendo do quadril (Y0) até as patas (FEET).
As duas faixas ficam em fases opostas, então corpo, cabeça e hastes não mudam.
Uso: python3 tools/make_walk_legs.py [veado|lebre|javali]   (sem argumento: todos)
"""
import math
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAID = ROOT / 'assets' / 'sprites' / 'raid'
AMP = 2  # deslocamento máximo, em px, nas patas

# faixas de colunas medidas no repouso (quadril = Y0, patas = FEET)
CONFIG = {
    'veado': dict(sprite='animal_deer', Y0=64, FEET=88, back=(8, 33), front=(40, 58), frames=16),
    'lebre': dict(sprite='animal_hare', Y0=55, FEET=62, back=(18, 40), front=(43, 59), frames=16),
    'javali': dict(sprite='animal_boar', Y0=57, FEET=73, back=(14, 48), front=(52, 80), frames=16),
    # Lobos e gêmeos: a base é o repouso já gerado (wolf_idle_0 etc.); a saída usa o mesmo prefixo.
    'lobo': dict(sprite='wolf_idle_0', out='wolf', Y0=25, FEET=31, back=(10, 22), front=(23, 35), frames=16, amp=3),
    'gemeo_mandibula': dict(sprite='twin_jaw_idle_0', out='twin_jaw', Y0=27, FEET=35, back=(11, 24), front=(26, 38), frames=16, amp=3),
    'gemeo_patas': dict(sprite='twin_paw_idle_0', out='twin_paw', Y0=26, FEET=35, back=(13, 25), front=(26, 41), frames=16, amp=3),
}


def shift_band(im, x0, x1, y0, dxf):
    """Desloca as colunas x0..x1 de cada linha y>=y0 por dxf(y) pixels."""
    out = im.copy()
    w, h = im.size
    src = im.load()
    dst = out.load()
    for y in range(y0, h):
        dx = round(dxf(y))
        row = [src[x, y] for x in range(x0, x1 + 1)]
        for x in range(x0, x1 + 1):
            dst[x, y] = (0, 0, 0, 0)
        for i, px in enumerate(row):
            nx = x0 + i + dx
            if 0 <= nx < w and px[3]:
                dst[nx, y] = px
    return out


def make(name):
    cfg = CONFIG[name]
    rest = Image.open(RAID / f"{cfg['sprite']}.png").convert('RGBA')
    span = cfg['FEET'] - cfg['Y0']

    def ramp(y):
        return min(1.0, max(0.0, (y - cfg['Y0']) / span))

    frames = cfg.get('frames', 8)
    for k in range(frames):
        phi = 2 * math.pi * k / frames
        amp = cfg.get('amp', AMP)
        back = lambda y, p=phi + math.pi: amp * math.sin(p) * ramp(y)
        front = lambda y, p=phi: amp * math.sin(p) * ramp(y)
        im = shift_band(rest, cfg['back'][0], cfg['back'][1], cfg['Y0'], back)
        im = shift_band(im, cfg['front'][0], cfg['front'][1], cfg['Y0'], front)
        out = RAID / f"{cfg.get('out', cfg['sprite'])}_walk_{k}.png"
        im.save(out)
    print(f"{name}: {frames} quadros em {RAID}")


if __name__ == '__main__':
    for n in (sys.argv[1:] or list(CONFIG)):
        make(n)
