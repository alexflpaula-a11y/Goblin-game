#!/usr/bin/env python3
"""
replay_preview.py — Reproduz o JSON do render_preview.mjs num PNG.

Não é um canvas completo: é um replay fiel o bastante para conferir
LAYOUT (posições, sobreposições, textos) das telas do jogo, com os
sprites reais. Uso:

    python3 tools/replay_preview.py armazem equip market world
"""
import json
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'tools', 'preview')
SCALE = 2
W, H = 640, 360

# ---------------- cores ----------------
def parse_color(c):
    if c is None:
        return (0, 0, 0, 255)
    if isinstance(c, (list, tuple)):
        return tuple(c)
    c = c.strip()
    if c.startswith('#'):
        h = c[1:]
        if len(h) == 3:
            h = ''.join(ch * 2 for ch in h)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
    m = re.match(r'rgba?\(([^)]+)\)', c)
    if m:
        parts = [float(p) for p in m.group(1).split(',')]
        r, g, b = [int(p) for p in parts[:3]]
        a = int(parts[3] * 255) if len(parts) > 3 else 255
        return (r, g, b, a)
    named = {'black': (0, 0, 0, 255), 'white': (255, 255, 255, 255)}
    return named.get(c, (255, 0, 255, 255))


def with_alpha(color, alpha):
    r, g, b, a = color
    return (r, g, b, int(a * alpha))


# ---------------- fontes ----------------
_font_cache = {}

def get_font(spec):
    m = re.search(r'(\d+)px', spec or '')
    size = int(m.group(1)) if m else 10
    if size not in _font_cache:
        try:
            _font_cache[size] = ImageFont.load_default(size=size)
        except TypeError:
            _font_cache[size] = ImageFont.load_default()
    return _font_cache[size]


def text_anchor(align, base):
    h = {'left': 'l', 'center': 'm', 'right': 'r'}.get(align, 'l')
    v = 'm' if base == 'middle' else 's'   # s = baseline
    return h + v


# ---------------- camadas (save/restore/clip) ----------------
class Layer:
    def __init__(self):
        self.img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)
        self.clip = None   # PIL Image máscara L


