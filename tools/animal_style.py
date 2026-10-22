#!/usr/bin/env python3
"""animal_style.py — Acabamento das estruturas no estilo dos animais do jogo.

Os animais (javali, cervo, lebre, lobo) são low-poly IA: centenas/milhares de
cores, facetas com gradiente suave, sem contorno preto, sombra funda e luz
quente. As estruturas antigas eram pixel art chapada (16-30 cores, traço
preto). Este módulo deixa o render novo com a MESMA leitura dos animais.

Alvos calibrados medindo os sprites dos animais (rodar --measure).
"""
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ASSETS = os.path.join(ROOT, 'assets', 'sprites')

TARGETS = {'lum_p10': 28.0, 'lum_p50': 78.0, 'lum_p90': 128.0, 'sat': 0.62}


def stats(img):
    a = np.asarray(img.convert('RGBA')).astype(np.float32)
    op = a[..., 3] > 128
    if not op.any():
        return None
    rgb = a[..., :3][op]
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    mx, mn = rgb.max(1), rgb.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    return {'lum_p10': float(np.percentile(lum, 10)), 'lum_p50': float(np.median(lum)),
            'lum_p90': float(np.percentile(lum, 90)), 'sat': float(np.median(sat)),
            'colors': int(len(np.unique(rgb.astype(np.uint8), axis=0)))}


def dissolve_outline(img, thresh=72, amount=0.55):
    """Dissolve o traço preto: os animais não têm contorno chapado."""
    a = np.asarray(img.convert('RGBA')).astype(np.float32)
    rgb = a[..., :3].copy()
    alpha = a[..., 3].copy()
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    mask = (lum < thresh) & (alpha > 100)
    if mask.any():
        acc = np.zeros_like(rgb)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    acc += np.roll(np.roll(rgb, dy, 0), dx, 1)
        rgb = np.where(mask[:, :, None], rgb * (1 - amount) + (acc / 8.0) * amount, rgb)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), 'RGBA')


def match_tone(img, stone=False, warmth=1.0):
    """Leva sombra/luz/saturação para os alvos dos animais."""
    t = dict(TARGETS)
    a = np.asarray(img.convert('RGBA')).astype(np.float32)
    rgb, alpha = a[..., :3].copy(), a[..., 3].copy()
    m = stats(img)
    lum = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lo = t['lum_p10'] * (1.6 if stone else 1.0)
    hi = t['lum_p90']
    if m['lum_p90'] - m['lum_p10'] > 1:
        lum2 = (lum - m['lum_p10']) * (hi - lo) / (m['lum_p90'] - m['lum_p10']) + lo
        rgb = rgb * np.where(lum > 1, lum2 / np.maximum(lum, 1), 1.0)[..., None]
    cur = stats(Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), 'RGBA'))
    want = t['sat'] * (0.34 if stone else 1.0)
    if cur and cur['sat'] > 0.01:
        k = max(0.6, min(2.2, want / cur['sat']))
        grey = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        rgb = grey[..., None] + (rgb - grey[..., None]) * k
    l = np.clip((rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)) / 255.0, 0, 1)
    shadow = np.array([1.13, 0.94, 0.83], dtype=np.float32)
    light = np.array([1.04, 1.01, 0.95], dtype=np.float32)
    tint = shadow + (light - shadow) * l[..., None]
    rgb = rgb * (1.0 - 0.22 * warmth + 0.22 * warmth * tint)
    return Image.fromarray(np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8), 'RGBA')


def finish(img, stone=False, warmth=1.0, blur=0.2):
    out = dissolve_outline(img)
    out = match_tone(out, stone=stone, warmth=warmth)
    return out.filter(ImageFilter.GaussianBlur(blur)) if blur else out


def measure():
    print(f'{"sprite":10s} {"p10":>4s} {"p50":>4s} {"p90":>4s} {"sat":>5s} {"cores":>6s}')
    for name, path in [('javali', 'raid/animal_boar.png'), ('cervo', 'raid/animal_deer.png'),
                       ('lebre', 'raid/animal_hare.png'), ('lobo', 'raid/wolf_idle_0.png')]:
        s = stats(Image.open(os.path.join(ASSETS, path)))
        print(f'{name:10s} {s["lum_p10"]:4.0f} {s["lum_p50"]:4.0f} {s["lum_p90"]:4.0f} '
              f'{s["sat"]:5.2f} {s["colors"]:6d}')


if __name__ == '__main__':
    measure() if '--measure' in sys.argv else print(__doc__)
