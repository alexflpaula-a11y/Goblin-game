#!/usr/bin/env python3
"""
Gera os sprites jogáveis das 45 variações de goblin fornecidas como GIF.

Cada GIF é uma prévia 413x292 com cinco animações 32x32 ampliadas em 4x:
idle, walk, attack, hurt e death. A prévia tem 40 quadros e foi montada a
partir das mesmas poses do goblin base. Este script desfaz essa montagem,
remove o fundo/sombra, restaura o alinhamento e exporta os 62 quadros usados
pelo jogo.

As variações são deliberadamente processadas em lotes de cinco. Além delas,
o script cria overlays pequenos das skins de equipamento. Assim, uma cicatriz,
tatuagem ou outra característica continua visível quando o goblin veste uma
peça, sem gerar 45 x 8 combinações completas.

Requer Pillow (a mesma dependência dos geradores em sprites/itens/):
    python3 tools/gen_goblin_variations.py
"""

from pathlib import Path
import json
import re
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
GOBLIN_DIR = ROOT / 'assets' / 'sprites' / 'goblins'
OVERLAY_DIR = ROOT / 'assets' / 'sprites' / 'goblin-gear-overlays'
MANIFEST = ROOT / 'assets' / 'manifest.json'

BATCH_SIZE = 5
FRAME_COUNTS = {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15}

# Canto superior esquerdo de cada canvas 128x128 (sprite 32x32 em escala 4x).
PREVIEW_SLOTS = {
    'idle': (0, 0),
    'walk': (128, 0),
    'attack': (256, 0),
    'hurt': (64, 128),
    'death': (192, 128),
}

# O preview dispara as animações de ação em intervalos. Estes índices recuperam
# cada pose do conjunto original, inclusive as repetições presentes nos 62
# quadros usados pelo jogo.
SOURCE_FRAMES = {
    'idle': list(range(5)),
    'walk': list(range(8)),
    'attack': [i % 4 for i in range(17)],
    'hurt': [0, 1, 2, 3, 0, 10, 2, 3, 0, 10, 2, 3, 0, 10, 2, 3, 0],
    'death': list(range(8)) + list(range(20, 27)),
}

BACKGROUND_COLORS = {
    (118, 153, 186),  # #7699BA — fundo
    (104, 132, 158),  # #68849E — sombra
}

GEAR_VERSIONS = [
    'av_cap', 'av_cal', 'av_pei', 'av_cap_cal',
    'av_cap_pei', 'av_pei_cal', 'av_full', 'ferro_pei',
]


def gif_sources():
    """Retorna somente os GIFs numerados de variação, em ordem numérica."""
    found = []
    for path in ROOT.glob('*.gif'):
        match = re.match(r'^(\d{2})_([a-z0-9_]+)\.gif$', path.name)
        if match:
            found.append((int(match.group(1)), match.group(2), path))
    return sorted(found)


def normalized(image):
    """Normaliza pixels transparentes para tornar comparações reproduzíveis."""
    if isinstance(image, (str, Path)):
        image = Image.open(image)
    image = image.convert('RGBA')
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = pixels[x, y]
            pixels[x, y] = (r, g, b, 255) if a else (0, 0, 0, 0)
    return image


def extract_frame(gif, action, source_index):
    """Extrai um sprite 32x32 transparente de um quadro da prévia."""
    gif.seek(source_index)
    frame = gif.convert('RGB')
    x, y = PREVIEW_SLOTS[action]
    sprite = frame.crop((x, y, x + 128, y + 128))
    sprite = sprite.resize((32, 32), Image.Resampling.NEAREST).convert('RGBA')

    pixels = sprite.load()
    for py in range(32):
        for px in range(32):
            r, g, b, _ = pixels[px, py]
            pixels[px, py] = (0, 0, 0, 0) if (r, g, b) in BACKGROUND_COLORS else (r, g, b, 255)

    # A montagem posiciona os sprites um pixel acima do canvas original.
    aligned = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    dx = -1 if action == 'attack' else 0  # a coluna attack também está 1 px à direita
    aligned.alpha_composite(sprite, (dx, 1))
    return aligned


