"""Assemble THE TAPES dialogue tracks from ElevenLabs lines + synthesized SFX.
python3 mix.py <LETTER>   -> <LETTER>_dialogue.wav + <LETTER>_subs.json
"""
import json, sys, subprocess
import numpy as np
from scipy.signal import butter, sosfilt

SR = 44100
rng = np.random.default_rng(3)
S = json.load(open('scripts.json'))


def load(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                         capture_output=True).stdout
    a = np.frombuffer(raw, np.float32).astype(np.float64)
    nz = np.where(np.abs(a) > 0.01)[0]
    return a[max(0, nz[0] - 300): nz[-1] + 1500] if len(nz) else a


def band(x, lo, hi, o=4):
    return sosfilt(butter(o, [lo, hi], btype='band', fs=SR, output='sos'), x)


def lp(x, f, o=4):
    return sosfilt(butter(o, f, btype='low', fs=SR, output='sos'), x)


def norm(x, peak=0.8):
    m = np.abs(x).max()
    return x * (peak / m) if m > 0 else x


def phone(x, drive=2.0):
    return norm(np.tanh(band(x, 300, 3400) * drive), 0.8)


def radio(x):
    y = np.tanh(band(x, 450, 2800) * 3.5)
    return norm(y, 0.75)


def room(x):
    y = lp(x, 6500)
    rev = np.zeros_like(y)
    for d, g in [(0.031, 0.25), (0.053, 0.18), (0.089, 0.12)]:
        k = int(d * SR); rev[k:] += y[:-k] * g
    return norm(y + rev, 0.8)


def muffled(x):  # through a door
    return norm(lp(x, 900) * 1.0, 0.45)


def monitor(x):  # baby monitor speaker
    y = np.tanh(band(x, 600, 2600) * 4)
    y += 0.04 * band(rng.standard_normal(len(y)), 1000, 5000)
    return norm(y, 0.55)


# ---- sfx ----
def noise(n, lo, hi, amp):
    return band(rng.standard_normal(n), lo, hi, 2) * amp


def squelch(dur=0.22):
    n = int(dur * SR); return noise(n, 500, 4500, 0.25) * np.linspace(1, 0.3, n)


def click():
    n = int(0.015 * SR); return noise(n, 1500, 6000, 0.6) * np.exp(-np.arange(n) / (0.002 * SR))


def thud(amp=0.5):
    n = int(0.25 * SR); t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 60 * t) + 0.6 * noise(n, 80, 600, 1)) * np.exp(-t / 0.05) * amp


def footsteps(k=6, gap=0.55, amp=0.35):
    out = np.zeros(int((k * gap + 0.4) * SR))
    for j in range(k):
        s = thud(amp * (0.6 + 0.4 * j / k)); i = int(j * gap * SR); out[i:i + len(s)] += s
    return out


def rattle(dur=1.2):
    n = int(dur * SR); out = np.zeros(n)
    for j in range(int(dur * 14)):
        i = int(rng.uniform(0, dur - 0.05) * SR); c = noise(int(0.03 * SR), 800, 5000, 0.5) * np.hanning(int(0.03 * SR))
        out[i:i + len(c)] += c
    return out


def bang():
    n = int(0.6 * SR); t = np.arange(n) / SR
    return (noise(n, 60, 3000, 0.9) + 0.5 * np.sin(2 * np.pi * 45 * t)) * np.exp(-t / 0.09)


def hangup():
    out = np.zeros(int(2.2 * SR)); out[:400] += 0.7 * np.hanning(400)
    t = np.arange(int(0.27 * SR)) / SR
    for q, f in enumerate([913.8, 1370.6, 1776.7]):
        i = int((0.5 + q * 0.3) * SR); out[i:i + len(t)] += 0.15 * np.sin(2 * np.pi * f * t)
    return out


def vm_beep():
    t = np.arange(int(0.35 * SR)) / SR; return 0.22 * np.sin(2 * np.pi * 1000 * t)


def static_burst(dur=1.5, amp=0.5):
    n = int(dur * SR); return noise(n, 300, 6000, amp) * np.minimum(1, np.linspace(3, 0, n))


def glass_knock():
    out = np.zeros(int(1.0 * SR))
    for j in range(3):
        k = noise(int(0.04 * SR), 1500, 7000, 0.5) * np.exp(-np.arange(int(0.04 * SR)) / (0.006 * SR)); i = int(j * 0.28 * SR)
        out[i:i + len(k)] += k
    return out


