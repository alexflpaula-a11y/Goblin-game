#!/usr/bin/env python3
"""door_variant.py — variante com a porta aberta, gerada por IA.

Fluxo:
1. o sprite aprovado é ampliado 8x (NEAREST) e enviado à IA, que devolve a
   mesma cena com a porta aberta;
2. o retorno é recortado no conteúdo, o magenta é removido e a imagem é
   reduzida UMA única vez por MEDIANA de bloco — cada pixel da saída vira
   uma cor chapada, sem interpolação (é isso que evita o borrão);
3. a peça é alinhada ao sprite original por busca de deslocamento;
4. só o retângulo da porta é composto, e apenas onde o sprite original é
   opaco. Fora dele, o sprite aprovado fica pixel a pixel intacto.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAND = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'candidates')
RAW = os.path.join(ROOT, 'art-source', 'lowpoly-village', 'raw')
MAGENTA = np.array([255, 0, 255], dtype=np.int16)


def strip_magenta(img, tol=260):
    """Remove o fundo magenta e o roxo que a IA espalhou nas bordas."""
    a = np.asarray(img.convert('RGBA')).copy()
    rgb = a[..., :3].astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    d = np.abs(rgb - MAGENTA).sum(2)
    # fundo chapado
    a[d < tol, 3] = 0
    # roxo/magenta em qualquer tom (r e b altos, g baixo)
    purple = (r > 120) & (b > 120) & (g < 130) & ((r - g) > 45) & ((b - g) > 45)
    a[purple, 3] = 0
    # vizinhos diretos do fundo que ainda puxam roxo
    alpha = a[..., 3] > 0
    near = np.zeros_like(alpha)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            near |= np.roll(np.roll(~alpha, dy, 0), dx, 1)
    a[near & purple, 3] = 0
    # última linha/coluna com roxo: como a IA às vezes pinta uma faixa rosa na
    # base, apagamos qualquer pixel opaco que tenha roxo forte
    r2, b2, g2 = a[..., 0].astype(int), a[..., 2].astype(int), a[..., 1].astype(int)
    strong = (r2 > 110) & (b2 > 110) & ((r2 - g2) > 25) & ((b2 - g2) > 25)
    a[strong, 3] = 0
    return Image.fromarray(a, 'RGBA')


def repair_purple(piece):
    """Troca qualquer pixel roxo/rosado pela cor de um vizinho sadio."""
    a = np.asarray(piece.convert('RGBA')).copy()
    for _ in range(3):
        r, g, b = a[..., 0].astype(int), a[..., 1].astype(int), a[..., 2].astype(int)
        bad = (a[..., 3] > 0) & (r > 95) & (b > 95) & ((r - g) > 22) & ((b - g) > 22)
        if not bad.any():
            break
        ys, xs = np.nonzero(bad)
        h, w = a.shape[:2]
        for y, x in zip(ys, xs):
            for rad in (1, 2, 3):
                y0, y1 = max(0, y - rad), min(h, y + rad + 1)
                x0, x1 = max(0, x - rad), min(w, x + rad + 1)
                blk = a[y0:y1, x0:x1]
                ok = (blk[..., 3] > 0)
                rr, gg, bb = blk[..., 0].astype(int), blk[..., 1].astype(int), blk[..., 2].astype(int)
                good = ok & ~((rr > 95) & (bb > 95) & ((rr - gg) > 22) & ((bb - gg) > 22))
                if good.any():
                    a[y, x, :3] = np.median(blk[..., :3][good], axis=0).astype(np.uint8)
                    break
    return Image.fromarray(a, 'RGBA')


def content_bbox(img):
    a = np.asarray(img.convert('RGBA'))
    ys, xs = np.nonzero(a[..., 3] > 40)
    if len(xs) == 0:
        return (0, 0) + img.size
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def block_median(img, out_size):
    """Reduz por mediana de bloco: saída chapada, sem interpolação."""
    a = np.asarray(img.convert('RGBA'), dtype=np.float32)
    h, w = a.shape[:2]
    ow, oh = out_size
    out = np.zeros((oh, ow, 4), dtype=np.uint8)
    for oy in range(oh):
        y0, y1 = int(oy * h / oh), max(int((oy + 1) * h / oh), int(oy * h / oh) + 1)
        for ox in range(ow):
            x0, x1 = int(ox * w / ow), max(int((ox + 1) * w / ow), int(ox * w / ow) + 1)
            blk = a[y0:y1, x0:x1].reshape(-1, 4)
            op = blk[blk[:, 3] > 90]
            if len(op) < max(1, len(blk) // 3):
                continue
            out[oy, ox, :3] = np.median(op[:, :3], axis=0)
            out[oy, ox, 3] = 255
    return Image.fromarray(out, 'RGBA')


def align(piece, base, mask):
    """Acha o deslocamento que mais aproxima a peça do original (fora da porta)."""
    pb = np.full((64, 64, 4), 255, dtype=np.uint8)
    pb[:piece.height, :piece.width] = np.asarray(piece)
    pa = np.asarray(base.convert('RGBA')).astype(np.float32)
    best = (-1e18, 0, 0)
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            sh = piece.transform(piece.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy), resample=Image.NEAREST)
            full = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            full.alpha_composite(sh, (0, 0))
            fa = np.asarray(full).astype(np.float32)
            op = (fa[..., 3] > 90) & (pa[..., 3] > 90) & (~mask)
            if op.sum() < 200:
                continue
            score = -np.abs(fa[..., :3] - pa[..., :3]).sum(2)[op].mean()
            if score > best[0]:
                best = (score, dx, dy)
    return best[1], best[2]


def find_dark_opening(src, rect_frac):
    """Acha o vão escuro da porta aberta dentro do render da IA.

    A IA às vezes encolhe o prédio dentro do quadro, então mapear por
    proporção erra 1-2 px. Aqui procuramos o retângulo escuro mais próximo
    do esperado; se não achar nada convincente, devolvemos None.
    """
    a = np.asarray(src.convert('RGBA')).astype(np.float32)
    h, w = a.shape[:2]
    g = a[..., :3].mean(2)
    op = a[..., 3] > 60
    dark = op & (g < 55)
    ys, xs = np.nonzero(dark)
    if len(xs) < 200:
        return None
    ex, ey = rect_frac
    # agrupa pela coluna/linha mais densa perto do esperado
    tol_x = w * 0.16
    tol_y = h * 0.22
    sel = (np.abs(xs - ex * w) < tol_x) & (ys > (ey - 0.10) * h)
    if sel.sum() < 150:
        return None
    xs2, ys2 = xs[sel], ys[sel]
    return (int(xs2.min()), int(ys2.min()), int(xs2.max()) + 1, int(ys2.max()) + 1)


def build(name, rect):
    """Recorta a PORTA em alta resolução e reduz uma única vez."""
    base = Image.open(os.path.join(CAND, name + '.png')).convert('RGBA')
    w, h = base.size
    src = strip_magenta(Image.open(os.path.join(RAW, 'p8_' + name + '.png')).convert('RGBA'))

    # silhueta do original (o sprite já é o objeto: bbox do alpha)
    bb = content_bbox(base)
    sb = content_bbox(src)

    # mapeia o retângulo da porta (coords do sprite) para coords do render
    sx = (sb[2] - sb[0]) / max(1, bb[2] - bb[0])
    sy = (sb[3] - sb[1]) / max(1, bb[3] - bb[1])
    x0, y0, x1, y1 = rect
    rx0 = int(round(sb[0] + (x0 - bb[0]) * sx))
    rx1 = int(round(sb[0] + (x1 - bb[0]) * sx))
    ry0 = int(round(sb[1] + (y0 - bb[1]) * sy))
    ry1 = int(round(sb[1] + (y1 - bb[1]) * sy))
    crop = src.crop((rx0, ry0, rx1, ry1))

    # UMA redução, por mediana de bloco: cor chapada, sem borrão
    piece = repair_purple(block_median(crop, (x1 - x0, y1 - y0)))

    # AUTO-ALINHAMENTO: acha o vão escuro dentro da peça e desloca a peça para
    # que ele caia exatamente no retângulo da porta do sprite original.
    pa0 = np.asarray(piece.convert('RGBA')).astype(np.float32)
    lum = pa0[..., :3].mean(2)
    dark = (pa0[..., 3] > 60) & (lum < 62)
    if dark.sum() >= 12:
        ys, xs = np.nonzero(dark)
        cx, cy = float(xs.mean()), float(ys.mean())
        tx, ty = (x0 + x1 - 1) / 2 - x0, (y0 + y1 - 1) / 2 - y0
        sx, sy = int(round(tx - cx)), int(round(ty - cy))
        canvas = Image.new('RGBA', (x1 - x0, y1 - y0), (0, 0, 0, 0))
        canvas.alpha_composite(piece, (sx, sy))
        piece = canvas

    # ajuste fino: testa deslocamentos de 1 px e escolhe o que melhor
    # continua as linhas do sprite original
    def score(px, py):
        full = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        full.alpha_composite(piece, (x0 + px, y0 + py))
        fa = np.asarray(full).astype(np.float32)
        ba = np.asarray(base).astype(np.float32)
        op = (fa[..., 3] > 90) & (ba[..., 3] > 90)
        op[y0:y1, x0:x1] = False
        return float(np.abs(fa[..., :3] - ba[..., :3]).sum(2)[op].mean()) if op.sum() > 100 else 1e9

    dxf, dyf = 0, 0

    # só a porta, e só onde o original é opaco
    # a peça nunca deixa buraco nem roxo: o que não foi pintado volta ao original
    pa0 = np.asarray(piece.convert('RGBA')).copy()
    base_crop = np.asarray(base.crop(rect).convert('RGBA'))
    rr, gg, bb = pa0[..., 0].astype(int), pa0[..., 1].astype(int), pa0[..., 2].astype(int)
    pink = (rr > 85) & (bb > 85) & ((rr - gg) > 18) & ((bb - gg) > 18)
    hole = (pa0[..., 3] < 40) | pink
    pa0[hole] = base_crop[hole]
    piece = Image.fromarray(pa0, 'RGBA')

    placed = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    placed.alpha_composite(piece, (x0 + dxf, y0 + dyf))
    # dentro do retangulo, o que a IA nao pintou continua sendo o original
    filled = np.asarray(placed).copy()
    pa = np.asarray(base)
    z = filled[..., 3] < 40
    filled[z] = pa[z]
    result = base.copy()
    result.paste(Image.fromarray(filled, 'RGBA').crop(rect), (x0, y0))

    # rede de segurança: nenhum roxo/magenta sobrevive dentro da porta.
    # O que sobrar volta a ser exatamente o pixel do sprite aprovado.
    ra = np.asarray(result.convert('RGBA')).copy()
    rr, gg, bb = ra[..., 0].astype(int), ra[..., 1].astype(int), ra[..., 2].astype(int)
    pink = (rr > 85) & (bb > 85) & ((rr - gg) > 18) & ((bb - gg) > 18)
    zone = np.zeros(rr.shape, bool)
    zone[y0:y1, x0:x1] = True
    fix = pink & zone
    if fix.any():
        ra[fix] = np.asarray(base.convert('RGBA'))[fix]
    result = Image.fromarray(ra, 'RGBA')
    result.save(os.path.join(CAND, 'porta_' + name + '.png'))
    return result


RECTS = {
    'house': (24, 46, 36, 62),
    'bar': (24, 45, 38, 63),
    'quartel': (29, 53, 38, 63),
    'armazem': (17, 37, 47, 62),
    'cozinha': (33, 45, 49, 61),
    'serraria': (43, 39, 59, 62),
    'mercado': (5, 40, 14, 62),
}

if __name__ == '__main__':
    for n in (sys.argv[1:] or list(RECTS)):
        build(n, RECTS[n])
        print('porta_' + n)