def save_variations(sources):
    entries = []
    produced = 0
    for batch_no, start in enumerate(range(0, len(sources), BATCH_SIZE), 1):
        batch = sources[start:start + BATCH_SIZE]
        labels = ', '.join(f'{number:02d}_{slug}' for number, slug, _ in batch)
        print(f'  lote {batch_no:02d}: {labels}')

        for number, slug, gif_path in batch:
            variant_id = f'{number:02d}_{slug}'
            gif = Image.open(gif_path)
            if gif.size != (413, 292) or getattr(gif, 'n_frames', 1) < 40:
                raise ValueError(f'{gif_path.name}: esperado GIF 413x292 com pelo menos 40 quadros')

            for action, count in FRAME_COUNTS.items():
                indexes = SOURCE_FRAMES[action]
                if len(indexes) != count:
                    raise AssertionError(f'mapeamento inválido de {action}')
                for frame_no, source_index in enumerate(indexes):
                    sprite = extract_frame(gif, action, source_index)
                    sprite_id = f'variant_{variant_id}_{action}_{frame_no}'
                    rel = f'assets/sprites/goblins/{sprite_id}.png'
                    sprite.save(ROOT / rel, optimize=True)
                    entries.append({'id': sprite_id, 'path': rel})
                    produced += 1
            gif.close()
    return entries, produced


def gear_path(version, action, frame_no):
    if version.startswith('av_'):
        return ROOT / 'assets' / 'sprites' / 'avaritia' / f'{version}_{action}_{frame_no}.png'
    return GOBLIN_DIR / f'{version}_{action}_{frame_no}.png'


def save_gear_overlays():
    """Salva somente os pixels alterados por cada skin em relação ao base."""
    OVERLAY_DIR.mkdir(parents=True, exist_ok=True)
    entries = []
    produced = 0

    for version in GEAR_VERSIONS:
        for action, count in FRAME_COUNTS.items():
            for frame_no in range(count):
                base = normalized(GOBLIN_DIR / f'goblin_{action}_{frame_no}.png')
                skin = normalized(gear_path(version, action, frame_no))
                base_pixels = base.load()
                skin_pixels = skin.load()
                overlay = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
                out = overlay.load()

                for y in range(32):
                    for x in range(32):
                        if skin_pixels[x, y] != base_pixels[x, y]:
                            # As skins existentes são recolorações: não alteram a
                            # silhueta alfa. A checagem impede regressões futuras.
                            if skin_pixels[x, y][3] == 0:
                                raise ValueError(f'{version}_{action}_{frame_no} remove pixels do goblin base')
                            out[x, y] = skin_pixels[x, y]

                sprite_id = f'overlay_{version}_{action}_{frame_no}'
                rel = f'assets/sprites/goblin-gear-overlays/{sprite_id}.png'
                overlay.save(ROOT / rel, optimize=True)
                entries.append({'id': sprite_id, 'path': rel})
                produced += 1

    return entries, produced


def update_manifest(entries):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    old = manifest.get('sprites', [])
    old = [entry for entry in old
           if not entry['id'].startswith('variant_')
           and not entry['id'].startswith('overlay_')]
    manifest['sprites'] = old + entries
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    sources = gif_sources()
    if not sources:
        sys.exit('nenhum GIF numerado de variação encontrado na raiz')
    if len(sources) % BATCH_SIZE:
        sys.exit(f'esperava lotes completos de {BATCH_SIZE}; encontrei {len(sources)} GIFs')

    print(f'Gerando {len(sources)} variações em {len(sources) // BATCH_SIZE} lotes de {BATCH_SIZE}...')
    variant_entries, variants = save_variations(sources)
    overlay_entries, overlays = save_gear_overlays()
    update_manifest(variant_entries + overlay_entries)

    print(f'OK — {variants} quadros de variação + {overlays} overlays de equipamento')
    print(f'     {variants + overlays} sprites adicionados ao manifest')


if __name__ == '__main__':
    main()
