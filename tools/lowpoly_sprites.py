#!/usr/bin/env python3
"""
lowpoly_sprites.py — Converte sprites pixel-art de CENÁRIO/ESTRUTURA para o
estilo low-poly facetado ja usado pelos animais (lobo, Gemeos, javali,
veado, lebre): superficies feitas de triangulos planos, cada face com uma
cor unica sombreada, sem textura nem dither.

Como funciona (reprodutivel, sem IA):
  1. Os PNGs pixel-art originais sao preservados em
     art-source/pixelart-cenarios-estruturas/ (espelho de assets/sprites/).
     A ferramenta SEMPRE le dali — nunca de um assets/ ja facetado —
     entao rodar de novo com outros parametros nao acumula efeito.
  2. A imagem e ampliada (2x–3x), suavizada e ganha leve saturacao para
     limpar o dither da pixel art; a cor "vaza" para fora da silhueta
     (bleed) para nenhuma face de borda ficar preta.
  3. Uma grade de vertices com jitter (seed fixa por sprite) vira
     triangulos; cada face recebe a cor media amostrada da fonte e um
     sombreamento flat proprio (luz vindo do alto-esquerda, como na
     arte-fonte dos Gemeos), desenhada com supersampling p/ anti-alias.
  4. O alfa final e o alfa original ampliado: silhueta, furos e linha
     dos pes/base ficam EXATAMENTE onde estavam — nenhum codigo de
     ancora/hitbox muda. So a resolucao interna cresce; os drawImage
     ja existentes tem tamanho de destino fixo.

Uso:
  /tmp/pv/bin/python tools/lowpoly_sprites.py --snapshot   # 1a vez: salva originais
  /tmp/pv/bin/python tools/lowpoly_sprites.py              # gera todos os alvos
  /tmp/pv/bin/python tools/lowpoly_sprites.py building_house_1 node_tree_0
  /tmp/pv/bin/python tools/lowpoly_sprites.py --check      # lista alvos e estado

Depois de gerar: rode tools/build_singlefile.py (build jogavel) e tools/test.sh.
Ver docs/lowpoly.md para o inventario completo da transformacao.
"""
import argparse
import hashlib
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets', 'sprites')
ORIGINALS = os.path.join(ROOT, 'art-source', 'pixelart-cenarios-estruturas')

# ---------------------------------------------------------------------------
# Alvos desta etapa (cenarios e estruturas). Animais NAO entram: ja nascem
# low-poly na arte-fonte. Goblins/itens/UI ficam para etapas futuras
# (ver docs/lowpoly.md).
#
#   scale : resolucao interna de saida / resolucao atual
#   cell  : tamanho alvo da aresta das facetas, em px DA SAIDA
#   shade : amplitude do sombreamento flat por face (0.07 = ±7%)
# ---------------------------------------------------------------------------
TARGETS = {}


def add(patterns, scale, cell, shade=0.07, sat=1.08, detail=1.0):
    for name in patterns:
        TARGETS[name] = dict(scale=scale, cell=cell, shade=shade, sat=sat,
                             detail=detail)


add([  # as 14 estruturas da vila + lona de obra (64x64 -> 192x192)
    'buildings/building_house_1.png',
    'buildings/building_construction_1.png',
    'buildings/building_questboard_1.png',
    'buildings/building_serraria_1.png',
    'buildings/building_fazenda_1.png',
    'buildings/building_armazem_1.png',
    'buildings/building_cozinha_1.png',
    'buildings/building_mercado_1.png',
    'buildings/building_estabulo_1.png',
    'buildings/building_ferraria_1.png',
    'buildings/building_altar_1.png',
    'buildings/building_bazar_1.png',
    'buildings/building_porto_1.png',
    'buildings/building_quartel_1.png',
    'buildings/building_construction_site.png',
], scale=3, cell=13, shade=0.055)

add([  # divindades (estruturas especiais) + pedra arremessada
    'deities/building_grande_arvore_1.png',
    'deities/building_golem_pedra_1.png',
], scale=3, cell=15, shade=0.06)
add(['deities/fx_pedra_divina.png'], scale=3, cell=15)

add([  # nos coletaveis
    'nodes/node_tree_0.png',
    'nodes/node_tree_stump.png',
    'nodes/node_rock_0.png',
    'nodes/node_rock_rubble.png',
], scale=3, cell=16, shade=0.06)

add([  # balao nos 3 estados
    'raid/balloon_wrecked.png',
    'raid/balloon_ready.png',
    'raid/balloon_flying.png',
], scale=3, cell=17, shade=0.06)

