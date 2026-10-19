import sys, os
sys.path.insert(0, '/home/user/Goblin-game/tools')
from PIL import Image
from cut_gemeos_lowpoly import mask_of, CANVAS, MAX_W, MAX_H

def robust_extent(m, min_count=6):
    w, h = m.size; px = m.load()
    colc = [0]*w; rowc = [0]*h
    for y in range(h):
        for x in range(w):
            if px[x, y] >= 128:
                colc[x] += 1; rowc[y] += 1
    xs = [x for x in range(w) if colc[x] >= min_count]
    ys = [y for y in range(h) if rowc[y] >= min_count]
    return (min(xs), min(ys), max(xs)+1, max(ys)+1)

def cut_set(files, outdir):
    info = {}
    for f in files:
        im = Image.open(f).convert('RGB'); m = mask_of(im)
        info[f] = (im, m, m.getbbox(), robust_extent(m))
    rw = max(e[2]-e[0] for *_, e in info.values())
    rh = max(e[3]-e[1] for *_, e in info.values())
    s = min(MAX_W / rw, MAX_H / rh)
    os.makedirs(outdir, exist_ok=True)
    for f, (im, m, bb, ex) in info.items():
        crop = im.crop(bb); mc = m.crop(bb)
        cw, ch = crop.size
        nw, nh = max(1, round(cw*s)), max(1, round(ch*s))
        crop = crop.resize((nw, nh), Image.BOX)
        mc = mc.resize((nw, nh), Image.BOX).point(lambda v: 255 if v >= 90 else 0)
        # centre on the robust body extent, feet on the last row
        body_cx = ((ex[0]+ex[2])/2 - bb[0]) * s
        ox = round(CANVAS[0]/2 - body_cx)
        oy = CANVAS[1] - nh
        out = Image.new('RGBA', CANVAS, (0, 0, 0, 0))
        rgba = crop.convert('RGBA'); rgba.putalpha(mc)
        out.alpha_composite(rgba, (max(0, ox), oy), (max(0, -ox), 0, nw, nh) and None) if False else out.paste(rgba, (ox, oy), rgba)
        out.save(os.path.join(outdir, os.path.basename(f)), optimize=True)
    print(outdir, 'scale', round(s, 4), 'robust', rw, rh, 'frames', len(info), flush=True)

if __name__ == '__main__':
    cut_set(sys.argv[2:], sys.argv[1])