# ---- per-video plans: (line_no, fx, gap_before, extra_sfx_after) ----
FX = {
 'A': dict(fx={'*': radio}, gaps={13: 1.4, 15: 0.6, 17: 1.2}, radio=True, after={}),
 'B': dict(fx={'DISPATCH': lambda x: phone(x, 1.4), 'CALLER': phone, 'UNKNOWN': lambda x: muffled(phone(x))},
           gaps={11: 4.4, 12: 0.8, 14: 0.4}, after={10: ('steps', footsteps(6, 0.55, 1.1)), 13: ('rattle', rattle(1.4)), 14: ('end', None)}),
 'C': dict(fx={'DISPATCH': lambda x: phone(x, 1.4), 'CALLER': phone, 'MONITOR': lambda x: phone(monitor(x), 1.2)},
           gaps={9: 1.6, 12: 1.4}, after={8: ('mon', noise(int(1.2 * SR), 800, 5000, 0.05)), 13: ('end', None)}),
 'D': dict(fx={'VOICEMAIL': lambda x: norm(band(x, 250, 5000), 0.7), 'MEGAN': phone, 'UNKNOWN': lambda x: phone(x, 1.2)},
           gaps={}, vm=True, after={8: ('knock', glass_knock())}),
 'E': dict(fx={'*': radio}, gaps={3: 1.6, 8: 1.0, 11: 0.4, 12: 1.6}, radio=True, after={11: ('burst', static_burst(1.6, 0.25))}),
 'F': dict(fx={'*': radio}, gaps={9: 1.0, 10: 1.2, 11: 1.4}, radio=True, after={10: ('burst', static_burst(1.4, 0.28))}),
 'G': dict(fx={'*': room}, gaps={4: 1.0, 6: 0.9, 8: 1.0, 10: 1.6}, after={}),
}


def build(L):
    spec = S[L]; P = FX[L]; lines = spec['lines']
    t = 0.4; segs = []; subs = []
    for i, (spk, txt) in enumerate(lines, 1):
        a = load(f'{L}/{i:02d}.mp3')
        f = P['fx'].get(spk) or P['fx'].get('*')
        y = f(a)
        tgt = 0.07 if (L == 'B' and spk == 'UNKNOWN') else (0.09 if spk in ('VOICEMAIL',) else 0.13)
        y = y * (tgt / max(1e-6, np.sqrt(np.mean(y[np.abs(y) > 0.02] ** 2)) if np.any(np.abs(y) > 0.02) else 1))
        y = np.tanh(y * 1.3) / 1.3
        gap = P['gaps'].get(i, 0.35)
        if P.get('vm') and spk == 'VOICEMAIL':
            gap = 0.9 if i > 1 else 0.3
        t += gap
        if P.get('radio'):
            segs.append((t - 0.05, click()))
        segs.append((t, y)); d = len(y) / SR
        clean = txt.split('] ', 1)[-1] if txt.startswith('[') else txt
        subs.append({'t0': round(t, 2), 't1': round(t + d + 0.15, 2), 'spk': spk, 'text': clean})
        t += d
        if P.get('radio'):
            segs.append((t, squelch())); t += 0.15
        if P.get('vm') and spk == 'VOICEMAIL':
            segs.append((t + 0.2, vm_beep())); t += 0.6
        ex = P['after'].get(i)
        if ex and ex[1] is not None:
            segs.append((t + 0.2, ex[1])); t += 0.2 + len(ex[1]) / SR * (0.85 if ex[0] in ('steps', 'mon') else 1.0)
    end = t
    if L in ('B', 'C'):
        segs.append((t + 0.3, bang() if L == 'B' else noise(int(0.5 * SR), 500, 6000, 0.4)))
        segs.append((t + 0.9, hangup())); end = t + 3.2
    elif L == 'D':
        segs.append((t + 0.6, vm_beep())); segs.append((t + 1.4, vm_beep() * 0.0)); end = t + 2.0
    elif L == 'G':
        segs.append((t + 0.8, click())); end = t + 1.4
    else:
        end = t + 1.0
    n = int((end + 0.5) * SR); mix = np.zeros(n)
    for t0, y in segs:
        i = int(t0 * SR); j = min(n, i + len(y)); mix[i:j] += y[:j - i]
    # line bed: phone hiss / radio static / tape hiss
    bed = {'A': noise(n, 400, 3000, 0.035), 'E': noise(n, 400, 3000, 0.03), 'F': noise(n, 300, 3500, 0.05),
           'G': noise(n, 2000, 9000, 0.012)}.get(L, noise(n, 300, 3400, 0.015))
    bed *= np.clip(np.arange(n) / SR / 0.4, 0, 1) * (np.arange(n) / SR < end)
    mix = mix + bed
    mix = np.tanh(mix * 1.6) / 1.6
    mix = mix / max(1e-6, np.abs(mix).max()) * 0.95
    import soundfile as sf
    sf.write(f'{L}_dialogue.wav', np.stack([mix, mix], 1).astype(np.float32), SR)
    json.dump({'subs': subs, 'end': round(end, 2)}, open(f'{L}_subs.json', 'w'), indent=1)
    print(L, 'dialogue', round(end, 1), 's')


for L in sys.argv[1:]:
    build(L)
