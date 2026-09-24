#!/usr/bin/env python3
"""
unbuild.py — Reconstrói o projeto-fonte a partir do build de arquivo único.

O `release/vila-de-goblins-jogavel.html` é um build gerado por
`tools/build_singlefile.py`: ele embute CSS, sprites (base64), JSONs e todos
os módulos JS num HTML só. Este script faz o caminho inverso, recriando a
árvore de código descrita no planejamento:

    index.html · css/style.css · js/*.js
    assets/manifest.json · assets/data/*.json · assets/sprites/**/*.png

Uso (uma vez só, para recuperar a fonte):  python3 tools/unbuild.py
"""
import base64
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'vila-de-goblins-jogavel.html')

# Em qual pasta cada prefixo de sprite mora (convenção do planejamento, §4.2)
SPRITE_DIRS = {
    'goblin': 'goblins',
    'gnome': 'goblins',
    'building': 'buildings',
    'item': 'items',
    'res': 'resources',
    'node': 'nodes',
    'tile': 'tiles',
    'ui': 'ui',
    'enemy': 'enemies',
    'boss': 'bosses',
    'fx': 'fx',
    'misc': 'misc',
}


def write(path, content, binary=False):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    mode = 'wb' if binary else 'w'
    with open(full, mode, **({} if binary else {'encoding': 'utf-8'})) as f:
        f.write(content)
    return full


def main():
    if not os.path.exists(SRC):
        sys.exit(f'não encontrei {SRC}')
    html = open(SRC, encoding='utf-8').read()

    # ---------- 1. EMBEDDED (sprites + i18n + balance) ----------
    i = html.index('window.EMBEDDED = ') + len('window.EMBEDDED = ')
    embedded, _ = json.JSONDecoder().raw_decode(html[i:])

    n_spr = 0
    manifest = {'sprites': []}
    for sid, datauri in sorted(embedded['sprites'].items()):
        prefix = sid.split('_')[0]
        folder = SPRITE_DIRS.get(prefix, 'misc')
        path = f'assets/sprites/{folder}/{sid}.png'
        b64 = datauri.split(',', 1)[1]
        write(path, base64.b64decode(b64), binary=True)
        manifest['sprites'].append({'id': sid, 'path': path})
        n_spr += 1
    write('assets/manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(f'  {n_spr} sprites → assets/sprites/**')

    for lang, table in embedded['i18n'].items():
        name = 'i18n.pt-br.json' if lang == 'pt-BR' else f'i18n.{lang}.json'
        write(f'assets/data/{name}', json.dumps(table, indent=2, ensure_ascii=False) + '\n')
        print(f'  {len(table)} textos → assets/data/{name}')

    write('assets/data/balance.json',
          json.dumps(embedded['balance'], indent=2, ensure_ascii=False) + '\n')
    print('  balance → assets/data/balance.json')

    # ---------- 2. CSS ----------
    css = re.search(r'<style>\n(.*?)</style>', html, re.S).group(1)
    write('css/style.css', css.strip() + '\n')
    print('  css/style.css')

    # ---------- 3. Módulos JS ----------
    # Formato no build, um bloco por módulo:
    #   __define('nome.js', function(module, exports, require){
    #   <corpo>
    #   });
    # Cuidado: o corpo contém vários "});" (callbacks), então NÃO dá para
    # usar regex não-gulosa até o primeiro fechamento — isso truncava o
    # main.js no primeiro addEventListener. Separamos pelos cabeçalhos.
    header = re.compile(
        r"^__define\('([^']+)', function\(module, exports, require\)\{$",
        re.M)
    marks = [(m.group(1), m.start(), m.end()) for m in header.finditer(html)]
    if not marks:
        sys.exit('nenhum módulo encontrado no build')

    order = []
    for idx, (name, _start, body_from) in enumerate(marks):
        # o corpo vai até o cabeçalho do próximo módulo (ou até o
        # __require('main.js') final, no caso do último)
        if idx + 1 < len(marks):
            body_to = marks[idx + 1][1]
        else:
            body_to = html.index("__require('main.js');", body_from)
        body = html[body_from:body_to]
        # tira o "});" que fecha o __define
        body = body.rstrip()
        if not body.endswith('});'):
            sys.exit(f'módulo {name} não termina como esperado')
        body = body[:-3].rstrip()
        # dentro dos módulos o build troca require( por __require(  → desfaz
        body = body.replace('__require(', 'require(')
        write(f'js/{name}', body.strip() + '\n')
        order.append(name)
        print(f'  js/{name}')
    write('js/_order.json', json.dumps(order, indent=2) + '\n')

    # ---------- 4. index.html ----------
    head = html[:html.index('<style>')]
    body = html[html.index('</style>') + len('</style>'):html.index('<script>')]
    body = body.replace('</head>\n', '')
    scripts = '\n'.join(f'<script src="js/{n}" data-module="{n}"></script>' for n in order)
    index = (head
             + '<link rel="stylesheet" href="css/style.css" />\n</head>'
             + body
             + '<script src="js/loader.js"></script>\n'
             + scripts
             + '\n<script>__require(\'main.js\');</script>\n</body>\n</html>\n')
    write('index.html', index)
    print('  index.html')
    print(f'\nOK — {len(order)} módulos recuperados.')


if __name__ == '__main__':
    main()
