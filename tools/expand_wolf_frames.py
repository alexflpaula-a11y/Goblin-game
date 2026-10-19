#!/usr/bin/env python3
"""
expand_wolf_frames.py — Mais quadros (e pés no chão) para os lobos.

Lê a base preservada em `art-source/wolves-base/` (um quadro por pose, com
os segurados que existiam antes) e produz a versão final em
`assets/sprites/raid/`:

  1. Remove quadros repetidos consecutivos (eram "segurados" que travavam
     a animação).
  2. Insere um quadro intermediário entre cada par de poses distintas
     (união das silhuetas, cor média onde ambas são opacas). Em ciclos
     (idle/walk) o último quadro também ganha intermediário com o primeiro.
  3. Ancora os pés de cada quadro na mesma linha do chão (a linha do idle),
     para que o ataque da Mandíbula não "decole" da sombra.
  4. Registra os ids novos em `assets/manifest.json` e gera
     `js/creatures.js` com a contagem de quadros de cada animação.

Uso:  python3 tools/expand_wolf_frames.py      (requer Pillow)
"""
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'art-source' / 'wolves-base'
OUT = ROOT / 'assets' / 'sprites' / 'raid'
MANIFEST = ROOT / 'assets' / 'manifest.json'
CREATURES_JS = ROOT / 'js' / 'creatures.js'

# prefixo -> animações e quantidade de quadros-base
KINDS = {
    'wolf': {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15},
    'twin_jaw': {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15},
    'twin_paw': {'idle': 5, 'walk': 8, 'attack': 17, 'hurt': 17, 'death': 15},
}
CYCLIC = {'idle', 'walk'}
# Ataque da Mandíbula: escala do corpo para a do repouso (medido: 19–26 px vs 34 px).
JAW_ATTACK_SCALE = 1.3
# Duração total de cada animação (segundos) — preservada do jogo anterior
# (quadros-base × passo antigo). Com mais quadros, cada um dura menos.
# Duração total de cada animação com os quadros reais (sem intermediários).
DURATION = {'idle': 0.9, 'walk': 0.8, 'attack': 0.8, 'hurt': 0.5, 'death': 0.7}
# A caminhada (16 quadros) é gerada por tools/make_walk_legs.py, não aqui.
WALK_FRAMES = 16


def load(path):
    return Image.open(path).convert('RGBA')