add([  # tocas, covil e baus
    'raid/prop_den.png',
    'raid/chest_closed.png',
    'raid/chest_open.png',
], scale=3, cell=14, shade=0.06)
add([
    'raid/prop_den_lair.png',
    'raid/reward_chest_wood.png',
    'raid/reward_chest_bone.png',
    'raid/prop_hive.png',
], scale=2, cell=20, shade=0.06)

add([  # fundos de batalha/passagem e mar do mapa (640x360 -> 1280x720)
    'raid/bg_den.png',
    'raid/bg_den_twins.png',
    'raid/bg_den_passage.png',
    'ui/islands_sea.png',
], scale=2, cell=34, shade=0.06, detail=0.12)

add([  # retratos das ilhas no mapa
    'ui/island_home.png',
    'ui/island_fangs.png',
    'ui/island_smoke.png',
    'ui/island_iron.png',
], scale=2, cell=20, shade=0.06, detail=0.45)


# ---------------------------------------------------------------------------
def seed_for(name):
    return int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16)


def bleed_colors(rgba):
    """RGB opaco "vazado": o borrao forte da propria imagem por baixo da
    imagem nitida, para amostras perto da silhueta nao capturarem preto
    dos pixels transparentes."""
    blur = rgba.filter(ImageFilter.GaussianBlur(max(4, rgba.width // 24)))
    base = Image.new('RGBA', rgba.size)
    base.paste(blur, (0, 0))
    base.alpha_composite(rgba)
    # fundo opaco com a cor borrada onde ainda for transparente
    bg = blur.copy()
    bg.putalpha(255)
    bg.alpha_composite(base)
    return bg.convert('RGB')


def sample(px, w, h, x, y):
    x = min(w - 1, max(0, int(round(x))))
    y = min(h - 1, max(0, int(round(y))))
    return px[x, y]


def facetize(src, scale, cell, shade, sat, seed, detail=1.0):
    w, h = src.width * scale, src.height * scale
    big = src.resize((w, h), Image.LANCZOS)
    big = big.filter(ImageFilter.GaussianBlur(scale * 0.38))
    colors = bleed_colors(big)
    colors = ImageEnhance.Color(colors).enhance(sat)
    colors = ImageEnhance.Contrast(colors).enhance(1.03)
    alpha = big.getchannel('A')
    cpx = colors.load()

    rng = random.Random(seed)
    ss = 2  # supersampling p/ bordas de faceta anti-aliased
    out = Image.new('RGB', (w * ss, h * ss), (0, 0, 0))
    draw = ImageDraw.Draw(out)

    nx = max(2, round(w / cell))
    ny = max(2, round(h / cell))
    cw, ch = w / nx, h / ny
    pts = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x, y = i * cw, j * ch
            if 0 < i < nx:
                x += rng.uniform(-0.38, 0.38) * cw
            if 0 < j < ny:
                y += rng.uniform(-0.38, 0.38) * ch
            row.append((x, y))
        pts.append(row)

    def draw_face(tri):
        cx = sum(p[0] for p in tri) / 3
        cy = sum(p[1] for p in tri) / 3
        acc = [0.0, 0.0, 0.0]
        samples = [(cx, cy)] + [(cx + (p[0] - cx) * 0.55,
                                 cy + (p[1] - cy) * 0.55) for p in tri]
        for sx_, sy_ in samples:
            r, g, b = sample(cpx, w, h, sx_, sy_)
            acc[0] += r; acc[1] += g; acc[2] += b
        # sombreamento flat: chute por face + luz suave do alto
        f = 1.0 + rng.uniform(-shade, shade) + (0.5 - cy / max(1, h)) * 0.05
        # quantizar funde faces vizinhas do mesmo material em paineis maiores
        col = tuple(min(255, max(0, round(a / len(samples) * f / 8) * 8)) for a in acc)
        # expande 1px a partir do centroide p/ nao abrir frestas entre faces
        poly = [((cx + (p[0] - cx) * 1.03) * ss, (cy + (p[1] - cy) * 1.03) * ss)
                for p in tri]
        draw.polygon(poly, fill=col)

    for j in range(ny):
        for i in range(nx):
            a, b = pts[j][i], pts[j][i + 1]
            c, d = pts[j + 1][i], pts[j + 1][i + 1]
            if (i + j) % 2 == 0:
                draw_face((a, b, d)); draw_face((a, d, c))
            else:
                draw_face((a, b, c)); draw_face((b, d, c))

    out = out.resize((w, h), Image.LANCZOS).convert('RGBA')

    # Passe de detalhe: portas, cordas, serras e lampadas sao linhas finas
    # de alto contraste que a media das facetas apaga. Onde a luminancia
    # foge da media LOCAL (mais escura ou mais clara que a vizinhanca),
    # reimprimimos a cor original (pouco borrada) por cima das facetas —
    # a leitura do predio volta sem trazer a textura inteira da pixel art.
    lum = colors.convert('L')
    local = lum.filter(ImageFilter.GaussianBlur(cell * 0.7))
    dark = ImageChops.subtract(local, lum).point(
        lambda v: 0 if v < 16 else min(235, int((v - 16) * 4.4)))
    bright = ImageChops.subtract(lum, local).point(
        lambda v: 0 if v < 30 else min(205, int((v - 30) * 3.4)))
    ink_alpha = ImageChops.lighter(dark, bright)
    if detail < 1.0:  # fundos: quase sem reimpressao (so facetas)
        ink_alpha = ink_alpha.point(lambda v: int(v * detail))
    ink_alpha = ImageChops.multiply(
        ink_alpha, alpha.point(lambda a: min(255, a * 2)))
    sharp = bleed_colors(src.resize((w, h), Image.LANCZOS)
                         .filter(ImageFilter.GaussianBlur(scale * 0.22)))
    sharp_rgba = sharp.convert('RGBA')
    sharp_rgba.putalpha(ink_alpha)
    out.alpha_composite(sharp_rgba)

    # silhueta identica a original (so mais resolucao): limiar firme p/
    # o LANCZOS nao deixar halo semi-transparente em volta
    alpha = alpha.point(lambda a: 0 if a < 24 else min(255, int((a - 24) * 1.35)))
    out.putalpha(alpha)
    return out


def convert(rel):
    cfg = TARGETS[rel]
    src_path = os.path.join(ORIGINALS, rel)
    dst_path = os.path.join(ASSETS, rel)
    if not os.path.exists(src_path):
        print(f'  ! original ausente, pulando: {rel} (rode --snapshot antes)')
        return False
    src = Image.open(src_path).convert('RGBA')
    img = facetize(src, seed=seed_for(rel), **cfg)
    # Faceta e cor chapada: paleta de 256 cores e visualmente identica e
    # 4-5x menor — importante porque o build embute tudo em base64.
    img = img.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                       dither=Image.Dither.NONE)
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    img.save(dst_path, optimize=True)
    kb = os.path.getsize(dst_path) // 1024
    print(f'  {rel}: {src.width}x{src.height} -> {img.width}x{img.height} ({kb} KB)')
    return True


def snapshot():
    n = 0
    for rel in TARGETS:
        src = os.path.join(ASSETS, rel)
        dst = os.path.join(ORIGINALS, rel)
        if os.path.exists(dst):
            print(f'  = ja preservado: {rel}')
            continue
        if not os.path.exists(src):
            print(f'  ! nao existe em assets/: {rel}')
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        Image.open(src).save(dst)
        n += 1
        print(f'  + preservado: {rel}')
    print(f'{n} originais preservados em art-source/pixelart-cenarios-estruturas/')


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('names', nargs='*',
                    help='nomes (sufixos) a converter; vazio = todos')
    ap.add_argument('--snapshot', action='store_true',
                    help='copia os PNGs atuais para art-source/ (1a vez)')
    ap.add_argument('--check', action='store_true',
                    help='lista alvos e se original/convertido existem')
    args = ap.parse_args()

    if args.snapshot:
        snapshot()
        if args.check or args.names:
            pass
        else:
            return
    if args.check:
        for rel in sorted(TARGETS):
            o = os.path.exists(os.path.join(ORIGINALS, rel))
            a = os.path.join(ASSETS, rel)
            size = '?' if not os.path.exists(a) else \
                f'{Image.open(a).width}x{Image.open(a).height}'
            print(f"{'ok ' if o else 'SEM'} {rel:45s} assets={size}")
        return

    wanted = sorted(TARGETS)
    if args.names:
        wanted = [r for r in wanted
                  if any(r.endswith(n) or n in r for n in args.names)]
        if not wanted:
            print('nenhum alvo casa com:', ', '.join(args.names))
            sys.exit(1)
    done = sum(convert(r) for r in wanted)
    print(f'{done}/{len(wanted)} sprites convertidos p/ low-poly.')


if __name__ == '__main__':
    main()
