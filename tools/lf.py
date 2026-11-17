"""Creepy Partner LONG-FORM builder (YouTube, 1920x1080, 24 fps).
Usage: python3 lf.py <dir>/spec.json [--revoice] [--rerender] [--preview N]   (image paths relative to /home/claude/partner/wk)
spec: {id, title_top, comment, lines:[{id, text, pause?, chapter?, hit?, overlay?, shots:[{img, mode(in|out|face|up|down|pan), tint(night|grey|dark|sepia), focus}]}]}
Lines with no shots show the talking Partner (intro + outro). Years are spoken naturally via spoken.say().
Output: <dir>/CreepyPartner_LF_<id>.mp4 (two-pass, under 95 MB for the GitHub raw route) + sheet.png
"""
import json, math, os, re, subprocess, sys
import numpy as np, soundfile as sf, cv2
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "/home/claude/partner/video02"); sys.path.insert(0, "/home/claude/partner")
from tts import creepy
from spoken import say

WK = "/home/claude/partner/wk/"; FONTS = "/home/claude/partner/fonts/"
W, H, FPS = 1920, 1080, 24
spec = json.load(open(sys.argv[1])); OUT = os.path.dirname(os.path.abspath(sys.argv[1])); os.chdir(OUT)
ID = spec["id"]
PREVIEW = int(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else 0

# ---------------- voice ----------------
if not os.path.exists("voice.wav") or "--revoice" in sys.argv:
    from kokoro_onnx import Kokoro
    k = Kokoro('/home/claude/tts/kokoro-v1.0.onnx', '/home/claude/tts/voices-v1.0.bin')
    SR = 44100; t = 1.0; audio = [np.zeros(int(SR * 1.0))]; tl = []
    for L in spec["lines"]:
        segf = f"seg_{L['id']}.wav"
        s, sr = k.create(say(L["text"]), voice="bm_lewis", speed=spec.get("speed", 0.86), lang="en-us")
        sf.write("tmp.wav", s, sr); creepy("tmp.wav", segf, semis=-2.5)
        a, _ = sf.read(segf); a = a.mean(1) if a.ndim > 1 else a
        nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(nz[0] - 400, 0): nz[-1] + 1500]
        pre = 1.2 if L.get("chapter") else 0.0
        audio.append(np.zeros(int(SR * pre))); t += pre
        d = len(a) / SR; tl.append({"id": L["id"], "start": round(t, 3), "end": round(t + d, 3)})
        p = L.get("pause", 0.45); audio += [a, np.zeros(int(SR * p))]; t += d + p
    sf.write("voice.wav", np.concatenate(audio), SR); json.dump(tl, open("timeline.json", "w"), indent=1)
TL = {x["id"]: x for x in json.load(open("timeline.json"))}
LN = {L["id"]: L for L in spec["lines"]}
ORDER = [L["id"] for L in spec["lines"]]
TOTAL = TL[ORDER[-1]]["end"] + 3.0
print("voice", round(TOTAL, 1), "s =", round(TOTAL / 60, 2), "min", flush=True)

# ---------------- shots ----------------
SH = []
for i, lid in enumerate(ORDER):
    t0 = 0 if i == 0 else TL[lid]["start"] - 0.2 - (1.2 if LN[lid].get("chapter") else 0)
    t1 = (TL[ORDER[i + 1]]["start"] - 0.2 - (1.2 if LN[ORDER[i + 1]].get("chapter") else 0)) if i + 1 < len(ORDER) else TOTAL
    shots = LN[lid].get("shots") or [None]
    for j, s in enumerate(shots):
        SH.append((t0 + (t1 - t0) * j / len(shots), t0 + (t1 - t0) * (j + 1) / len(shots), s, lid))

CREDITS = {}
def credit(path):
    d = os.path.dirname(WK + path); cf = d + "/credits.json"
    if cf not in CREDITS:
        CREDITS[cf] = json.load(open(cf)) if os.path.exists(cf) else {}
    m = CREDITS[cf].get(os.path.basename(path))
    if not m:
        return None
    if m.get("text"):
        return m["text"]
    who = re.sub(r"\s+", " ", m.get("artist") or "Unknown").split(" from ")[0][:44]
    return f"Photo: {who} / {m.get('license') or '?'} / {m.get('src', 'Wikimedia Commons')}"

