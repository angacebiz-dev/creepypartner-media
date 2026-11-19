"""THE TAPES format (9:16): evidence-board layout + VHS static + speaker-labelled subtitles over a dialogue track.
Usage: python3 tape.py <dir>/spec.json
spec: {id, header, fiction, cover:{img,title}, comment, total,
       center:{img | clips:[{file,ss,to}], cap1, cap2, credit},
       smalls:[{img,credit}] x4, audio: "<dialogue wav, relative to dir>",
       subs:[{t0,t1,spk,text,type?}], cards:[{t0,t1,text}], bed: 0..1}
"""
import json, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance, ImageFilter
from scipy.io import wavfile
from scipy.signal import butter, sosfilt

sys.path.insert(0, "/home/claude/partner")
from cover import make_cover

SPEC = os.path.abspath(sys.argv[1]); D = os.path.dirname(SPEC); os.chdir(D)
spec = json.load(open(SPEC))
WK = "/home/claude/partner/wk/"; FONTS = "/home/claude/partner/fonts"
W, H, FPS = 1080, 1920, 30
TOTAL = float(spec["total"]); ID = spec["id"]
F = lambda n, s: ImageFont.truetype(f"{FONTS}/{n}", s)
BG = (8, 12, 28)

def P(p):
    return p if os.path.isabs(p) else (WK + p if not os.path.exists(p) else p)

def framed(img, w, h, border=10, focus=0.5):
    im = ImageOps.fit(Image.open(P(img)).convert("RGB"), (w, h), centering=(0.5, focus))
    im = ImageEnhance.Color(im).enhance(0.75)
    out = Image.new("RGB", (w + 2 * border, h + 2 * border), (205, 205, 200)); out.paste(im, (border, border))
    return out

# ---------------- layout ----------------
lay = Image.new("RGB", (W, H), BG)
g = np.zeros((H, W, 3), np.float32)
yy, xx = np.mgrid[0:H, 0:W]
r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.42) / H) ** 2)
g[..., 0] = 26 - 30 * r; g[..., 1] = 34 - 34 * r; g[..., 2] = 70 - 60 * r
lay = Image.fromarray(np.clip(g, 0, 255).astype(np.uint8))
d = ImageDraw.Draw(lay)
SW, SH = 300, 300
pos = [(150, 190), (630, 190), (150, 1240), (630, 1240)]
for (x, y), s in zip(pos, spec["smalls"]):
    lay.paste(framed(s["img"], SW, SH, 6, s.get("focus", 0.5)), (x - 6, y - 6))
    if s.get("label"):
        fl = F("Anton-Regular.ttf", 26); lt = s["label"]; lw = d.textlength(lt, font=fl)
        d.rectangle((x, y + SH - 38, x + SW, y + SH), fill=(0, 0, 0))
        d.text((x + (SW - lw) / 2, y + SH - 37), lt, font=fl, fill=(235, 235, 235))
    if s.get("bar"):
        d.polygon([(x + 40, y + 200), (x + 70, y + 230), (x + 260, y + 80), (x + 230, y + 50)], fill=(0, 0, 0))
CX, CY, CW, CH = 205, 540, 670, 560
c = spec["center"]
d.rectangle((CX - 16, CY - 16, CX + CW + 16, CY + CH + 150), fill=(208, 208, 203))
if c.get("img"):
    lay.paste(ImageOps.fit(Image.open(P(c["img"])).convert("RGB"), (CW, CH), centering=(0.5, c.get("focus", 0.5))), (CX, CY))
else:
    d.rectangle((CX, CY, CX + CW, CY + CH), fill=(0, 0, 0))
for k, t in enumerate([c.get("cap1", ""), c.get("cap2", "")]):
    sz = 38
    while d.textlength(t, font=F("SpecialElite.ttf", sz)) > CW - 10 and sz > 22: sz -= 2
    fe = F("SpecialElite.ttf", sz)
    d.text(((W - d.textlength(t, font=fe)) / 2, CY + CH + 30 + 50 * k), t, font=fe, fill=(70, 70, 75))
# header
fa = F("Anton-Regular.ttf", 54)
hd = spec.get("header", "THE TAPES")
d.text(((W - d.textlength(hd, font=fa)) / 2, 70), hd, font=fa, fill=(230, 230, 235))
tag = spec.get("tag") or ("FICTION  ·  A CREEPY PARTNER ORIGINAL" if spec.get("fiction") else None)
if tag:
    f2 = F("Anton-Regular.ttf", 32); col = tuple(spec.get("tag_color", [170, 20, 20]))
    tw = d.textlength(tag, font=f2); d.rectangle(((W - tw) / 2 - 16, 138, (W + tw) / 2 + 16, 178), fill=col)
    d.text(((W - tw) / 2, 139), tag, font=f2, fill=(255, 255, 255))
