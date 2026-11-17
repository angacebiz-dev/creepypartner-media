"""Partner Files documentary short builder.
Usage: python3 doc.py spec.json   (run from the spec's folder; image paths relative to /home/claude/partner/wk)
spec: {id, title_top, cover:{img,title,focus_y}, comment, lines:[{id,text,pause?,shots:[{img|clip,mode,tint,focus,ss}],overlay?,hit?}]}
Lines with no shots show the talking Partner (use for hook + end)."""
import json, math, os, re, subprocess, sys
import numpy as np, soundfile as sf
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageEnhance
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "/home/claude/partner/video02"); sys.path.insert(0, "/home/claude/partner")
from tts import creepy
from kokoro_onnx import Kokoro
from cover import make_cover

WK = "/home/claude/partner/wk/"; FONTS = "/home/claude/partner/fonts/"
W, H, FPS = 1080, 1920, 30
spec = json.load(open(sys.argv[1])); OUT = os.path.dirname(os.path.abspath(sys.argv[1])); os.chdir(OUT)
ID = spec["id"]

# ---------------- voice ----------------
if not os.path.exists("voice.wav") or "--revoice" in sys.argv:
    k = Kokoro('/home/claude/tts/kokoro-v1.0.onnx', '/home/claude/tts/voices-v1.0.bin')
    SR = 44100; t = 0.5; audio = [np.zeros(int(SR * 0.5))]; tl = []
    for L in spec["lines"]:
        s, sr = k.create(L["text"], voice="bm_lewis", speed=spec.get("speed", 0.86), lang="en-us")
        sf.write("tmp.wav", s, sr); creepy("tmp.wav", f"seg_{L['id']}.wav", semis=-2.5)
        a, _ = sf.read(f"seg_{L['id']}.wav"); a = a.mean(1) if a.ndim > 1 else a
        nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(nz[0] - 400, 0): nz[-1] + 1500]
        d = len(a) / SR; tl.append({"id": L["id"], "start": round(t, 3), "end": round(t + d, 3)})
        p = L.get("pause", 0.35); audio += [a, np.zeros(int(SR * p))]; t += d + p
    sf.write("voice.wav", np.concatenate(audio), SR); json.dump(tl, open("timeline.json", "w"), indent=1)
TL = {x["id"]: x for x in json.load(open("timeline.json"))}
LN = {L["id"]: L for L in spec["lines"]}
ORDER = [L["id"] for L in spec["lines"]]
TOTAL = TL[ORDER[-1]]["end"] + 1.2
print("voice", round(TOTAL, 1), "s")

# ---------------- shots ----------------
SH = []  # (t0, t1, shot or None)
for i, lid in enumerate(ORDER):
    t0 = 0 if i == 0 else TL[lid]["start"] - 0.15
    t1 = TL[ORDER[i + 1]]["start"] - 0.15 if i + 1 < len(ORDER) else TOTAL
    shots = LN[lid].get("shots") or [None]
    n = len(shots)
    for j, s in enumerate(shots):
        SH.append((t0 + (t1 - t0) * j / n, t0 + (t1 - t0) * (j + 1) / n, s, lid))

CREDITS = {}
def credit(path):
    d = os.path.dirname(WK + path); cf = d + "/credits.json"
    if cf not in CREDITS:
        CREDITS[cf] = json.load(open(cf)) if os.path.exists(cf) else {}
    m = CREDITS[cf].get(os.path.basename(path))
    if not m:
        return None
    who = re.sub(r"\s+", " ", m.get("artist") or "Unknown")
    who = who.replace("Unknown authorUnknown author", "Unknown").split(" from ")[0][:40]
    lic = m.get("license") or "?"
    return f"{'Photo' if not path.endswith(('.webm','.ogv','.mp4')) else 'Video'}: {who} / {lic} / Wikimedia Commons"

