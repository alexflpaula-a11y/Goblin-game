#!/usr/bin/env python3
"""auditoria_encaixe.py — confere se o sprite novo cai no MESMO lugar que o antigo.

O jogo ancora prédios em (x, y) com a caixa 64x64 terminando em y (village.js
desenha s.y-60), e nós com 48x48 ancorados pela base. Se o novo render tiver
margem diferente embaixo, do lado ou proporção diferente, a estrutura flutua,
afunda ou desalinha em relação às vizinhas.

Mede, para o sprite antigo e o novo:
  • bbox do conteúdo;
  • folga inferior (px vazios abaixo do conteúdo) — é o que faz flutuar/afundar;
  • centro horizontal do conteúdo vs centro da caixa;
  • largura/altura do conteúdo.

Uso: python3 tools/auditoria_encaixe.py [--base REV]
"""
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ITEMS = [
    ('buildings/building_house_1.png', 64),
    ('buildings/building_ferraria_1.png', 64),
    ('buildings/building_altar_1.png', 64),
    ('buildings/building_armazem_1.png', 64),
    ('buildings/building_bazar_1.png', 64),
    ('buildings/building_cozinha_1.png', 64),
    ('buildings/building_estabulo_1.png', 64),
    ('buildings/building_fazenda_1.png', 64),
    ('buildings/building_mercado_1.png', 64),
    ('buildings/building_porto_1.png', 64),
    ('buildings/building_quartel_1.png', 64),
    ('buildings/building_questboard_1.png', 64),
    ('nodes/node_tree_0.png', 48),
    ('nodes/node_rock_0.png', 48),
]
BASE_REV = 'e565e0b'


def metrics(img, native):
    img = img.convert('RGBA')
    if img.size != (native, native):
        img = img.resize((native, native), Image.LANCZOS)
    a = img.split()[3]
    bbox = a.getbbox()
    if not bbox:
        return None
    x0, y0, x1, y1 = bbox
    return {
        'w': x1 - x0, 'h': y1 - y0,
        'bottom_gap': native - y1,
        'side_gap_min': min(x0, native - x1),
        'cx_off': ((x0 + x1) / 2) - native / 2,
    }


def load_old(rel):
    data = subprocess.check_output(['git', 'show', f'{BASE_REV}:assets/sprites/{rel}'], cwd=ROOT)
    from io import BytesIO
    return Image.open(BytesIO(data))


def main():
    print(f'{"sprite":38s} {"folga inferior":>18s} {"centro":>16s} {"tamanho":>16s}')
    print(f'{"":38s} {"antes→depois":>18s} {"antes→depois":>16s} {"antes→depois":>16s}')
    problems = []
    for rel, native in ITEMS:
        old = metrics(load_old(rel), native)
        new = metrics(Image.open(os.path.join(ROOT, 'assets', 'sprites', rel)), native)
        if not old or not new:
            problems.append(f'{rel}: sprite vazio')
            continue
        db = new['bottom_gap'] - old['bottom_gap']
        dc = new['cx_off'] - old['cx_off']
        dh = new['h'] - old['h']
        dw = new['w'] - old['w']
        name = rel.replace('buildings/', '').replace('nodes/', '').replace('.png', '')
        print(f'{name:38s} {old["bottom_gap"]:>3d} → {new["bottom_gap"]:<3d} ({db:+d})   '
              f'{old["cx_off"]:>+5.1f} → {new["cx_off"]:<+5.1f} ({dc:+.1f})   '
              f'{old["w"]}x{old["h"]} → {new["w"]}x{new["h"]}')
        # critérios de encaixe
        if abs(db) > 1:
            problems.append(f'{name}: folga inferior mudou {db:+d}px (flutua/afunda)')
        if abs(dc) > 1.5:
            problems.append(f'{name}: centro horizontal deslocado {dc:+.1f}px')
        # estruturas baixas por natureza (balcão, pier, placa) não são erro
        if new['h'] < native * 0.70:
            problems.append(f'{name}: altura {new["h"]}px em caixa de {native} (pequeno demais)')
        if new['w'] > native:
            problems.append(f'{name}: largura {new["w"]}px estoura a caixa de {native}')
    print()
    if problems:
        print('PROBLEMAS:')
        for p in problems:
            print('  ✗', p)
    else:
        print('encaixe OK: base, centro e tamanho compatíveis com a arte antiga')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
