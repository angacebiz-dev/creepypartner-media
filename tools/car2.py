"""Story carousel renderer v2 (1080x1920 JPG slides) + optional slideshow video with creepy bed.
Usage: python3 car2.py spec.json [--video]
spec: {name, ritual, slides:[{text, img (rel. to wk/), focus, zoom, tint, cover?}]}  -> last slide auto = ritual + follow."""
import json, os, re, subprocess, sys, textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance

W, H = 1080, 1920
WK = "/home/claude/partner/wk/"; F = "/home/claude/partner/fonts/"
fA = lambda s: ImageFont.truetype(F + "Anton-Regular.ttf", s)
fT = lambda s: ImageFont.truetype(F + "SpecialElite.ttf", s)
fC = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
rng = np.random.default_rng(5)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
_CR = {}


def credit(path):
    d = os.path.dirname(WK + path); cf = d + "/credits.json"
    if cf not in _CR:
        _CR[cf] = json.load(open(cf)) if os.path.exists(cf) else {}
    m = _CR[cf].get(os.path.basename(path))
    if not m:
        return None
    who = re.sub(r"\s+", " ", m.get("artist") or "Unknown").replace("Unknown authorUnknown author", "Unknown").split(" from ")[0][:38]
    return f"Photo: {who} / {m.get('license', '?')} / Wikimedia Commons"


