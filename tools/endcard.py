"""3-second end card: comment prompt + follow Creepy Partner (TikTok / YouTube written out, no logos).
Usage: python3 endcard.py "<COMMENT LINE>" out.mp4"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
from scipy.io import wavfile

W, H, FPS, DUR = 1080, 1920, 30, 3.2
F = "/home/claude/partner/fonts/"
from PIL import ImageFont
A = lambda s: ImageFont.truetype(F + "Anton-Regular.ttf", s)
comment = sys.argv[1] if len(sys.argv) > 1 else "COMMENT \"YES\" IF YOU'D GO"
out = sys.argv[2] if len(sys.argv) > 2 else "endcard.mp4"

base = Image.open("/home/claude/partner/THE_PARTNER_vertical_1080x1920.png").convert("RGB")
bg = ImageEnhance.Brightness(base.filter(ImageFilter.GaussianBlur(6))).enhance(0.35)
face = base.crop((140, 380, 940, 1180)).resize((560, 560), Image.LANCZOS)
m = Image.new("L", face.size, 0); ImageDraw.Draw(m).ellipse((0, 0, 559, 559), fill=255)


def centered(d, y, txt, f, fill, sw=6):
    d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0))


def pill(d, cx, y, txt, fill, tc):
    f = A(62); tw = d.textlength(txt, font=f); pw = tw + 90
    d.rounded_rectangle((cx - pw/2, y, cx + pw/2, y + 110), radius=55, fill=fill, outline=(255, 255, 255), width=4)
    d.text((cx - tw/2, y + 14), txt, font=f, fill=tc)


frames = []
rng = np.random.default_rng(2)
# bed first
SR = 44100; n = int(SR * DUR); t = np.arange(n) / SR
bed = (np.sin(2*np.pi*36.7*t) + 0.6*np.sin(2*np.pi*55*t)) * np.clip(t/0.3, 0, 1) * np.clip((DUR - t)/0.8, 0, 1)
bed += np.exp(-t*2.5) * np.sin(2*np.pi*np.cumsum(np.interp(t, [0, 1.5], [80, 30]))/SR)
bed = (bed / np.abs(bed).max() * 0.35).astype(np.float32)
wavfile.write("endcard_bed.wav", SR, np.stack([bed, bed], 1))
ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                       "-i", "-", "-f", "wav", "-i", "endcard_bed.wav", "-c:v", "libx264", "-preset", "medium", "-b:v", "6M",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", out], stdin=subprocess.PIPE)
def _fit(txt, start=88, minsz=66):
    _d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    sz = start
    while _d.textlength(txt, font=A(sz)) > 1000 and sz > minsz:
        sz -= 4
    return sz, _d.textlength(txt, font=A(sz)) <= 1000
_sz, _ok = _fit(comment)
if _ok:
    CLINES = [(900, comment, A(_sz))]
else:  # two lines
    w = comment.split(" "); best = None
    for k in range(1, len(w)):
        a, b = " ".join(w[:k]), " ".join(w[k:]); mx = max(len(a), len(b))
        if best is None or mx < best[0]: best = (mx, a, b)
    a, b = best[1], best[2]
    _d = ImageDraw.Draw(Image.new("RGB", (10, 10))); sz = 84
    while max(_d.textlength(a, font=A(sz)), _d.textlength(b, font=A(sz))) > 1000 and sz > 50:
        sz -= 4
    CLINES = [(872, a, A(sz)), (872 + int(sz * 1.08), b, A(sz))]
for i in range(int(DUR * FPS)):
    tt = i / FPS; p = min(tt / 0.35, 1.0)
    fr = bg.copy(); d = ImageDraw.Draw(fr)
    z = 1.0 + 0.03 * tt
    fc = face.resize((int(560*z), int(560*z)), Image.LANCZOS); mm = m.resize(fc.size)
    fr.paste(fc, ((W - fc.width)//2, 260 - (fc.height - 560)//2), mm)
    d.ellipse(((W-560)//2 - 6, 254, (W+560)//2 + 6, 826), outline=(220, 30, 30), width=8)
    for _y, _t, _f in CLINES:
        centered(d, _y, _t, _f, (255, 214, 0))
    centered(d, 1080, "FOLLOW", A(80), (255, 255, 255))
    centered(d, 1180, "CREEPY PARTNER", A(118), (255, 255, 255), 8)
    if tt > 0.25:
        pill(d, W/2 - 230, 1420, "TikTok", (12, 12, 12), (255, 255, 255))
        pill(d, W/2 + 230, 1420, "YouTube", (200, 20, 20), (255, 255, 255))
    centered(d, 1600, "@creepypartner", A(64), (230, 230, 230), 4)
    a = np.asarray(fr).astype(np.float32) * p + rng.normal(0, 5, (H, W, 1))
    ff.stdin.write(np.clip(a, 0, 255).astype(np.uint8).tobytes())
ff.stdin.close(); ff.wait()
print("endcard", out)
