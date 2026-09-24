#!/usr/bin/env python3
"""
gen_icons.py — Ícones 16×16 dos equipamentos e habilidades.

Mesma paleta/estilo do gen_sprites.py, mas em grade 16×16 (como os
ícones do conjunto Avaritia: av_pei_icon & cia). Cada ícone é um mapa
de caracteres — um pixel por letra, '.' = transparente.

Também:
  • copia o ícone/skins do peitoral_ferro (sprites/itens/) para
    assets/sprites/, com os ids que o jogo usa (item_peitoral_ferro,
    ferro_pei_{anim}_{n});
  • acrescenta TODOS os sprites novos ao assets/manifest.json
    (idempotente: ids que já existem não são duplicados).

Uso:  python3 tools/gen_icons.py
"""
import json
import os
import shutil

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEM_DIR = os.path.join(ROOT, 'assets/sprites/items')
GOB_DIR = os.path.join(ROOT, 'assets/sprites/goblins')
BLD_DIR = os.path.join(ROOT, 'assets/sprites/buildings')
MANIFEST = os.path.join(ROOT, 'assets/manifest.json')

S = 16

# ---------------- paleta (idêntica ao gen_sprites.py) ----------------
OUT = (34, 26, 18)
WOOD = (169, 113, 61)
WOOD_D = (110, 70, 38)
WOOD_X = (74, 48, 24)
WOOD_L = (200, 150, 95)
GRN = (62, 142, 78)
GRN_L = (79, 165, 98)
GRN_D = (47, 107, 60)
STRAW = (232, 210, 147)
STRAW_D = (198, 172, 110)
GOLD = (232, 178, 58)
GOLD_D = (181, 131, 33)
STONE = (125, 130, 145)
STONE_L = (154, 160, 173)
STONE_D = (106, 111, 125)
RED = (184, 69, 46)
RED_D = (140, 47, 31)
FIRE = (232, 120, 40)
FIRE_L = (250, 200, 90)
WATER = (29, 92, 143)
WATER_L = (58, 130, 180)
WATER_XL = (150, 205, 235)
PURPLE = (167, 139, 250)
PURPLE_D = (110, 85, 190)
DARK = (24, 18, 14)
BONE = (230, 225, 210)
BONE_D = (180, 172, 152)
COPPER = (196, 112, 54)
COPPER_D = (140, 74, 32)
RUBY = (214, 60, 90)
RUBY_D = (150, 30, 60)

PAL = {
    'w': WOOD, 'd': WOOD_D, 'x': WOOD_X, 'l': WOOD_L, 'W': WOOD_L,
    'g': GRN, 'G': GRN_L, 'v': GRN_D,
    's': STONE, 'S': STONE_L, 'z': STONE_D,
    'h': STRAW, 'H': STRAW_D,
    'o': GOLD, 'O': GOLD_D,
    'r': RED, 'R': RED_D,
    'f': FIRE, 'F': FIRE_L,
    'a': WATER, 'A': WATER_L, 'e': WATER_XL,
    'p': PURPLE, 'P': PURPLE_D,
    'k': DARK, 'b': BONE, 'B': BONE_D,
    'c': COPPER, 'C': COPPER_D,
    'u': RUBY, 'U': RUBY_D,
}