EX = 1.18
IMG = {}
def load(path, tint):
    key = (path, tint)
    if key in IMG:
        return IMG[key]
    im = Image.open(WK + path).convert("RGB")
    tw, th = int(W * EX), int(H * EX)
    if im.width / im.height < 1.45:  # portrait / square: blurred fill + framed photo
        bg = im.resize((tw, int(im.height * tw / im.width))).crop((0, 0, tw, th)) if im.height * tw / im.width >= th else im.resize((int(im.width * th / im.height), th))
        bg = bg.resize((tw, th)).filter(ImageFilter.GaussianBlur(40))
        bg = Image.fromarray((np.asarray(bg).astype(np.float32) * 0.3).astype(np.uint8))
        fh = int(th * 0.9); fw = int(im.width * fh / im.height)
        if fw > tw * 0.9:
            fw = int(tw * 0.9); fh = int(im.height * fw / im.width)
        fg = im.resize((fw, fh), Image.LANCZOS)
        bg.paste(fg, ((tw - fw) // 2, (th - fh) // 2))
        a = np.asarray(bg).astype(np.float32)
    else:
        s = max(tw / im.width, th / im.height)
        im2 = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
        x0 = (im2.width - tw) // 2; y0 = (im2.height - th) // 2
        a = np.asarray(im2.crop((x0, y0, x0 + tw, y0 + th))).astype(np.float32)
    if tint == "night":
        a = a * np.array([0.42, 0.46, 0.66], np.float32)
    elif tint == "grey":
        a = np.repeat(a.mean(2, keepdims=True), 3, 2) * 0.85
    elif tint == "dark":
        a = a * 0.6
    elif tint == "sepia":
        g = a.mean(2, keepdims=True); a = np.concatenate([g * 1.0, g * 0.88, g * 0.68], 2) * 0.9
    a = np.clip(a * 1.06 - 6, 0, 255).astype(np.uint8)
    IMG[key] = a
    if len(IMG) > 40:
        IMG.pop(next(iter(IMG)))
    return a

def still(s, t0, t1, t):
    a = load(s["img"], s.get("tint")); ah, aw = a.shape[:2]
    p = (t - t0) / max(t1 - t0, 0.01); p = p * p * (3 - 2 * p) * 0.6 + p * 0.4
    mode = s.get("mode", "in"); fy = s.get("focus", 0.5); fx = s.get("focus_x", 0.5)
    cx = aw * fx; cy = ah * fy
    if mode == "in":
        z = 1.0 + 0.1 * p
    elif mode == "out":
        z = 1.1 - 0.1 * p
    elif mode == "face":
        z = 1.35 + 0.15 * p
    else:
        z = 1.02
        span = (ah - ah / EX / z) / 2
        cy = ah / 2 + span * (1 - 2 * p) * (1 if mode == "up" else -1) if mode in ("up", "down") else ah / 2
        if mode == "pan":
            cx = aw / 2 + (aw - aw / EX / z) / 2 * (2 * p - 1)
    cw, ch = aw / EX / z, ah / EX / z
    x0 = float(np.clip(cx - cw / 2, 0, aw - cw)); y0 = float(np.clip(cy - ch / 2, 0, ah - ch))
    M = np.array([[cw / W, 0, x0], [0, ch / H, y0]], np.float32)
    return cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_REFLECT)

# talking Partner (vertical art -> host shot on the right, title on the left)
VW, VH = 1080, 1920
base = Image.open("/home/claude/partner/THE_PARTNER_vertical_1080x1920.png").convert("RGB")
OX, OY = 250, 500
CURVE = [(OX + x, OY + y) for x, y in [(120, 390), (200, 409), (310, 393), (410, 343), (487, 262)]]
jaw_poly = CURVE + [(OX + 600, OY + 330), (OX + 560, OY + 640), (OX + 60, OY + 640), (OX + 60, OY + 420)]
jm = Image.new("L", (VW, VH), 0); ImageDraw.Draw(jm).polygon(jaw_poly, fill=255); jm = jm.filter(ImageFilter.GaussianBlur(5))
jaw = base.copy(); jaw.putalpha(jm)
va, VSR = sf.read("voice.wav"); va = va.mean(1) if va.ndim > 1 else va
hop = VSR // FPS
ENV = np.array([np.sqrt(np.mean(va[i * hop:(i + 1) * hop] ** 2)) for i in range(len(va) // hop)])
ENV = ENV / (np.percentile(ENV, 97) + 1e-9)
OPEN = np.zeros(len(ENV))
for i in range(len(ENV)):
    OPEN[i] = (OPEN[i - 1] if i else 0) * 0.45 + np.clip(ENV[i], 0, 1) * 0.55
PS = 0.78; PW, PH = int(VW * PS), int(VH * PS)
PX = 1880 - PW; PY = -int(150 * PS)
BGP = cv2.GaussianBlur(cv2.resize(np.asarray(base)[300:1400], (W, H)), (0, 0), 35)
BGP = (BGP.astype(np.float32) * 0.35).astype(np.uint8)
feather = np.ones(PW, np.float32); fl = 120
feather[:fl] = np.linspace(0, 1, fl); feather[-fl:] = np.linspace(1, 0, fl)
FEA = feather[None, :, None]
fT = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 120); fS = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 54)
def title_layer(txt):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.text((110, 330), "PARTNER FILES", font=fS, fill=(255, 214, 0), stroke_width=4, stroke_fill=(0, 0, 0))
    for i, ln in enumerate(txt.split("\n")):
        d.text((105, 400 + i * 135), ln, font=fT, fill=(240, 240, 240), stroke_width=6, stroke_fill=(0, 0, 0))
    return np.asarray(im).astype(np.float32)
TITLE = title_layer(spec["title_top"])

def partner(fi, t, t0, t1, show_title):
    d = 30 * OPEN[min(fi, len(OPEN) - 1)]
    fr = base.copy()
    gap = CURVE + [(x + 0.3 * d, y + d) for x, y in reversed(CURVE)]
    g = Image.new("L", (VW, VH), 0); ImageDraw.Draw(g).polygon(gap, fill=255); g = g.filter(ImageFilter.GaussianBlur(3))
    fr.paste((22, 10, 10), (0, 0), g); fr.paste(jaw, (int(0.3 * d), int(d)), jaw)
    p = (t - t0) / max(t1 - t0, 0.01); z = 1.0 + 0.05 * p; bob = 4 * math.sin(t * 1.7)
    fg = cv2.resize(np.asarray(fr), (int(PW * z), int(PH * z)), interpolation=cv2.INTER_AREA)
    ox = (fg.shape[1] - PW) // 2; oy = int((fg.shape[0] - PH) * 0.35 + bob) + max(0, -PY)
    fg = fg[oy:oy + H, ox:ox + PW].astype(np.float32)
    out = BGP.astype(np.float32).copy()
    hh = min(H, fg.shape[0])
    out[:hh, PX:PX + PW] = out[:hh, PX:PX + PW] * (1 - FEA) + fg[:hh] * FEA
    if show_title:
        a = TITLE[..., 3:4] / 255.0 * min(1, (t - t0) / 0.6)
        out = out * (1 - a) + TITLE[..., :3] * a
    out *= 0.93 + 0.07 * (math.sin(t * 31) > 0.7)
    return np.clip(out, 0, 255).astype(np.uint8)

fC = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
fCh = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 92); fChs = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 44)
fO = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 100)
LAY = {}
def layer(kind, txt):
    k = kind + txt
    if k not in LAY:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if kind == "cr":
            tw = d.textlength(txt, font=fC)
            d.text((W - tw - 36, H - 52), txt, font=fC, fill=(235, 235, 235, 200), stroke_width=2, stroke_fill=(0, 0, 0, 200))
        elif kind == "ch":
            num, _, name = txt.partition("|")
            d.rectangle((90, 120, 104, 290), fill=(255, 214, 0))
            d.text((130, 110), num, font=fChs, fill=(255, 214, 0), stroke_width=3, stroke_fill=(0, 0, 0))
            d.text((128, 165), name, font=fCh, fill=(245, 245, 245), stroke_width=5, stroke_fill=(0, 0, 0))
        else:
            for i, ln in enumerate(txt.split("\n")):
                tw = d.textlength(ln, font=fO)
                d.text(((W - tw) / 2, 140 + i * 115), ln, font=fO, fill=(255, 40, 40), stroke_width=6, stroke_fill=(0, 0, 0))
        LAY[k] = (np.asarray(im)[..., :3].astype(np.float32), np.asarray(im)[..., 3:4].astype(np.float32) / 255.0)
    return LAY[k]
