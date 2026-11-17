import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
def make_cover(src, title, out, sub="CREEPY PARTNER", focus_y=0.45):
    W, H = 1080, 1920
    im = Image.open(src).convert("RGB")
    s = max(W/im.width, H/im.height); im = im.resize((int(im.width*s)+1, int(im.height*s)+1), Image.LANCZOS)
    x0 = (im.width-W)//2; y0 = int(max(0, min(im.height-H, im.height*focus_y - H/2)))
    im = im.crop((x0, y0, x0+W, y0+H))
    im = ImageEnhance.Contrast(im).enhance(1.15)
    # dark gradient top + bottom for text
    g = Image.new("L", (W, H), 0); d = ImageDraw.Draw(g)
    for y in range(H):
        a = 0
        if y < 760: a = int(205*(1-y/760)**1.3)
        if y > H-520: a = max(a, int(180*((y-(H-520))/520)**1.5))
        d.line((0, y, W, y), fill=a)
    im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, g)
    d = ImageDraw.Draw(im)
    F = "/home/claude/partner/fonts/Anton-Regular.ttf"
    # wrap title to fit
    size = 150
    words = title.upper().split()
    while True:
        f = ImageFont.truetype(F, size); lines, cur = [], ""
        for w in words:
            t = (cur+" "+w).strip()
            if d.textlength(t, font=f) > W-120 and cur: lines.append(cur); cur = w
            else: cur = t
        lines.append(cur)
        if len(lines) <= 3 or size < 90: break
        size -= 10
    y = 170
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=f)
        col = (255, 214, 0) if i == len(lines)-1 else (255, 255, 255)
        d.text(((W-tw)/2, y), ln, font=f, fill=col, stroke_width=8, stroke_fill=(0, 0, 0))
        y += int(size*1.12)
    fs = ImageFont.truetype(F, 54); tw = d.textlength(sub, font=fs)
    d.text(((W-tw)/2, H-190), sub, font=fs, fill=(200, 30, 30), stroke_width=4, stroke_fill=(0, 0, 0))
    im.save(out, quality=92)
if __name__ == "__main__":
    make_cover(sys.argv[1], sys.argv[2], sys.argv[3])
