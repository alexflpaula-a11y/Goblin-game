#!/usr/bin/env python3
"""
build_singlefile.py — Gera o build jogável de ARQUIVO ÚNICO.

Pega a fonte modular (index-dev.html + css/ + js/ + assets/) e produz
`vila-de-goblins-jogavel.html`: um HTML só, com CSS, sprites (base64),
JSONs e todos os módulos JS embutidos. Funciona offline, aberto direto
do disco (file://), sem servidor e sem dependências.

Uso:  python3 tools/build_singlefile.py
"""
import base64
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'vila-de-goblins-jogavel.html')


def read(path, binary=False):
    full = os.path.join(ROOT, path)
    if binary:
        return open(full, 'rb').read()
    return open(full, encoding='utf-8').read()


def main():
    # ---------- 1. Sprites → data URIs ----------
    manifest = json.loads(read('assets/manifest.json'))
    sprites = {}
    for entry in manifest['sprites']:
        raw = read(entry['path'], binary=True)
        b64 = base64.b64encode(raw).decode('ascii')
        sprites[entry['id']] = 'data:image/png;base64,' + b64

    # ---------- 2. JSONs de dados ----------
    embedded = {
        'sprites': sprites,
        'i18n': {
            'pt-BR': json.loads(read('assets/data/i18n.pt-br.json')),
            'en': json.loads(read('assets/data/i18n.en.json')),
        },
        'balance': json.loads(read('assets/data/balance.json')),
    }

    # ---------- 3. Módulos JS ----------
    order = json.loads(read('js/_order.json'))
    parts = []
    for name in order:
        body = read(f'js/{name}')
        # No build todos os módulos vivem no mesmo escopo: o require
        # interno vira __require para não colidir com nada da página.
        body = body.replace("require('", "__require('")
        parts.append(
            f"__define('{name}', function(module, exports, require){{\n{body}\n}});")
    modules_js = '\n'.join(parts)

    loader_js = """
var __modules = {}, __cache = {};
function __define(n, f) { __modules[n] = f; }
function __require(n) {
  if (!__cache[n]) {
    var m = { exports: {} };
    __cache[n] = m;
    __modules[n](m, m.exports, __require);
  }
  return __cache[n].exports;
}
""".strip()

    # ---------- 4. Monta o HTML ----------
    css = read('css/style.css')
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
<meta name="theme-color" content="#16121f" />
<title>Vila de Goblins</title>
<style>
{css}
</style>
</head>
<body>
<div id="viewport">
  <canvas id="game"></canvas>
  <header id="hud">
    <button id="settingsBtn" type="button" aria-label="Configurações">⚙️</button>
  </header>

  <div id="settingsModal" class="hidden" role="dialog" aria-modal="true">
    <div id="settingsPanel">
      <div id="settingsHead">
        <span id="settingsTitle">Configurações</span>
        <button id="settingsClose" type="button" aria-label="Fechar">✕</button>
      </div>
      <div class="settings-row">
        <span id="settingsLangLabel">Idioma</span>
        <div id="langToggle">
          <button id="langPt" type="button" class="lang-opt">🇧🇷 PT</button>
          <button id="langEn" type="button" class="lang-opt">🇬🇧 EN</button>
        </div>
      </div>
    </div>
  </div>

  <div id="status"></div>
</div>
<script>
window.EMBEDDED = {json.dumps(embedded, ensure_ascii=False)};
</script>
<script>
{loader_js}
{modules_js}
__require('main.js');
</script>
</body>
</html>
"""
    open(OUT, 'w', encoding='utf-8').write(html)
    kb = len(html.encode('utf-8')) / 1024
    print(f'OK → {os.path.relpath(OUT, ROOT)}  ({kb:.0f} KB, '
          f'{len(sprites)} sprites, {len(order)} módulos)')


if __name__ == '__main__':
    main()
