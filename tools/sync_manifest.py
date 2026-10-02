#!/usr/bin/env python3
"""
sync_manifest.py — poe o assets/manifest.json de acordo com os arquivos.

O manifest e so a lista "id -> caminho" de todo PNG em assets/sprites. Como
o numero de quadros das animacoes mudou (a morte passou de 15 para 24) e
armas novas entraram, manter essa lista na mao vira fonte de erro: este
script le o disco e reescreve a lista inteira, em ordem estavel.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPR = ROOT / 'assets' / 'sprites'
MANIFEST = ROOT / 'assets' / 'manifest.json'


def main():
    sprites = [{'id': png.stem, 'path': png.relative_to(ROOT).as_posix()}
               for png in SPR.rglob('*.png')]
    sprites.sort(key=lambda e: e['id'])
    vistos = {}
    for e in sprites:
        if e['id'] in vistos:
            raise SystemExit(f"id duplicado: {e['id']} "
                             f"({vistos[e['id']]} e {e['path']})")
        vistos[e['id']] = e['path']
    antes = len(json.loads(MANIFEST.read_text(encoding='utf-8'))['sprites'])
    MANIFEST.write_text(json.dumps({'sprites': sprites}, ensure_ascii=False,
                                   indent=2) + '\n', encoding='utf-8')
    print(f'manifest: {antes} -> {len(sprites)} sprites')


if __name__ == '__main__':
    main()