# ============================ ÍCONES ============================
# 16 linhas × 16 colunas. '.' = transparente.
ICONS = {

# ---- equipamentos ----
'item_capacete_ferro': [
    "................",
    "................",
    ".....ssssss.....",
    "....sSSSSSSs....",
    "...sSSSSSSSSs...",
    "..sSSSSSSSSSSs..",
    "..sSSkkkkkkSSs..",
    "..sSSSSSSSSSSs..",
    "..szSSSSSSSSzs..",
    "..szzSS..SSzzs..",
    "...zzs....szz...",
    "....z......z....",
    "................",
    "................",
    "................",
    "................",
],

'item_calca_ferro': [
    "................",
    "...ssssssssss...",
    "...sSSSSSSSSs...",
    "...sSSSSSSSSs...",
    "...sSSxSSxSSs...",
    "...sSSxSSxSSs...",
    "...szSxSSxSzs...",
    "...szzxSSxzzs...",
    "....zzxSSxzz....",
    ".....zxSSxz.....",
    ".....zxSSxz.....",
    ".....zxSSxz.....",
    ".....zxxxz......",
    ".....zz.zz......",
    "................",
    "................",
],

'item_botas_couro': [
    "................",
    "................",
    "................",
    "...dd....dd.....",
    "...dd....dd.....",
    "...dd....dd.....",
    "...dd....dd.....",
    "...dd....dd.....",
    "...ddd...ddd....",
    "...dddd..dddd...",
    "..xxxxx..xxxxx..",
    "..xxxxxx.xxxxxx.",
    "..dddddd.dddddd.",
    "................",
    "................",
    "................",
],

'item_anel_cobre': [
    "................",
    "................",
    "................",
    "................",
    "......cccc......",
    ".....c....c.....",
    "....c......c....",
    "....c......c....",
    "....c......c....",
    "....c......c....",
    ".....c....c.....",
    "......cccc......",
    "................",
    "................",
    "................",
    "................",
],

'item_anel_rubi': [
    "................",
    "................",
    "................",
    ".....uUUu.......",
    "....uUUUUu......",
    "....UUUUUU.oo...",
    "....uUUUUo....o.",
    ".....uUUo..o..o.",
    "......uuo.o..o..",
    "........o....o..",
    ".......o....o...",
    "........oooo....",
    "................",
    "................",
    "................",
    "................",
],

'item_espada_ferro': [
    "................",
    "...........ss...",
    "..........sSSs..",
    ".........sSSs...",
    "........sSSs....",
    ".......sSSs.....",
    "......sSSs......",
    ".....sSSs.......",
    "....sSSs........",
    "...osSo.........",
    "..oooo..........",
    ".doo.d..........",
    ".dd.............",
    "................",
    "................",
    "................",
],

'item_clava_goblin': [
    "................",
    "................",
    "................",
    "......xxxx......",
    ".....xwwwwx.....",
    "....xwwwwwwx....",
    "....xwzwwzwx....",
    "....xwwwwwwx....",
    "....xwzwwzwx....",
    ".....xwwwwx.....",
    "......xdx.......",
    "......xdx.......",
    "......xdx.......",
    "......xxx.......",
    "................",
    "................",
],

'item_escudo_madeira': [
    "................",
    "................",
    "................",
    "...wwwwwwwww....",
    "..wWwwwwwwWww...",
    "..wwWwwwwWwww...",
    "..wwwWssWwwww...",
    "..wwwWssWwwww...",
    "..wwWwwwwWwww...",
    "..wWwwwwwwWww...",
    "...wWwwwwWww....",
    "....wwwwwww.....",
    ".....wwwww......",
    "......www.......",
    "................",
    "................",
],

'item_runa_azul': [
    "................",
    "................",
    "....zzzzzz......",
    "...zssssssz.....",
    "...zsAzzzsz.....",
    "...zsAzzzsz.....",
    "...zsAAAzsz.....",
    "...zszAAzsz.....",
    "...zszAAzsz.....",
    "...zszzAzsz.....",
    "...zssssssz.....",
    "....zzzzzz......",
    "................",
    "................",
    "................",
    "................",
],

'item_colar_presas': [
    "................",
    "................",
    "....dd....dd....",
    "...d..d..d..d...",
    "..d....dd....d..",
    "..d...d..d...d..",
    "...dbd.dd.dbd...",
    "....bb.d.bb.....",
    "....bb...bb.....",
    "....Bb...bB.....",
    "....Bb...bB.....",
    "................",
    "................",
    "................",
    "................",
    "................",
],

# ---- habilidades ----
'skill_golpe_brutal': [
    "................",
    "...........rr...",
    "..........rrr...",
    ".....r...rrr....",
    "....rr..rrr.....",
    "....rr.rrr......",
    "....rrrrr.......",
    "....rrrr........",
    "...rrrrr........",
    "...rrrr.rr......",
    "..rrrr..rr......",
    "..rr...rr.......",
    "..r...rr........",
    "......r.........",
    "................",
    "................",
],

'skill_muralha_ferro': [
    "................",
    "................",
    "................",
    "...sssssssss....",
    "..sSSsSSsSSss...",
    "..sSSsSSsSSss...",
    "..sssssssssss...",
    "..sSSsSSsSSss...",
    "..sSSsSSsSSss...",
    "..sssssssssss...",
    "..sSSsSSsSSss...",
    "..sssssssssss...",
    "................",
    "................",
    "................",
    "................",
],

'skill_bola_fogo': [
    "................",
    "................",
    "......f.........",
    ".....fFf...f....",
    "....fFFf..fF....",
    "...fFFFf.fFf....",
    "...fFFFFfFf.....",
    "...fFFFFFFf.....",
    "....fFFFFFf.....",
    "....fFFFFf......",
    ".....fFFf.......",
    "....fFfFf.......",
    "....f...f.......",
    "................",
    "................",
    "................",
],

'skill_raio_gelido': [
    "................",
    "................",
    "......AAA.......",
    ".....AAAAA......",
    "....AeAAAAA.....",
    "....AAAAAAA.....",
    ".....AAAAA......",
    "....AAAAAA......",
    "...AAAAAAA......",
    "...AAAAAA.......",
    "....AAAA........",
    "...AAAAA........",
    "...AAA..........",
    "................",
    "................",
    "................",
],

'skill_toque_curativo': [
    "................",
    "................",
    "....GG....GG....",
    "....GG....GG....",
    "..GGGGGGGGGG....",
    "..GGGGGGGGGG....",
    "..GGGGGGGGGG....",
    "..GGGGGGGGGG....",
    "....GGGGGG......",
    "....GGGGGG......",
    "....GG..GG......",
    "...gGG..GGg.....",
    "..g........g....",
    "................",
    "................",
    "................",
],

'skill_rezo': [
    "................",
    "................",
    "......oooo......",
    "....oo....oo....",
    "...o........o...",
    "...o........o...",
    "...o........o...",
    "....oo....oo....",
    "......oooo......",
    ".......oo.......",
    ".....oooooo.....",
    "....oo.oo.oo....",
    "....o..oo..o....",
    "................",
    "................",
    "................",
],

'skill_tempero_secreto': [
    "................",
    "................",
    ".........o......",
    ".......o.o.o....",
    "....xx.o.o.o....",
    "...xcccx..o.....",
    "...xcccx........",
    "..xcccccx.......",
    "..xcccccx.......",
    "..xcccccx.......",
    "...xcccx........",
    "...xxxxx........",
    "................",
    "................",
    "................",
    "................",
],

'skill_braco_forte': [
    "................",
    "................",
    "................",
    "....sss.........",
    "...sSSsss.......",
    "...sSSSSss......",
    "....sSSSSss.....",
    ".....sSSSSs.....",
    "....sSSSSs......",
    "...sSSSSs.......",
    "...ssSSs........",
    "....sss.........",
    "................",
    "................",
    "................",
    "................",
],

'skill_passo_leve': [
    "................",
    "................",
    "................",
    "..........GG....",
    ".......GGGGG....",
    "....GGGGGG......",
    "..GGGGGG........",
    ".bbGGGG.........",
    ".bbbbb..........",
    ".xxbbbbb........",
    ".xxxxxbbb.......",
    ".xxxxxxbbb......",
    "................",
    "................",
    "................",
    "................",
],

'skill_investida': [
    "................",
    "................",
    "................",
    "................",
    "...........kk...",
    "....r.....kkkk..",
    "....rr...kkkk...",
    "....rrr.kkkk....",
    "....rrrrkkk.....",
    "....rrrrkk......",
    "....rrr.kk......",
    "....rr..........",
    "................",
    "................",
    "................",
    "................",
],
}