IMG = {}
def load(path, tint):
    key = (path, tint)
    if key in IMG:
        return IMG[key]
    im = Image.open(WK + path).convert("RGB")
    ex = 1.2; tw, th = int(W * ex), int(H * ex)
    if im.width / im.height > 0.8:
        bg = ImageOps.fit(im, (tw, th)).filter(ImageFilter.GaussianBlur(30)); bg = ImageEnhance.Brightness(bg).enhance(0.35)
        fw = tw; fg = im.resize((fw, int(im.height * fw / im.width)), Image.LANCZOS)
        if fg.height > th * 0.62:
            s = th * 0.62 / im.height; fg = im.resize((int(im.width * s), int(th * 0.62)), Image.LANCZOS)
        bg.paste(fg, ((tw - fg.width) // 2, int(th * 0.44 - fg.height / 2)))
        a = np.asarray(bg).astype(np.float32)
    else:
        a = np.asarray(ImageOps.fit(im, (tw, th), Image.LANCZOS)).astype(np.float32)
    if tint == "night":
        a = a * np.array([0.42, 0.46, 0.66], np.float32)
    elif tint == "grey":
        a = np.repeat(a.mean(2, keepdims=True), 3, 2) * 0.85
    elif tint == "dark":
        a = a * 0.6
    a = a * 1.08 - 8  # contrast
    IMG[key] = a
    return a

def still(s, t0, t1, t):
    a = load(s["img"], s.get("tint")); ah, aw = a.shape[:2]
    p = (t - t0) / max(t1 - t0, 0.01); mode = s.get("mode", "in")
    fy = s.get("focus", 0.5)
    if mode == "in":
        z = 1.0 + 0.12 * p; cy = ah * fy
    elif mode == "out":
        z = 1.12 - 0.12 * p; cy = ah * fy
    elif mode == "face":
        z = 1.5 + 0.2 * p; cy = ah * fy
    elif mode == "up":
        z = 1.0; cy = ah / 2 + (ah - ah / 1.2) / 2 * (1 - 2 * p)
    else:
        z = 1.0; cy = ah / 2 - (ah - ah / 1.2) / 2 * (1 - 2 * p)
    cw, ch = aw / 1.2 / z, ah / 1.2 / z
    x0 = int(np.clip(aw / 2 - cw / 2, 0, aw - cw)); y0 = int(np.clip(cy - ch / 2, 0, ah - ch))
    crop = a[y0:y0 + int(ch), x0:x0 + int(cw)]
    return np.asarray(Image.fromarray(np.clip(crop, 0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32)

CLIPS = {}
def clipframe(s, t0, t):
    path = WK + s["clip"]
    if path not in CLIPS:
        tmp = f"clip_{len(CLIPS)}.raw"; ss = s.get("ss", 0); dur = s.get("dur", 30)
        vf = (f"fps={FPS},scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(ss), "-t", str(dur), "-i", path, "-vf", vf,
                        "-f", "rawvideo", "-pix_fmt", "rgb24", tmp], check=True)
        CLIPS[path] = np.memmap(tmp, dtype=np.uint8, mode="r").reshape(-1, H, W, 3)
    fr = CLIPS[path]; i = min(int((t - t0) * FPS), len(fr) - 1)
    return fr[i].astype(np.float32)

# talking Partner
base = Image.open("/home/claude/partner/THE_PARTNER_vertical_1080x1920.png").convert("RGB")
OX, OY = 250, 500
CURVE = [(OX + x, OY + y) for x, y in [(120, 390), (200, 409), (310, 393), (410, 343), (487, 262)]]
jaw_poly = CURVE + [(OX + 600, OY + 330), (OX + 560, OY + 640), (OX + 60, OY + 640), (OX + 60, OY + 420)]
jm = Image.new("L", (W, H), 0); ImageDraw.Draw(jm).polygon(jaw_poly, fill=255); jm = jm.filter(ImageFilter.GaussianBlur(5))
jaw = base.copy(); jaw.putalpha(jm)
va, VSR = sf.read("voice.wav"); va = va.mean(1) if va.ndim > 1 else va
hop = VSR // FPS
ENV = np.array([np.sqrt(np.mean(va[i * hop:(i + 1) * hop] ** 2)) for i in range(len(va) // hop)])
ENV = ENV / (np.percentile(ENV, 97) + 1e-9)
OPEN = np.zeros(len(ENV))
for i in range(len(ENV)):
    OPEN[i] = (OPEN[i - 1] if i else 0) * 0.45 + np.clip(ENV[i], 0, 1) * 0.55

def partner(fi, t, t0, t1):
    d = 30 * OPEN[min(fi, len(OPEN) - 1)]
    fr = base.copy()
    gap = CURVE + [(x + 0.3 * d, y + d) for x, y in reversed(CURVE)]
    g = Image.new("L", (W, H), 0); ImageDraw.Draw(g).polygon(gap, fill=255); g = g.filter(ImageFilter.GaussianBlur(3))
    fr.paste((22, 10, 10), (0, 0), g); fr.paste(jaw, (int(0.3 * d), int(d)), jaw)
    p = (t - t0) / max(t1 - t0, 0.01); z = 1.0 + 0.07 * p; bob = 4 * math.sin(t * 1.7)
    cw, ch = int(W / z), int(H / z); x0 = (W - cw) // 2; y0 = int((H - ch) * 0.35 + bob)
    fr = fr.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BICUBIC)
    return np.asarray(fr).astype(np.float32) * (0.93 + 0.07 * (math.sin(t * 31) > 0.7))

fA = ImageFont.truetype(FONTS + "Anton-Regular.ttf", 86)
fC = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 26)
LAY = {}
def overlay(txt):
    if txt not in LAY:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for i, ln in enumerate(txt.split("\n")):
            tw = d.textlength(ln, font=fA)
            d.text(((W - tw) / 2, 300 + i * 100), ln, font=fA, fill=(255, 40, 40), stroke_width=6, stroke_fill=(0, 0, 0))
        LAY[txt] = np.asarray(im).astype(np.float32)
    return LAY[txt]
def credlayer(txt):
    k = "cr" + txt
    if k not in LAY:
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((36, H - 70), txt, font=fC, fill=(235, 235, 235, 210), stroke_width=2, stroke_fill=(0, 0, 0, 210))
        LAY[k] = np.asarray(im).astype(np.float32)
    return LAY[k]
def comp(fr, L):
    a = L[..., 3:4] / 255.0
    return fr * (1 - a) + L[..., :3] * a

rng = np.random.default_rng(9)
GR = [rng.normal(0, 6, (H, W, 1)).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1.05 - 0.5 * (((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2) * 2.2)[..., None]

if not os.path.exists("frames.mp4") or "--rerender" in sys.argv:
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt",
                           "yuv420p", "frames.mp4"], stdin=subprocess.PIPE)
    for fi in range(int(TOTAL * FPS)):
        t = fi / FPS
        t0, t1, s, lid = next((x for x in SH if x[0] <= t < x[1]), SH[-1])
        if s is None:
            fr = partner(fi, t, t0, t1)
        elif "clip" in s:
            fr = clipframe(s, t0, t)
        else:
            fr = still(s, t0, t1, t)
        if t - t0 < 0.07 and t0 > 0.1:
            fr = fr * 0.4
        ov = LN[lid].get("overlay")
        if ov and t >= TL[lid]["start"]:
            fr = comp(fr, overlay(ov))
        if s is not None:
            c = credit(s.get("img") or s.get("clip"))
            if c:
                fr = comp(fr, credlayer(c))
        fr = (fr + GR[fi % 6]) * VIG
        ff.stdin.write(np.clip(fr, 0, 255).astype(np.uint8).tobytes())
    ff.stdin.close(); ff.wait()
    for p in os.listdir("."):
        if p.startswith("clip_") and p.endswith(".raw"):
            os.remove(p)

# ---------------- bed ----------------
SR = 44100; n = int(SR * TOTAL); t = np.arange(n) / SR; rng = np.random.default_rng(3)
lp = lambda x, hi: sosfilt(butter(4, hi, btype="low", fs=SR, output="sos"), x)
def env_at(s, a, d):
    e = np.zeros(n); i0 = int(s * SR); seg = np.concatenate([np.linspace(0, 1, max(int(a * SR), 1)), np.exp(-np.linspace(0, 6, int(d * SR)))])
    if i0 < n: e[i0:i0 + len(seg)] = seg[:n - i0]
    return e
lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.06 * t)
drone = (np.sin(2 * np.pi * 36.7 * t) + 0.7 * np.sin(2 * np.pi * 37.3 * t) + 0.45 * np.sin(2 * np.pi * 55 * t) + 0.2 * np.sin(2 * np.pi * 110 * t + np.sin(2 * np.pi * 0.15 * t))) * lfo
drone += 0.6 * lp(rng.standard_normal(n), 110); drone /= np.abs(drone).max()
mb = np.zeros(n); notes = [440, 523.25, 659.25, 493.88, 415.3, 523.25, 440, 392]
i1 = ORDER[1] if len(ORDER) > 1 else ORDER[0]
for kk, s in enumerate(np.arange(TL[i1]["start"], TOTAL - 4, 1.6)):
    f = notes[kk % len(notes)] * 0.985
    mb += env_at(s, 0.003, 1.3) * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t))
mb /= np.abs(mb).max() + 1e-9
hits = np.zeros(n)
for lid in [L["id"] for L in spec["lines"] if L.get("hit")]:
    s = TL[lid]["start"] - 0.15; e = env_at(s, 0.008, 2.4)
    hits += e * np.sin(2 * np.pi * np.cumsum(np.interp(t, [s, s + 2.0], [85, 30])) / SR)
hits /= np.abs(hits).max() + 1e-9
bed = 0.24 * drone + 0.07 * mb + 0.5 * hits
bed *= np.clip(t / 0.8, 0, 1) * np.clip((TOTAL - t) / 1.5, 0, 1)
bed = bed / np.abs(bed).max() * 0.6
wavfile.write("bed.wav", SR, np.stack([bed, bed], 1).astype(np.float32))

# ---------------- captions ----------------
def ts(x):
    return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
ev = []
for lid in ORDER:
    L = TL[lid]; words = LN[lid]["text"].replace("...", "… ").split()
    wt = [len(re.sub(r"[^A-Za-z0-9]", "", w)) + 2 + (5 if w.endswith(("…", ".", ",", "?", "!")) else 0) for w in words]
    cum = np.concatenate([[0], np.cumsum(wt)]) / sum(wt) * (L["end"] - L["start"]) + L["start"]
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if len(cur) == 3 or w.endswith(("…", ".", ",", "?", "!")):
            chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    cl = lambda s: s.replace("…", "").replace('"', "").upper()
    for ci, ch in enumerate(chunks):
        for kk, i in enumerate(ch):
            s = cum[i]; e = cum[ch[kk + 1]] if kk + 1 < len(ch) else (cum[i + 1] if ci + 1 < len(chunks) else L["end"] + 0.3)
            txt = " ".join(("{\\c&H00D6FF&}" + cl(words[j]) + "{\\c&HFFFFFF&}") if j == i else cl(words[j]) for j in ch)
            ev.append(f"Dialogue: 0,{ts(s)},{ts(e)},Cap,,0,0,0,,{txt}")
top = spec["title_top"].upper()
ev.append(f"Dialogue: 1,{ts(0)},{ts(TL[ORDER[0]]['end'])},Top,,0,0,0,,{{\\fad(0,300)}}PARTNER FILES\\N{{\\c&H00D6FF&}}{top}")
open("captions.ass", "w").write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Anton,100,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,7,3,2,80,80,520,1
Style: Top,Anton,112,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,0,0,0,0,100,100,1,0,1,7,3,8,70,70,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""" + "\n".join(ev) + "\n")

enc = ["-c:v", "libx264", "-preset", "medium", "-b:v", "6M", "-maxrate", "8M", "-bufsize", "16M", "-pix_fmt", "yuv420p",
       "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "frames.mp4", "-i", "voice.wav", "-i", "bed.wav", "-filter_complex",
                f"[0:v]subtitles=captions.ass:fontsdir={FONTS}[v];[1:a]aresample=44100,apad=whole_dur={TOTAL}[vo];[2:a]volume=0.55[bd];"
                "[vo][bd]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]",
                "-map", "[v]", "-map", "[a]", "-t", str(TOTAL)] + enc + ["story.mp4"], check=True)

# cover + endcard
c = spec["cover"]
make_cover(WK + c["img"], c["title"], "cover.jpg", sub="PARTNER FILES", focus_y=c.get("focus_y", 0.45))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-t", "0.5", "-i", "cover.jpg", "-f", "lavfi", "-t", "0.5",
                "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-c:v", "libx264", "-b:v", "6M",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "cov.mp4"], check=True)
subprocess.run(["python3", "/home/claude/partner/endcard.py", spec["comment"], "endcard.mp4"], check=True)
open("cat.txt", "w").write("file cov.mp4\nfile story.mp4\nfile endcard.mp4\n")
final = f"CreepyPartner_{ID}.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "cat.txt"] + enc + ["-movflags", "+faststart", final], check=True)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final]))
vb = int((2_780_000 * 8 / dur - 64000) / 1000)
vf = "hqdn3d=6:5:8:8,scale=720:1280:flags=lanczos"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vb}k",
                "-pass", "1", "-passlogfile", f"p_{ID}", "-an", "-f", "mp4", "/dev/null"], check=True)
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", final, "-vf", vf, "-c:v", "libx264", "-preset", "slow", "-b:v", f"{vb}k",
                "-maxrate", f"{int(vb * 1.4)}k", "-bufsize", f"{int(vb * 2.8)}k", "-pass", "2", "-passlogfile", f"p_{ID}",
                "-c:a", "aac", "-b:a", "64k", "-ar", "48000", "-movflags", "+faststart", f"light_{ID}.mp4"], check=True)
for tt in [0.2, 2.5, dur * 0.3, dur * 0.5, dur * 0.7, dur * 0.88, dur - 1.5]:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(tt), "-i", final, "-frames:v", "1", "-vf", "scale=270:480", f"ck_{tt:.1f}.png"])
cks = sorted([p for p in os.listdir(".") if p.startswith("ck_")], key=lambda p: float(p[3:-4]))
sheet = Image.new("RGB", (270 * len(cks), 480))
for i, p in enumerate(cks):
    sheet.paste(Image.open(p), (i * 270, 0)); os.remove(p)
sheet.save("sheet.png")
print("DONE", final, round(dur, 1), "s", os.path.getsize(final), "light", os.path.getsize(f"light_{ID}.mp4"))