def bg_photo(path, focus=0.45, zoom=1.0, tint=None):
    im = Image.open(WK + path).convert("RGB")
    if im.width / im.height > 0.8:
        bg = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(28)); bg = ImageEnhance.Brightness(bg).enhance(0.35)
        fw = int(W * zoom); fg = im.resize((fw, int(im.height * fw / im.width)), Image.LANCZOS)
        if fg.height > 1100:
            fg = ImageOps.fit(fg, (fw, 1100), centering=(0.5, focus))
        if fw > W:
            fg = fg.crop(((fw - W) // 2, 0, (fw - W) // 2 + W, fg.height))
        bg.paste(fg, ((W - fg.width) // 2, max(250, 760 - fg.height // 2)))
        out = bg
    else:
        out = ImageOps.fit(im, (int(W * zoom), int(H * zoom)), Image.LANCZOS, centering=(0.5, focus))
        if zoom > 1:
            ox, oy = (out.width - W) // 2, int((out.height - H) * focus)
            out = out.crop((ox, oy, ox + W, oy + H))
    a = np.asarray(out).astype(np.float32)
    if tint == "grey":
        a = np.repeat(a.mean(2, keepdims=True), 3, 2) * 0.85
    elif tint == "dark":
        a = a * np.array([0.5, 0.52, 0.65], np.float32)
    return a


def center(d, y, txt, f, fill, sw=6):
    d.text(((W - d.textlength(txt, font=f)) / 2, y), txt, font=f, fill=fill, stroke_width=sw, stroke_fill=(0, 0, 0))


def render(a, s, idx, n, path=None, end=False, ritual=""):
    a = a * (1.04 - 0.45 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2)[..., None]
    g = np.clip((yy - 1050) / 600, 0, 1)[..., None] * 0.85
    gt = np.clip((420 - yy) / 420, 0, 1)[..., None] * 0.6
    a = a * (1 - g) * (1 - gt) + rng.normal(0, 5, (H, W, 1))
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    if s.get("cover"):
        f = fA(150); lines = textwrap.wrap(s["text"], 15)
        if len(lines) > 3:
            f = fA(124); lines = textwrap.wrap(s["text"], 17)
        y = 1680 - len(lines) * int(f.size * 1.08)
        for i, ln in enumerate(lines):
            center(d, y, ln, f, (255, 214, 0) if i == len(lines) - 1 else (255, 255, 255), 8); y += int(f.size * 1.08)
        center(d, 120, "PARTNER FILES", fA(52), (220, 30, 30), 4)
        center(d, 1760, "SWIPE  >>", fA(48), (235, 235, 235), 4)
    elif end:
        f = fA(96); lines = textwrap.wrap(ritual.upper(), 20); y = 1000
        for ln in lines:
            center(d, y, ln, f, (255, 214, 0), 7); y += 108
        y += 50
        center(d, y, "FOLLOW CREEPY PARTNER", fA(76), (255, 255, 255), 6); y += 110
        center(d, y, "TikTok  ·  YouTube  ·  @creepypartner", fT(44), (230, 230, 230), 3)
    else:
        f = fT(60); lines = textwrap.wrap(s["text"], 26)
        if len(lines) > 7:
            f = fT(52); lines = textwrap.wrap(s["text"], 30)
        y = 1680 - len(lines) * int(f.size * 1.32)
        for ln in lines:
            center(d, y, ln, f, (245, 240, 230), 4); y += int(f.size * 1.32)
        d.text((W - 130, 110), f"{idx + 1}/{n}", font=fA(44), fill=(230, 230, 230), stroke_width=3, stroke_fill=(0, 0, 0))
    if path:
        c = credit(path)
        if c:
            d.text((30, H - 52), c, font=fC, fill=(225, 225, 225), stroke_width=2, stroke_fill=(0, 0, 0))
    return im


def build(spec_path, video=False):
    S = json.load(open(spec_path)); out = os.path.dirname(os.path.abspath(spec_path))
    name = S["name"]; slides = S["slides"]; n = len(slides) + 1
    files = []
    for i, s in enumerate(slides):
        a = bg_photo(s["img"], s.get("focus", 0.45), s.get("zoom", 1.0), s.get("tint")) if s.get("img") else np.zeros((H, W, 3), np.float32) + 10
        im = render(a, s, i, n, s.get("img"))
        fn = f"{out}/{name}_{i + 1:02d}.jpg"; im.save(fn, quality=88); files.append(fn)
    pa = np.asarray(Image.open("/home/claude/partner/THE_PARTNER_vertical_1080x1920.png").convert("RGB")).astype(np.float32) * 0.55
    im = render(pa, {}, n - 1, n, end=True, ritual=S["ritual"])
    fn = f"{out}/{name}_{n:02d}.jpg"; im.save(fn, quality=88); files.append(fn)
    sheet = Image.new("RGB", (216 * n, 384))
    for i, f in enumerate(files):
        sheet.paste(Image.open(f).resize((216, 384)), (i * 216, 0))
    sheet.save(f"{out}/{name}_sheet.png")
    print(name, n, "slides", max(os.path.getsize(f) for f in files), "max bytes")
    if video:
        slideshow(files, f"{out}/{name}_slideshow.mp4")
    return files


def slideshow(files, out, per=3.4, first=2.6):
    """Slides as a video: slow push-in per slide, quick dark dip between slides, creepy drone + music box."""
    from scipy.io import wavfile
    FPS = 30; durs = [first] + [per] * (len(files) - 1); total = sum(durs)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out + ".v.mp4"], stdin=subprocess.PIPE)
    for f, du in zip(files, durs):
        img = Image.open(f).convert("RGB"); nfr = int(du * FPS)
        for k in range(nfr):
            z = 1.0 + 0.035 * k / nfr; cw, ch = int(W / z), int(H / z)
            fr = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
            a = np.asarray(fr).astype(np.float32)
            if k < 4: a *= 0.25 + 0.75 * k / 4
            if k > nfr - 4: a *= 0.25 + 0.75 * (nfr - k) / 4
            ff.stdin.write(np.clip(a, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait()
    SR = 44100; n = int(SR * total); t = np.arange(n) / SR
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t)
    bed = (np.sin(2 * np.pi * 36.7 * t) + 0.7 * np.sin(2 * np.pi * 37.3 * t) + 0.45 * np.sin(2 * np.pi * 55 * t)) * lfo * 0.5
    notes = [440, 523.25, 659.25, 493.88, 415.3, 523.25, 440, 392]
    for k, s0 in enumerate(np.arange(0.4, total - 2, 1.7)):
        i0 = int(s0 * SR); L = int(1.4 * SR); e = np.exp(-np.linspace(0, 6, L)); f = notes[k % 8] * 0.985
        seg = e * (np.sin(2 * np.pi * f * t[:L]) + 0.3 * np.sin(2 * np.pi * 2 * f * t[:L])) * 0.35
        bed[i0:i0 + L] += seg[:max(0, min(L, n - i0))]
    acc = 0.0
    for du in durs:  # low thump on each slide change
        i0 = int(acc * SR); L = int(1.2 * SR); e = np.exp(-np.linspace(0, 7, L))
        bed[i0:i0 + L] += (e * np.sin(2 * np.pi * np.cumsum(np.linspace(70, 32, L)) / SR) * 0.8)[:max(0, min(L, n - i0))]
        acc += du
    bed *= np.clip(t / 0.5, 0, 1) * np.clip((total - t) / 1.2, 0, 1); bed = bed / np.abs(bed).max() * 0.7
    wavfile.write(out + ".a.wav", SR, np.stack([bed, bed], 1).astype(np.float32))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out + ".v.mp4", "-i", out + ".a.wav", "-c:v", "libx264", "-preset", "medium",
                    "-b:v", "5M", "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
                    "-shortest", "-movflags", "+faststart", out], check=True)
    dur = total; vb = int((2_780_000 * 8 / dur - 64000) / 1000); light = out.replace(".mp4", "_light.mp4")
    vf = "scale=720:1280:flags=lanczos"; pl = out + ".plog"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vb}k",
                    "-pass", "1", "-passlogfile", pl, "-an", "-f", "mp4", "/dev/null"], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", out, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vb}k",
                    "-maxrate", f"{int(vb * 1.4)}k", "-bufsize", f"{int(vb * 2.8)}k", "-pass", "2", "-passlogfile", pl,
                    "-c:a", "aac", "-b:a", "64k", "-ar", "48000", "-movflags", "+faststart", light], check=True)
    for p in [out + ".v.mp4", out + ".a.wav"]:
        os.remove(p)
    print("slideshow", out, round(total, 1), "s; light", os.path.getsize(light))


if __name__ == "__main__":
    build(sys.argv[1], video="--video" in sys.argv)