def comp(fr, L, alpha=1.0):
    rgb, a = L; a = a * alpha
    return fr * (1 - a) + rgb * a

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1.06 - 0.55 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.0)[..., None]
first_story = next(i for i, x in enumerate(SH) if x[2] is not None)

if not os.path.exists("frames.mp4") or "--rerender" in sys.argv or PREVIEW:
    nfr = int(TOTAL * FPS)
    frames = range(nfr) if not PREVIEW else [int(nfr * (i + 0.5) / PREVIEW) for i in range(PREVIEW)]
    if not PREVIEW:
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt",
                               "yuv420p", "frames.mp4"], stdin=subprocess.PIPE)
    shots_i = 0
    for n, fi in enumerate(frames):
        t = fi / FPS
        while shots_i + 1 < len(SH) and t >= SH[shots_i][1]:
            shots_i += 1
        if PREVIEW:
            shots_i = next((i for i, x in enumerate(SH) if x[0] <= t < x[1]), len(SH) - 1)
        t0, t1, s, lid = SH[shots_i]
        if s is None:
            fr = partner(fi, t, t0, t1, shots_i < first_story).astype(np.float32)
        else:
            fr = still(s, t0, t1, t).astype(np.float32)
        dt = t - t0
        if dt < 0.35 and t0 > 0.1:  # quick dip-from-black between shots
            fr *= 0.35 + 0.65 * dt / 0.35
        if t1 - t < 0.2 and t < TOTAL - 0.5:
            fr *= 0.35 + 0.65 * (t1 - t) / 0.2
        L = LN[lid]
        if L.get("chapter") and s is not None:
            st = TL[lid]["start"] - 1.2
            if st <= t < st + 4.5:
                al = min(1, (t - st) / 0.4, (st + 4.5 - t) / 0.5)
                fr = comp(fr, layer("ch", L["chapter"]), al)
        if L.get("overlay") and t >= TL[lid]["start"]:
            fr = comp(fr, layer("ov", L["overlay"]))
        if s is not None:
            c = credit(s["img"])
            if c:
                fr = comp(fr, layer("cr", c))
        fr = fr * VIG
        if t < 1.0:
            fr *= t
        if t > TOTAL - 1.5:
            fr *= max(0, (TOTAL - t) / 1.5)
        out = np.clip(fr, 0, 255).astype(np.uint8)
        if PREVIEW:
            Image.fromarray(out).resize((640, 360)).save(f"pv_{n:02d}.jpg")
        else:
            ff.stdin.write(out.tobytes())
            if fi % (FPS * 30) == 0:
                print("frame", fi, "/", nfr, flush=True)
    if PREVIEW:
        ims = [Image.open(f"pv_{n:02d}.jpg") for n in range(len(frames))]
        cols = 4; rows = (len(ims) + cols - 1) // cols
        sh = Image.new("RGB", (640 * cols, 360 * rows))
        for i, im in enumerate(ims):
            sh.paste(im, ((i % cols) * 640, (i // cols) * 360))
        sh.save("preview.jpg"); print("preview.jpg"); sys.exit()
    ff.stdin.close(); ff.wait()

# ---------------- bed (long, slowly evolving; memory-light) ----------------
if not os.path.exists("bed.wav") or "--rebed" in sys.argv:
    SR = 44100; n = int(SR * TOTAL); rng = np.random.default_rng(5)
    t = (np.arange(n, dtype=np.float32) / SR)
    lp = lambda x, hi: sosfilt(butter(4, hi, btype="low", fs=SR, output="sos"), x).astype(np.float32)
    def add_note(buf, s0, a_, d_, fn):
        i0 = int(s0 * SR); L = int((a_ + d_) * SR)
        if i0 >= n: return
        L = min(L, n - i0); tt = np.arange(L, dtype=np.float32) / SR
        e = np.concatenate([np.linspace(0, 1, max(int(a_ * SR), 1), dtype=np.float32), np.exp(-np.linspace(0, 6, int(d_ * SR), dtype=np.float32))])[:L]
        buf[i0:i0 + L] += e * fn(tt, s0)
    lfo = (0.6 + 0.4 * np.sin(2 * np.pi * 0.045 * t)).astype(np.float32)
    ph = (2 * np.pi * np.cumsum(36.7 * (1 + 0.03 * np.sin(2 * np.pi * t / 140))) / SR).astype(np.float32)
    drone = (np.sin(ph) + 0.7 * np.sin(ph * 1.016) + 0.45 * np.sin(ph * 1.5) + 0.2 * np.sin(ph * 3 + np.sin(2 * np.pi * 0.15 * t))) * lfo
    del ph, lfo
    drone += 0.6 * lp(rng.standard_normal(n).astype(np.float32), 110); drone /= np.abs(drone).max()
    mb = np.zeros(n, np.float32); sets = [[440, 523.25, 659.25, 493.88, 415.3, 523.25, 440, 392], [392, 466.16, 587.33, 440, 369.99, 466.16, 392, 349.23]]
    i1 = next((x for x in ORDER if LN[x].get("shots")), ORDER[0])
    for kk, s0 in enumerate(np.arange(TL[i1]["start"], TOTAL - 6, 1.9)):
        if int(s0 // 45) % 3 == 2:
            continue
        f = sets[int(s0 // 90) % 2][kk % 8] * 0.985
        add_note(mb, s0, 0.003, 1.5, lambda tt, s0, f=f: np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt))
    mb /= np.abs(mb).max() + 1e-9
    hits = np.zeros(n, np.float32)
    for lid in [L["id"] for L in spec["lines"] if L.get("hit") or L.get("chapter")]:
        s0 = TL[lid]["start"] - (1.3 if LN[lid].get("chapter") else 0.15)
        add_note(hits, s0, 0.008, 2.6, lambda tt, s0: np.sin(2 * np.pi * np.cumsum(np.interp(tt, [0, 2.0], [85, 30])) / SR))
    hits /= np.abs(hits).max() + 1e-9
    bed = 0.26 * drone + 0.06 * mb + 0.45 * hits
    del drone, mb, hits
    bed *= np.clip(t / 1.5, 0, 1) * np.clip((TOTAL - t) / 2.5, 0, 1)
    bed = (bed / np.abs(bed).max() * 0.6).astype(np.float32)
    wavfile.write("bed.wav", SR, np.stack([bed, bed], 1))
    del bed, t

# ---------------- captions (lower third) ----------------
def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
ev = []
for lid in ORDER:
    L = TL[lid]; words = LN[lid]["text"].replace("...", "… ").split()
    wt = [len(re.sub(r"[^A-Za-z0-9]", "", say(w))) + 2 + (5 if w.endswith(("…", ".", ",", "?", "!")) else 0) for w in words]
    cum = np.concatenate([[0], np.cumsum(wt)]) / sum(wt) * (L["end"] - L["start"]) + L["start"]
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) == 5 or w.endswith(("…", ".", ",", "?", "!")):
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    cl = lambda s: s.replace("…", "").replace('"', "").upper()
    for ci, ch in enumerate(chunks):
        for kk, i in enumerate(ch):
            s0 = cum[i]; e = cum[ch[kk + 1]] if kk + 1 < len(ch) else (cum[i + 1] if ci + 1 < len(chunks) else L["end"] + 0.3)
            txt = " ".join(("{\\c&H00D6FF&}" + cl(words[j]) + "{\\c&HFFFFFF&}") if j == i else cl(words[j]) for j in ch)
            ev.append(f"Dialogue: 0,{ts(s0)},{ts(e)},Cap,,0,0,0,,{txt}")
open("captions.ass", "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,5,2,2,200,200,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

# ---------------- mix + two-pass encode under 95 MB ----------------
if not os.path.exists("mix.wav") or "--rebed" in sys.argv:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "voice.wav", "-i", "bed.wav", "-filter_complex",
                f"[0:a]aresample=44100,apad=whole_dur={TOTAL}[vo];[1:a]volume=0.5[bd];"
                "[vo][bd]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                "-map", "[a]", "-t", str(TOTAL), "-ar", "48000", "mix.wav"], check=True)
final = f"CreepyPartner_LF_{ID}.mp4"
vb = int((95e6 * 8 / TOTAL - 160000) / 1000)
vf = f"subtitles=captions.ass:fontsdir={FONTS}"
for ps in (1, 2):
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", "frames.mp4", "-i", "mix.wav", "-vf", vf, "-c:v", "libx264", "-preset", "medium",
           "-b:v", f"{vb}k", "-maxrate", f"{int(vb * 2)}k", "-bufsize", f"{int(vb * 4)}k", "-pix_fmt", "yuv420p", "-r", str(FPS),
           "-pass", str(ps), "-passlogfile", f"lfp_{ID}"]
    cmd += (["-an", "-f", "mp4", "/dev/null"] if ps == 1 else ["-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-movflags", "+faststart", final])
    subprocess.run(cmd, check=True)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final]))
cks = []
for i, tt in enumerate(np.linspace(2, dur - 3, 16)):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{tt:.2f}", "-i", final, "-frames:v", "1", "-vf", "scale=480:270", f"ck_{i:02d}.png"])
    cks.append(f"ck_{i:02d}.png")
sheet = Image.new("RGB", (480 * 4, 270 * 4))
for i, p in enumerate(cks):
    sheet.paste(Image.open(p), ((i % 4) * 480, (i // 4) * 270)); os.remove(p)
sheet.save("sheet.png")
print("done", final, round(dur, 1), "s", os.path.getsize(final) // 1_000_000, "MB")
