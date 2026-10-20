#!/usr/bin/env python3
"""
lowpoly_sprites.py — Prepara os renders low-poly da IA para o jogo.

Os originais gerados por IA ficam em `art-source/lowpoly-village/raw/` com
fundo magenta chapado (chroma key). Este script:

  1. remove o magenta (alpha suave nas bordas + despill, sem franja roxa);
  2. corta no conteúdo real;
  3. reduz para a caixa do jogo com LANCZOS em alpha pré-multiplicado;
  4. grava o PNG em `art-source/lowpoly-village/candidates/` (staging);
  5. monta uma folha de conferência ampliada (x4) sobre a grama do jogo.

Nada é publicado no jogo sem aprovação: para copiar os candidatos aprovados
para `assets/sprites/`, rode com `--publish`.

Uso:
    python3 tools/lowpoly_sprites.py                  # processa todos
    python3 tools/lowpoly_sprites.py house ferraria   # só alguns ids
    python3 tools/lowpoly_sprites.py --publish        # publica os aprovados

Requer Pillow e numpy (pip install pillow numpy).
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'raw')
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
OUT = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'preview')

GRASS = (90, 164, 99, 255)  # COLORS.ground do world.js, para a conferência

# box = tamanho NATIVO com que o jogo desenha o sprite, para o mapeamento de
# pixel ser 1:1 (o canvas não usa suavização):
#   prédios  -> 64x64, apoiados 1 px acima do pé (a pixel art antiga
#               deixava essa folga, então a base cai na mesma linha do chão)
#   nós      -> 48x48  (nodes.js desenha 48x48, ancorado pela base)
#   restos   -> 24x24  (tocos e entulho são desenhados em 24x24)
#   raid     -> toca 52x34, colmeia 32x40, baú 24x24 (raid.js)
#   divindade-> 72x72  (deities.js desenha 72x72)
ASSETS = {
    'house':      {'src': 'house.png',      'dst': 'assets/sprites/buildings/building_house_1.png',      'box': (64, 64), 'gap': 1},
    'ferraria':   {'src': 'ferraria.png',   'dst': 'assets/sprites/buildings/building_ferraria_1.png',   'box': (64, 64), 'gap': 1},
    'altar':      {'src': 'altar.png',      'dst': 'assets/sprites/buildings/building_altar_1.png',      'box': (64, 64), 'gap': 1},
    'armazem':    {'src': 'armazem.png',    'dst': 'assets/sprites/buildings/building_armazem_1.png',    'box': (64, 64), 'gap': 1},
    'bar':        {'src': 'bar.png',        'dst': 'assets/sprites/buildings/building_bazar_1.png',      'box': (64, 64), 'gap': 1},
    'bazar':      {'src': 'bar.png',        'dst': 'assets/sprites/buildings/building_bazar_1.png',      'box': (64, 64), 'gap': 1},
    'cozinha':    {'src': 'cozinha.png',    'dst': 'assets/sprites/buildings/building_cozinha_1.png',    'box': (64, 64), 'gap': 1},
    'estabulo':   {'src': 'estabulo.png',   'dst': 'assets/sprites/buildings/building_estabulo_1.png',   'box': (64, 64), 'gap': 1},
    'fazenda':    {'src': 'fazenda.png',    'dst': 'assets/sprites/buildings/building_fazenda_1.png',    'box': (64, 64), 'gap': 1},
    'mercado':    {'src': 'mercado.png',    'dst': 'assets/sprites/buildings/building_mercado_1.png',    'box': (64, 64), 'gap': 1},
    'porto':      {'src': 'porto.png',      'dst': 'assets/sprites/buildings/building_porto_1.png',      'box': (64, 64), 'gap': 1},
    'quartel':    {'src': 'quartel.png',    'dst': 'assets/sprites/buildings/building_quartel_1.png',    'box': (64, 64), 'gap': 1},
    'questboard': {'src': 'questboard.png', 'dst': 'assets/sprites/buildings/building_questboard_1.png', 'box': (64, 64), 'gap': 1},










    # --- lote 03: divindades, raid e restos ---
    'grande_arvore':     {'src': 'grande_arvore.png',     'dst': 'assets/sprites/deities/building_grande_arvore_1.png', 'box': (64, 64)},
    'golem_pedra':       {'src': 'golem_pedra.png',       'dst': 'assets/sprites/deities/building_golem_pedra_1.png',   'box': (64, 64)},
    'tree_sing_0':       {'src': 'tree_sing_0.png',       'dst': 'assets/sprites/deities/deity_tree_sing_0.png',        'box': (64, 64)},
    'tree_sing_1':       {'src': 'tree_sing_1.png',       'dst': 'assets/sprites/deities/deity_tree_sing_1.png',        'box': (64, 64)},
    'tree_sing_2':       {'src': 'tree_sing_2.png',       'dst': 'assets/sprites/deities/deity_tree_sing_2.png',        'box': (64, 64)},
    'fx_notas':          {'src': 'fx_notas.png',          'dst': 'assets/sprites/deities/fx_notas.png',                 'box': (24, 24)},
    'chest_open_1':      {'src': 'chest_open_1.png',      'dst': 'assets/sprites/raid/chest_open_1.png',                'box': (24, 24)},
    'chest_open_2':      {'src': 'chest_open_2.png',      'dst': 'assets/sprites/raid/chest_open_2.png',                'box': (24, 24)},
    'node_tree_stump':   {'src': 'node_tree_stump.png',   'dst': 'assets/sprites/nodes/node_tree_stump.png',            'box': (24, 24)},
    'node_rock_rubble':  {'src': 'node_rock_rubble.png',  'dst': 'assets/sprites/nodes/node_rock_rubble.png',           'box': (24, 24)},
    'prop_den':          {'src': 'prop_den.png',          'dst': 'assets/sprites/raid/prop_den.png',                    'box': (52, 34)},
    'prop_hive':         {'src': 'prop_hive.png',         'dst': 'assets/sprites/raid/prop_hive.png',                   'box': (32, 40)},
    'chest_closed':      {'src': 'chest_closed.png',      'dst': 'assets/sprites/raid/chest_closed.png',                'box': (24, 24)},
    'serraria':          {'src': 'serraria.png',          'dst': 'assets/sprites/buildings/building_serraria_1.png',     'box': (64, 64), 'gap': 1},
    'construction_1':    {'src': 'construction_1.png',    'dst': 'assets/sprites/buildings/building_construction_1.png', 'box': (64, 64), 'gap': 1},
    'construction_site': {'src': 'construction_site.png', 'dst': 'assets/sprites/buildings/building_construction_site.png', 'box': (64, 64), 'gap': 1},
    'node_tree':  {'src': 'node_tree.png',  'dst': 'assets/sprites/nodes/node_tree_0.png',                'box': (48, 48)},
    'node_rock':  {'src': 'node_rock.png',  'dst': 'assets/sprites/nodes/node_rock_0.png',                'box': (48, 48)},
}


def key_color(arr):
    """Cor do fundo: mediana do anel de 3 px na borda (só o magenta chapado)."""
    ring = np.concatenate([
        arr[:3, :, :].reshape(-1, 3), arr[-3:, :, :].reshape(-1, 3),
        arr[:, :3, :].reshape(-1, 3), arr[:, -3:, :].reshape(-1, 3),
    ])
    return np.median(ring, axis=0)


def remove_chroma(img):
    """Alpha pela distância ao magenta + despill do roxo nas bordas."""
    arr = np.asarray(img.convert('RGB'), dtype=np.float32)
    key = key_color(arr)
    dist = np.linalg.norm(arr - key, axis=2)

    # 0 = fundo, 1 = objeto. O degradê cobre o antialias da IA.
    alpha = np.clip((dist - 26.0) / (78.0 - 26.0), 0.0, 1.0)
    # Magenta puro nunca sobrevive; sombras coloridas sim.
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    magentaish = (r > 110) & (b > 110) & (g < np.minimum(r, b) * 0.72)
    alpha = np.where(magentaish & (dist < 150.0), 0.0, alpha)

    a = alpha[:, :, None]
    # Desmistura: tira o resto de magenta das bordas sem escurecer o objeto.
    safe = np.maximum(a, 1e-4)
    rgb = np.clip((arr - (1.0 - a) * key) / safe, 0, 255)

    # Despill final: mesmo depois da desmistura sobra um roxo fraco nas bordas
    # semitransparentes (r e b altos com g baixo). Aqui o excesso de magenta é
    # subtraído dos dois canais, o que devolve o cinza/madeira da borda.
    fr, fg, fb = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    excess = np.maximum(0.0, np.minimum(fr, fb) - fg)
    rgb = np.dstack([np.clip(fr - excess, 0, 255), fg, np.clip(fb - excess, 0, 255)])
    # Pixel quase transparente e ainda arroxeado vira transparente de vez.
    still_purple = (rgb[:, :, 0] > rgb[:, :, 1] * 1.55) & (rgb[:, :, 2] > rgb[:, :, 1] * 1.35)
    alpha = np.where(still_purple & (alpha < 0.85), 0.0, alpha)
    alpha = np.where(alpha < 0.06, 0.0, alpha)

    return Image.fromarray(np.dstack([rgb, alpha * 255.0]).astype(np.uint8), 'RGBA')


def resize_rgba(img, box, gap=0):
    """Corta no conteúdo e reduz para a caixa, apoiado a `gap` px do pé."""
    bbox = img.split()[3].getbbox()
    if bbox:
        img = img.crop(bbox)
    bw, bh = img.size
    scale = min(box[0] / bw, box[1] / bh)
    tw, th = max(1, round(bw * scale)), max(1, round(bh * scale))

    # LANCZOS em alpha pré-multiplicado: evita halo escuro/claro na borda.
    arr = np.asarray(img, dtype=np.float32) / 255.0
    a = arr[:, :, 3:4]
    pm = np.dstack([arr[:, :, :3] * a, a])
    pm_img = Image.fromarray((pm * 255.0).round().astype(np.uint8), 'RGBA')
    pm_small = np.asarray(pm_img.resize((tw, th), Image.LANCZOS), dtype=np.float32) / 255.0
    a2 = pm_small[:, :, 3:4]
    rgb2 = np.divide(pm_small[:, :, :3], np.maximum(a2, 1e-4))
    small = np.dstack([np.clip(rgb2, 0, 1), a2])
    sprite = Image.fromarray((small * 255.0).round().astype(np.uint8), 'RGBA')

    canvas = Image.new('RGBA', box, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, ((box[0] - tw) // 2, box[1] - th - gap))
    return canvas


def crisp(img, colors=40):
    """Acabamento aprovado (variante C): nitidez, cor e paleta curta.

    Em 64 px as facetas do render ficam macias; o unsharp devolve a quina,
    a saturação compensa a perda do downscale e a quantização deixa os
    planos chapados como nos lobos/javali do jogo.
    """
    alpha = img.split()[3]
    out = img.filter(ImageFilter.UnsharpMask(radius=0.9, percent=160, threshold=2))
    out = ImageEnhance.Color(out.convert('RGB')).enhance(1.12)
    out = ImageEnhance.Contrast(out).enhance(1.05)
    out = out.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE).convert('RGBA')
    out.putalpha(alpha)
    return out


def candidate_path(name):
    return os.path.join(CAND, name + '.png')


def build_preview(entries, path):
    """Folha x4 sobre grama, lado a lado, para aprovação visual."""
    pad, scale, label = 14, 4, 20
    cell_w = max(ASSETS[e]['box'][0] for e in entries) * scale + pad * 2
    cell_h = max(ASSETS[e]['box'][1] for e in entries) * scale + pad * 2 + label
    sheet = Image.new('RGBA', (cell_w * len(entries), cell_h), GRASS)
    for i, name in enumerate(entries):
        p = candidate_path(name)
        if not os.path.exists(p):
            continue
        spr = Image.open(p).convert('RGBA')
        big = spr.resize((spr.width * scale, spr.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (i * cell_w + pad, pad))
    sheet.save(path)
    return path


def publish(names):
    for name in names:
        src = candidate_path(name)
        if not os.path.exists(src):
            print(f'! {name}: sem candidato')
            continue
        dst = os.path.join(ROOT, ASSETS[name]['dst'])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        print(f'↗ {name:12s} -> {ASSETS[name]["dst"]}')


def main():
    args = sys.argv[1:]
    if '--publish' in args:
        publish([n for n in ASSETS if not (set(args) - {'--publish'})] if len(args) == 1
                else [a for a in args if a != '--publish'])
        return

    only = set(args)
    names = [n for n in ASSETS if not only or n in only]
    os.makedirs(CAND, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)
    done = []
    for name in names:
        spec = ASSETS[name]
        src = os.path.join(RAW, spec['src'])
        if not os.path.exists(src):
            print(f'! {name}: falta {spec["src"]}')
            continue
        sprite = crisp(resize_rgba(remove_chroma(Image.open(src)), spec['box'], spec.get('gap', 0)))
        sprite.save(candidate_path(name))
        done.append(name)
        print(f'✓ {name:12s} -> candidates/{name}.png  {sprite.size[0]}x{sprite.size[1]}')
    if done:
        sheet = build_preview(done, os.path.join(OUT, 'conferencia.png'))
        print(f'✓ folha de conferência: {os.path.relpath(sheet, ROOT)}')


if __name__ == '__main__':
    main()