def drop_sparkles(im):
    """Remove pontos claros soltos (brilho/poeira gravados na arte-fonte).

    Um pixel claro e pouco saturado com no máximo 2 vizinhos opacos é efeito,
    não parte do animal. O repouso não tem nenhum desses pontos, então não muda.
    """
    w, h = im.size
    src = im.load()
    out = im.copy()
    dst = out.load()
    def opaque(x, y):
        return 0 <= x < w and 0 <= y < h and src[x, y][3] >= 128
    for y in range(h):
        for x in range(w):
            r, g, b, a = src[x, y]
            if a == 0:
                continue
            light = (r + g + b) / 3 >= 150 and max(r, g, b) - min(r, g, b) <= 45
            if not light:
                continue
            nb = sum(opaque(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
            if nb <= 2:
                dst[x, y] = (0, 0, 0, 0)
    return out


def dedupe(frames):
    out = []
    for f in frames:
        if out and out[-1].tobytes() == f.tobytes():
            continue
        out.append(f)
    return out


def union_mid(a, b):
    w, h = a.size
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    pa, pb, po = a.load(), b.load(), out.load()
    for y in range(h):
        for x in range(w):
            ra, ga, ba, aa = pa[x, y]
            rb, gb, bb, ab = pb[x, y]
            oa, ob = aa >= 128, ab >= 128
            if oa and ob:
                po[x, y] = ((ra + rb) // 2, (ga + gb) // 2, (ba + bb) // 2, 255)
            elif oa:
                po[x, y] = (ra, ga, ba, 255)
            elif ob:
                po[x, y] = (rb, gb, bb, 255)
    return out


def expand(frames, cyclic):
    """Sem quadros intermediários: a união de dois quadros fazia fantasmas."""
    return list(frames)


def _old_expand_unused(frames, cyclic):
    seq = []
    pairs = list(zip(frames, frames[1:]))
    if cyclic and len(frames) > 1:
        pairs.append((frames[-1], frames[0]))
    for i, f in enumerate(frames):
        seq.append(f)
        if i < len(frames) - 1:
            seq.append(union_mid(f, frames[i + 1]))
        elif cyclic and len(frames) > 1:
            seq.append(union_mid(f, frames[0]))
    return seq


def fix_jaw_attack(im):
    """Mandíbula (ataque): tira o brilho metálico picotado, aumenta o corpo para a
    escala do repouso e descarta fragmentos soltos da escala.

    Só para twin_jaw/attack. O brilho cinza-claro (≥185, pouco saturado) não existe
    no repouso, então o limite não altera a pose parada.
    """
    im = im.convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a and (r + g + b) / 3 >= 185 and max(r, g, b) - min(r, g, b) <= 35:
                px[x, y] = (0, 0, 0, 0)
    bb = im.split()[3].getbbox()
    if bb is None:
        return im
    crop = im.crop(bb)
    f = JAW_ATTACK_SCALE
    nw, nh = round(crop.width * f), round(crop.height * f)
    s = crop.resize((nw, nh), Image.LANCZOS)
    s.putalpha(s.split()[3].point(lambda v: 255 if v >= 110 else 0))
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    out.paste(s, (round((bb[0] + bb[2]) / 2 - nw / 2), bb[3] - nh), s)
    return drop_edge_speckle(drop_small_parts(out))


def drop_edge_speckle(im, passes=2):
    """Remove pontos cinza-claros e neutros na borda do sprite (o 'xadrez' do ataque).

    Só age em pixels opacos, quase sem cor (saturação ≤14), claros (lum ≥115) e
    encostados em área transparente. O metal do interior não é tocado.
    """
    w, h = im.size
    for _ in range(passes):
        src = im.copy()
        sp = src.load()
        dp = im.load()
        for y in range(h):
            for x in range(w):
                r, g, b, a = sp[x, y]
                if a < 128 or max(r, g, b) - min(r, g, b) > 14 or (r + g + b) / 3 < 115:
                    continue
                edge = any(
                    not (0 <= x + dx < w and 0 <= y + dy < h) or sp[x + dx, y + dy][3] < 128
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                )
                if edge:
                    dp[x, y] = (0, 0, 0, 0)
    return im


def drop_small_parts(im, min_area=12):
    """Remove componentes conectados pequenos (fragmentos de brilho soltos)."""
    from collections import deque
    w, h = im.size
    a = im.split()[3].load()
    seen = [[False] * w for _ in range(h)]
    out = im.copy()
    po = out.load()
    for y in range(h):
        for x in range(w):
            if a[x, y] < 128 or seen[y][x]:
                continue
            q = deque([(x, y)])
            seen[y][x] = True
            cells = []
            while q:
                cx, cy = q.popleft()
                cells.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and a[nx, ny] >= 128:
                            seen[ny][nx] = True
                            q.append((nx, ny))
            if len(cells) < min_area:
                for cx, cy in cells:
                    po[cx, cy] = (0, 0, 0, 0)
    return out


# Ataque da Mandíbula: avanço procedural sobre a arte blindada (war-twins/jaw.png).
# Cada coluna desloca em x; a cabeça avança mais que o corpo (peso 0 atrás, 1 na ponta).
JAW_PROFILE = [0, -1, -2, 1, 3, 4, 3, 1, 0]  # recuo, bote, retorno (px na ponta)


def jaw_lunge_frames():
    base = Image.open(ROOT / 'art-source' / 'war-twins' / 'jaw.png').convert('RGBA')
    w, h = base.size
    out_frames = []
    for d in JAW_PROFILE:
        out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        # Mapeamento inverso: cada coluna de saída X copia a coluna de origem X - deslocamento(X).
        # Assim não sobram vãos transparentes entre colunas.
        for X in range(w):
            weight = min(1.0, max(0.0, (X - 22) / 16))
            x = X - round(d * weight)
            if 0 <= x < w:
                out.paste(base.crop((x, 0, x + 1, h)), (X, 0))
        out_frames.append(out)
    return out_frames


def feet_row(im):
    box = im.split()[3].getbbox()
    return box[3] if box else im.height


def ground(frames, baseline):
    out = []
    for f in frames:
        dy = baseline - feet_row(f)
        if dy <= 0:
            out.append(f)
            continue
        g = Image.new('RGBA', f.size, (0, 0, 0, 0))
        g.alpha_composite(f, (0, dy))
        out.append(g)
    return out


def main():
    counts = {}
    new_ids = []
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for prefix, anims in KINDS.items():
        base_idle = load(BASE / f'{prefix}_idle_0.png')
        baseline = base_idle.height
        # Remove todos os quadros antigos deste prefixo antes de regravar.
        for old in OUT.glob(f'{prefix}_*_*.png'):
            if '_walk_' not in old.name:  # caminhada é gerada por make_walk_legs.py
                old.unlink()
        counts[prefix] = {}
        for anim, n in anims.items():
            if anim == 'walk':
                counts[prefix]['walk'] = WALK_FRAMES
                new_ids += [f'{prefix}_walk_{i}' for i in range(WALK_FRAMES)]
                continue
            raw = [drop_sparkles(load(BASE / f'{prefix}_{anim}_{i}.png')) for i in range(n)]
            if prefix == 'twin_jaw' and anim == 'attack':
                raw = jaw_lunge_frames()
            uniq = dedupe(raw)
            seq = expand(uniq, anim in CYCLIC)
            seq = ground(seq, baseline)
            counts[prefix][anim] = len(seq)
            for i, im in enumerate(seq):
                name = f'{prefix}_{anim}_{i}'
                im.save(OUT / f'{name}.png', optimize=True)
                new_ids.append(name)
    # Manifesto: remove entradas antigas do prefixo e registra as novas.
    prefixes = tuple(f'{p}_' for p in KINDS)
    kept = [e for e in manifest['sprites'] if not e['id'].startswith(prefixes)]
    entries = [{'id': n, 'path': f'assets/sprites/raid/{n}.png'} for n in new_ids]
    manifest['sprites'] = kept + entries
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n',
                        encoding='utf-8')
    lines = [
        '// ============================================================',
        '// creatures.js — Contagem de quadros dos lobos e da Mandíbula/Patas.',
        '// GERADO por tools/expand_wolf_frames.py — não editar à mão.',
        '// ============================================================',
        'const CREATURE_FRAMES = {',
    ]
    for prefix, anims in counts.items():
        body = ', '.join(f'{a}: {n}' for a, n in anims.items())
        lines.append(f'  {prefix}: {{ {body} }},')
    dur = ', '.join(f'{a}: {v}' for a, v in DURATION.items())
    lines += [
        '};',
        '',
        '/** Duração total (s) de cada animação de criatura, mantida entre versões. */',
        f'const CREATURE_DURATION = {{ {dur} }};',
        '',
        '/** Quadros de uma animação de criatura (lobo/chefes); 1 se desconhecida. */',
        'function creatureFrames(prefix, anim) {',
        '  const row = CREATURE_FRAMES[prefix];',
        '  return (row && row[anim]) || 1;',
        '}',
        '',
        '/** Segundos por quadro: mesma duração total, mais quadros = mais fluido. */',
        'function creatureStep(prefix, anim) {',
        '  return (CREATURE_DURATION[anim] || 0.07) / creatureFrames(prefix, anim);',
        '}',
        '',
        'module.exports = { CREATURE_FRAMES, CREATURE_DURATION, creatureFrames, creatureStep };',
        '',
    ]
    CREATURES_JS.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(counts, indent=2))
    print(f'OK — {len(new_ids)} quadros gravados; manifesto e js/creatures.js atualizados')


if __name__ == '__main__':
    main()