# credits
cr = "  ·  ".join(x for x in [c.get("credit")] + [s.get("credit") for s in spec["smalls"]] if x)
fc = F("SpecialElite.ttf", 21)
words, lines, cur = cr.split("  ·  "), [], ""
for wds in words:
    t = (cur + "  ·  " + wds) if cur else wds
    if d.textlength(t, font=fc) > 980: lines.append(cur); cur = wds
    else: cur = t
lines.append(cur)
for k, t in enumerate(lines[:3]):
    d.text(((W - d.textlength(t, font=fc)) / 2, 1838 + 26 * k), t, font=fc, fill=(120, 125, 150))
lay.save("layout.png")
if os.environ.get("LAYOUT_ONLY"): sys.exit(0)

# ---------------- VHS overlay (alpha loop) ----------------
if not os.path.exists("vhs.mov"):
    os.makedirs("vhs", exist_ok=True); rnd = random.Random(7)
    scan = np.zeros((H, W, 4), np.uint8); scan[::4, :, 3] = 26
    for i in range(90):
        a = scan.copy()
        for _ in range(rnd.choice([0, 1, 1, 2, 3])):
            y = rnd.randrange(0, H); h = rnd.choice([2, 2, 3, 5]); x0 = rnd.randrange(0, W // 2); x1 = rnd.randrange(W // 2, W)
            a[y:y + h, x0:x1, :3] = (190, 200, 235); a[y:y + h, x0:x1, 3] = rnd.randrange(60, 150)
        if rnd.random() < 0.18:
            y = rnd.randrange(0, H - 140); h = rnd.randrange(30, 140)
            a[y:y + h, :, :3] = (150, 160, 210); a[y:y + h, :, 3] = np.maximum(a[y:y + h, :, 3], rnd.randrange(18, 40))
        Image.fromarray(a, "RGBA").save(f"vhs/{i:03d}.png")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", "15", "-i", "vhs/%03d.png", "-c:v", "qtrle", "vhs.mov"], check=True)

# ---------------- center clip ----------------
inputs = ["-loop", "1", "-framerate", str(FPS), "-t", str(TOTAL), "-i", "layout.png"]
fc_parts = []
if c.get("clips"):
    lst = []
    for k, cl in enumerate(c["clips"]):
        out = f"cl{k}.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(cl["ss"]), "-to", str(cl["to"]), "-i", P(cl["file"]), "-an",
                        "-vf", f"scale={CW}:{CH}:force_original_aspect_ratio=increase,crop={CW}:{CH},fps={FPS},format=yuv420p",
                        "-c:v", "libx264", "-crf", "18", out], check=True)
        lst.append(f"file {out}")
    open("clips.txt", "w").write("\n".join(lst) + "\n")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "clips.txt", "-c", "copy", "center.mp4"], check=True)
    inputs += ["-i", "center.mp4"]
    fc_parts.append(f"[1:v]tpad=stop_mode=clone:stop_duration={TOTAL}[cv];[0:v][cv]overlay={CX}:{CY}:shortest=0[b0]")
    vin = 2
else:
    fc_parts.append("[0:v]null[b0]"); vin = 1
inputs += ["-stream_loop", "-1", "-i", "vhs.mov"]

# ---------------- subtitles (ASS) ----------------
def ts(x):
    x = max(0, x); return f"{int(x // 3600)}:{int(x % 3600 // 60):02d}:{x % 60:05.2f}"
ass = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
       "[V4+ Styles]",
       "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
       "Style: S,Special Elite,50,&H00FFFFFF,&H00FFFFFF,&H00000000,&H90000000,0,0,0,0,100,100,0,0,1,3,1,8,80,80,1565,1",
       "Style: C,Anton,74,&H00FFFFFF,&H00FFFFFF,&H00000000,&HC0000000,0,0,0,0,100,100,1,0,3,18,0,5,90,90,0,1",
       "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
