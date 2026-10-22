#!/usr/bin/env python3
"""lowpoly_harmonize.py — unifica a paleta de um lote com a arte já aprovada.

Problema: cada render da IA escolhe sozinho a saturação e a temperatura das
cores, então os prédios parecem de jogos diferentes mesmo com as mesmas
facetas low-poly.

Solução: monta UMA paleta comum a partir dos sprites já aprovados (casa,
ferraria, árvore e pedra) somados ao lote, e re-quantiza todos os sprites do
lote nessa paleta. As matizes de cada peça continuam lá (a paleta contém as
cores do próprio lote), mas o vocabulário de cor passa a ser o mesmo.

Uso:
    python3 tools/lowpoly_harmonize.py altar armazem bar ...
    python3 tools/lowpoly_harmonize.py --palette 48 altar armazem ...
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
PREVIEW = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')

# sprites aprovados que definem o tom do jogo
REFERENCE = [
    os.path.join(ROOT, 'assets', 'sprites', 'buildings', 'building_house_1.png'),
    os.path.join(ROOT, 'assets', 'sprites', 'buildings', 'building_ferraria_1.png'),
    os.path.join(ROOT, 'assets', 'sprites', 'nodes', 'node_tree_0.png'),
    os.path.join(ROOT, 'assets', 'sprites', 'nodes', 'node_rock_0.png'),
]


def opaque_pixels(img):
    """Lista (r, g, b) dos pixels com alpha alto."""
    px = img.convert('RGBA').load()
    out = []
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a > 200:
                out.append((r, g, b))
    return out


def build_palette(files, colors):
    """Paleta única: quantiza o conjunto todo de uma vez."""
    pixels = []
    for path in files:
        pixels.extend(opaque_pixels(Image.open(path)))
    strip = Image.new('RGB', (len(pixels), 1))
    strip.putdata(pixels)
    pal_img = strip.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = pal_img.getpalette()[:colors * 3]
    return [tuple(pal[i:i + 3]) for i in range(0, len(pal), 3)]


def apply_palette(img, palette):
    """Mapeia cada pixel opaco para a cor mais próxima da paleta comum."""
    rgba = img.convert('RGBA')
    px = rgba.load()
    cache = {}
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = px[x, y]
            if a <= 8:
                px[x, y] = (0, 0, 0, 0)
                continue
            key = (r, g, b)
            np_ = cache.get(key)
            if np_ is None:
                np_ = min(palette, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2)
                cache[key] = np_
            px[x, y] = (np_[0], np_[1], np_[2], a)
    return rgba


def main():
    args = sys.argv[1:]
    colors = 48
    if '--palette' in args:
        i = args.index('--palette')
        colors = int(args[i + 1])
        del args[i:i + 2]
    if not args:
        print('uso: python3 tools/lowpoly_harmonize.py [--palette N] ids...')
        return

    files = [p for p in REFERENCE if os.path.exists(p)]
    paths = {name: os.path.join(CAND, name + '.png') for name in args}
    files += [p for p in paths.values() if os.path.exists(p)]
    palette = build_palette(files, colors)
    print(f'paleta comum: {len(palette)} cores (de {len(files)} sprites)')

    for name, path in paths.items():
        if not os.path.exists(path):
            print(f'! {name}: sem candidato')
            continue
        out = apply_palette(Image.open(path), palette)
        out.save(path)
        print(f'✓ {name:11s} harmonizado')


if __name__ == '__main__':
    main()
