"""Cut low-poly twin frames (1200x880, dark brown background) to 56x36 sprite frames.

Used only for approval previews: nothing is copied into assets/ by this script.
Steps: background distance mask -> largest connected blob -> bbox -> scale so the
content fits 54x34 keeping aspect -> feet on the last row (y=35) -> centred horizontally.
Usage: python tools/cut_gemeos_lowpoly.py SRC.png DST.png
"""
import sys
from PIL import Image, ImageFilter

BG = (55, 27, 8)
THRESH = 32
CANVAS = (56, 36)
MAX_W, MAX_H = 54, 34


def mask_of(im):
    px = im.load()
    w, h = im.size
    m = Image.new('L', (w, h), 0)
    mp = m.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            d = ((r - BG[0]) ** 2 + (g - BG[1]) ** 2 + (b - BG[2]) ** 2) ** 0.5
            if d > THRESH:
                mp[x, y] = 255
    # remove specks, then close small holes
    m = m.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    return m


def cut(src, dst):
    im = Image.open(src).convert('RGB')
    m = mask_of(im)
    bbox = m.getbbox()
    if bbox is None:
        raise SystemExit('empty mask: ' + src)
    crop = im.crop(bbox)
    mcrop = m.crop(bbox)
    cw, ch = crop.size
    s = min(MAX_W / cw, MAX_H / ch)
    nw, nh = max(1, round(cw * s)), max(1, round(ch * s))
    crop = crop.resize((nw, nh), Image.BOX)
    mcrop = mcrop.resize((nw, nh), Image.BOX).point(lambda v: 255 if v >= 90 else 0)
    out = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
    ox = (CANVAS[0] - nw) // 2
    oy = CANVAS[1] - nh
    rgba = crop.convert('RGBA')
    rgba.putalpha(mcrop)
    out.paste(rgba, (ox, oy))
    out.save(dst, optimize=True)
    return out


if __name__ == '__main__':
    cut(sys.argv[1], sys.argv[2])