class Replay:
    def __init__(self, data):
        self.sprites = {}
        self.stack = [Layer()]
        self.calls = data['calls']

    @property
    def layer(self):
        return self.stack[-1]

    # ----- sprites -----
    def sprite(self, src):
        if src not in self.sprites:
            p = os.path.join(ROOT, src) if src else None
            self.sprites[src] = Image.open(p).convert('RGBA') if p and os.path.exists(p) else None
        return self.sprites[src]

    # ----- ops -----
    def replay(self):
        for c in self.calls:
            getattr(self, 'op_' + c['op'])(c)

    def color(self, c, alpha=1.0):
        return with_alpha(parse_color(c), alpha)

    def op_save(self, c):
        self.stack.append(Layer())

    def op_restore(self, c):
        if len(self.stack) > 1:
            top = self.stack.pop()
            base = self.stack[-1]
            if top.clip is not None:
                transparent = Image.new('RGBA', (W, H), (0, 0, 0, 0))
                masked = Image.composite(top.img, transparent, top.clip)
                base.img.alpha_composite(masked)
            else:
                base.img.alpha_composite(top.img)

    def op_clip(self, c):
        # só suportamos clip de retângulo/retângulo-arredondado (o que o jogo usa)
        mask = Image.new('L', (W, H), 0)
        d = ImageDraw.Draw(mask)
        for op in c['ops']:
            if op[0] == 'roundrect':
                x, y, w, h, r = op[1], op[2], op[3], op[4], (op[5] if len(op) > 5 else 6)
                if isinstance(r, (list, tuple)):
                    r = r[0]
                d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=255)
            elif op[0] == 'rect':
                x, y, w, h = op[1:5]
                d.rectangle([x, y, x + w, y + h], fill=255)
        self.layer.clip = mask

    def op_fillRect(self, c):
        x, y, w, h = c['args']
        self.layer.draw.rectangle([x, y, x + w, y + h], fill=self.color(c['style'], c.get('alpha', 1)))

    def op_strokeRect(self, c):
        x, y, w, h = c['args']
        lw = max(1, int(round(c.get('lw', 1))))
        self.layer.draw.rectangle([x, y, x + w, y + h],
                                  outline=self.color(c['style'], c.get('alpha', 1)), width=lw)

    def op_fillText(self, c):
        t, x, y = c['args']
        f = get_font(c.get('font'))
        a = text_anchor(c.get('align', 'left'), c.get('base', 'alphabetic'))
        self.layer.draw.text((x, y), t, font=f, fill=self.color(c['style'], c.get('alpha', 1)),
                             anchor=a)

    def op_setLineDash(self, c):
        pass  # traço pontilhado: aproximado por linha sólida fina

    def op_drawImage(self, c):
        img = self.sprite(c['src'])
        if img is None:
            return
        a = c['args']
        if len(a) == 2:      # drawImage(img, dx, dy)
            dx, dy, dw, dh = a[0], a[1], img.width, img.height
        elif len(a) == 4:    # drawImage(img, dx, dy, dw, dh)
            dx, dy, dw, dh = a
        else:                # drawImage(img, sx, sy, sw, sh, dx, dy, dw, dh)
            sx, sy, sw, sh, dx, dy, dw, dh = a
            img = img.crop((sx, sy, sx + sw, sy + sh))
        if dw != img.width or dh != img.height:
            img = img.resize((max(1, int(dw)), max(1, int(dh))), Image.NEAREST)
        self.layer.img.alpha_composite(img, (int(dx), int(dy)))

    # ----- paths -----
    def _path_shapes(self, ops):
        """Separa o path em primitivas PIL: rect/roundrect/polígono/círculo."""
        rects, rounds, polys, lines, circles, ellipses = [], [], [], [], [], []
        pts = []
        def flush_poly():
            if len(pts) >= 2:
                polys.append(list(pts))
                lines.append(list(pts))
            pts.clear()
        for op in ops:
            k = op[0]
            if k == 'M':
                flush_poly()
                pts.append((op[1], op[2]))
            elif k == 'L':
                pts.append((op[1], op[2]))
            elif k == 'close':
                flush_poly()
            elif k == 'rect':
                rects.append(op[1:5])
            elif k == 'roundrect':
                r = op[5] if len(op) > 5 else 6
                if isinstance(r, (list, tuple)):
                    r = r[0]
                rounds.append((op[1], op[2], op[3], op[4], r))
            elif k == 'arc':
                circles.append((op[1], op[2], op[3]))  # círculo completo no jogo
            elif k == 'ellipse':
                ellipses.append((op[1], op[2], op[3], op[4]))
        flush_poly()
        return rects, rounds, polys, lines, circles, ellipses

    def op_path(self, c):
        d = self.layer.draw
        rects, rounds, polys, lines, circles, ellipses = self._path_shapes(c['ops'])
        style = c.get('style')
        alpha = c.get('alpha', 1)

        # gradiente radial (ui.glow): círculo preenchido com degradê
        if isinstance(style, dict) and style.get('_grad') and circles:
            self._radial_glow(style, circles[0])
            return

        if c['sub'] == 'fill':
            col = self.color(style, alpha)
            for x, y, w, h in rects:
                d.rectangle([x, y, x + w, y + h], fill=col)
            for x, y, w, h, r in rounds:
                d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=col)
            for pts in polys:
                if len(pts) >= 3:
                    d.polygon(pts, fill=col)
            for cx, cy, r in circles:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
            for cx, cy, rx, ry in ellipses:
                d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=col)
        else:
            col = self.color(style, alpha)
            lw = max(1, int(round(c.get('lw', 1))))
            for x, y, w, h in rects:
                d.rectangle([x, y, x + w, y + h], outline=col, width=lw)
            for x, y, w, h, r in rounds:
                d.rounded_rectangle([x, y, x + w, y + h], radius=r, outline=col, width=lw)
            for pts in lines:
                d.line(pts, fill=col, width=lw)
            for cx, cy, r in circles:
                d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=lw)

    def _radial_glow(self, style, circle):
        cx, cy, r = circle
        grad = style['_grad']
        stops = style.get('stops') or [(0, 'rgba(255,232,160,0.5)'), (1, 'rgba(255,232,160,0)')]
        c0 = parse_color(stops[0][1])
        c1 = parse_color(stops[-1][1])
        size = int(r * 2) + 2
        patch = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        px = patch.load()
        for y in range(size):
            for x in range(size):
                dist = math.hypot(x - r, y - r) / max(1, r)
                if dist > 1:
                    continue
                t = dist
                col = tuple(int(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
                a = int(c0[3] + (c1[3] - c0[3]) * t)
                px[x, y] = (col[0], col[1], col[2], a)
        self.layer.img.alpha_composite(patch, (int(cx - r - 1), int(cy - r - 1)))

    # ----- transforms ignorados (prévia 1:1 no espaço lógico) -----
    def op_setTransform(self, c): pass
    def op_translate(self, c): pass
    def op_scale(self, c): pass


def main(names):
    for name in names:
        src = os.path.join(OUT, name + '.json')
        if not os.path.exists(src):
            print(f'!! {name}: gere primeiro com  node tools/render_preview.mjs "?demo={name}"')
            continue
        with open(src, encoding='utf-8') as f:
            data = json.load(f)
        r = Replay(data)
        r.replay()
        img = r.stack[0].img
        if SCALE != 1:
            img = img.resize((W * SCALE, H * SCALE), Image.NEAREST)
        dst = os.path.join(OUT, name + '.png')
        img.convert('RGB').save(dst)
        print(f'OK → {os.path.relpath(dst, ROOT)}')


if __name__ == '__main__':
    main(sys.argv[1:] or ['world'])