def render(rows):
    """Mapa de caracteres → imagem 16×16 com contorno escuro externo."""
    assert len(rows) == S, f'{len(rows)} linhas'
    g = []
    for y, row in enumerate(rows):
        assert len(row) == S, f'linha {y} com {len(row)} colunas'
        g.append([PAL.get(ch) if ch != '.' else None for ch in row])

    # flood fill a partir da borda: quais pixels vazios são "exterior"?
    # (furos internos — o miolo de um anel, p.ex. — ficam transparentes)
    outside = [[False] * S for _ in range(S)]
    stack = []
    for i in range(S):
        for x, y in ((i, 0), (i, S - 1), (0, i), (S - 1, i)):
            if g[y][x] is None and not outside[y][x]:
                outside[y][x] = True
                stack.append((x, y))
    while stack:
        x, y = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < S and 0 <= ny < S and g[ny][nx] is None and not outside[ny][nx]:
                outside[ny][nx] = True
                stack.append((nx, ny))

    # contorno: só pixel de FORA vizinho (4-direções) a pixel pintado.
    # (checa contra o grid ORIGINAL: sem isso o contorno se espalha em cascata)
    src = [r[:] for r in g]
    for y in range(S):
        for x in range(S):
            if src[y][x] is not None or not outside[y][x]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < S and 0 <= ny < S and src[ny][nx] is not None:
                    g[y][x] = OUT
                    break

    im = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    pxs = im.load()
    for y in range(S):
        for x in range(S):
            c = g[y][x]
            if c is not None:
                pxs[x, y] = (c[0], c[1], c[2], 255)
    return im