for s in spec["subs"]:
    lab = f"{{\\c&H66D9FF&}}{s['spk']}:{{\\c&HFFFFFF&}} " if s.get("spk") else ""
    txt = s["text"]
    if s.get("type"):
        n = len(txt); step = max(1, n // 40); tt = s["t0"]
        for k in range(step, n + step, step):
            t2 = tt + 0.035 * step
            ass.append(f"Dialogue: 0,{ts(tt)},{ts(min(t2, s['t1']) if k < n else s['t1'])},S,,0,0,0,,{lab}{txt[:k]}")
            tt = t2
    else:
        ass.append(f"Dialogue: 0,{ts(s['t0'])},{ts(s['t1'])},S,,0,0,0,,{lab}{txt}")
for cd in spec.get("cards", []):
    ass.append(f"Dialogue: 1,{ts(cd['t0'])},{ts(cd['t1'])},C,,0,0,0,,{{\\pos(540,820)\\fad(250,250)}}{cd['text']}")
open("subs.ass", "w").write("\n".join(ass) + "\n")

# ---------------- bed ----------------
SR = 44100; n = int(SR * TOTAL); t = np.arange(n) / SR; rng = np.random.default_rng(5)
lp = lambda x, f: sosfilt(butter(4, f, btype="low", fs=SR, output="sos"), x)
bp = lambda x, a, b: sosfilt(butter(2, [a, b], btype="band", fs=SR, output="sos"), x)
drone = (np.sin(2 * np.pi * 41.2 * t) + 0.6 * np.sin(2 * np.pi * 41.9 * t) + 0.3 * np.sin(2 * np.pi * 82.4 * t)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.07 * t))
drone += 0.5 * lp(rng.standard_normal(n), 120); drone /= np.abs(drone).max()
hiss = bp(rng.standard_normal(n), 900, 6000); hiss /= np.abs(hiss).max()
bed = float(spec.get("bed", 0.5)) * (0.32 * drone + 0.05 * hiss)
bed *= np.clip(t / 0.6, 0, 1) * np.clip((TOTAL - t) / 1.2, 0, 1)
wavfile.write("bed.wav", SR, np.stack([bed, bed], 1).astype(np.float32))

# ---------------- render story ----------------
fc_parts.append(f"[{vin}:v]format=rgba[vh];[b0][vh]overlay=0:0:shortest=0,"
                "noise=alls=4:allf=t,eq=brightness='0.025*sin(t*17)*sin(t*3.1)':eval=frame,"
                f"subtitles=subs.ass:fontsdir={FONTS},format=yuv420p[v]")
aud = spec.get("audio")
if aud:
    inputs += ["-i", aud, "-i", "bed.wav"]
    ai = vin + 1
    fc_parts.append(f"[{ai}:a]aresample=44100,apad=whole_dur={TOTAL}[da];[{ai + 1}:a]volume=1.0[bd];"
                    "[da][bd]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]")
else:
    inputs += ["-i", "bed.wav"]
    fc_parts.append(f"[{vin + 1}:a]loudnorm=I=-16:TP=-1.5[a]")
enc = ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "9M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
subprocess.run(["ffmpeg", "-y", "-loglevel", "error"] + inputs + ["-filter_complex", ";".join(fc_parts), "-map", "[v]", "-map", "[a]",
                "-t", str(TOTAL)] + [x if x != "medium" else "veryfast" for x in enc] + ["story.mp4"], check=True)

# ---------------- cover + endcard + concat ----------------
cv = spec["cover"]
make_cover(P(cv["img"]), cv["title"], "cover.jpg", sub="THE TAPES", focus_y=cv.get("focus_y", 0.45))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-t", "0.5", "-i", "cover.jpg", "-f", "lavfi", "-t", "0.5",
                "-i", "anullsrc=r=48000:cl=stereo", "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-c:v", "libx264", "-b:v", "6M",
                "-c:a", "aac", "-b:a", "192k", "-shortest", "cov.mp4"], check=True)
subprocess.run(["python3", "/home/claude/partner/endcard.py", spec["comment"], "endcard.mp4"], check=True)
open("cat.txt", "w").write("file cov.mp4\nfile story.mp4\nfile endcard.mp4\n")
final = f"CreepyPartner_{ID}.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "cat.txt"] + enc + ["-movflags", "+faststart", final], check=True)
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", final]))
for k, tt in enumerate([2, dur * 0.25, dur * 0.5, dur * 0.75, dur - 4, dur - 1.5]):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{tt:.2f}", "-i", final, "-frames:v", "1", "-vf", "scale=270:480", f"sh{k}.png"], check=True)
ims = [Image.open(f"sh{k}.png") for k in range(6)]
sheet = Image.new("RGB", (270 * 6, 480)); [sheet.paste(im, (270 * k, 0)) for k, im in enumerate(ims)]
sheet.save("sheet.png"); print("done", final, f"{dur:.1f}s")