# ---------------- peitoral de ferro: ícone + skins ----------------
FERRO_SRC = os.path.join(ROOT, 'sprites/itens/peitoral_ferro')
FERRO_ANIMS = [
    ('idle', 5), ('walk', 8), ('attack', 17), ('hurt', 17), ('death', 15),
]


def main():
    novos = []

    # 1) ícones desenhados aqui
    for icon_id, rows in ICONS.items():
        path = os.path.join(ITEM_DIR, icon_id + '.png')
        os.makedirs(ITEM_DIR, exist_ok=True)
        render(rows).save(path)
        novos.append({'id': icon_id, 'path': 'assets/sprites/items/' + icon_id + '.png'})

    # 2) peitoral_ferro: ícone do item
    icon_dst = os.path.join(ITEM_DIR, 'item_peitoral_ferro.png')
    shutil.copyfile(os.path.join(FERRO_SRC, 'icon.png'), icon_dst)
    novos.append({'id': 'item_peitoral_ferro', 'path': 'assets/sprites/items/item_peitoral_ferro.png'})

    # 3) peitoral_ferro: skins do goblin equipado (ferro_pei_{anim}_{n})
    for anim, n in FERRO_ANIMS:
        for i in range(n):
            src = os.path.join(FERRO_SRC, f'goblin_{anim}_{i}.png')
            dst = os.path.join(GOB_DIR, f'ferro_pei_{anim}_{i}.png')
            shutil.copyfile(src, dst)
            novos.append({
                'id': f'ferro_pei_{anim}_{i}',
                'path': f'assets/sprites/goblins/ferro_pei_{anim}_{i}.png',
            })

    # 4) prédio do armazém (gerado pelo gen_sprites.py)
    novos.append({
        'id': 'building_armazem_1',
        'path': 'assets/sprites/buildings/building_armazem_1.png',
    })

    # 5) manifest — acrescenta só o que falta
    with open(MANIFEST, encoding='utf-8') as f:
        manifest = json.load(f)
    have = {s['id'] for s in manifest['sprites']}
    added = 0
    for e in novos:
        if e['id'] in have:
            continue
        manifest['sprites'].append(e)
        have.add(e['id'])
        added += 1

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write('\n')

    print(f'OK — {len(ICONS)} ícones desenhados, '
          f'{len(FERRO_ANIMS) and sum(n for _, n in FERRO_ANIMS)} skins ferro_pei, '
          f'+{added} entradas no manifest (total {len(manifest["sprites"])}).')


if __name__ == '__main__':
    main()
