#!/usr/bin/env python3
"""Two-part cinematic hunting reel series «Утро охотника».

Usage: build_reels.py <1|2> [steps...]
steps: video | audio | ass | final | sheet   (default: video audio ass final sheet)
REDO=0,6 build_reels.py 2 video ass final    -> re-render only shots 0 and 6
SYNTH_BIRDS=1 build_reels.py 1 audio final   -> add synthesized birdsong (off by default)

v2 (11.10): all fixes from HANDOFF «Что исправить дальше» + contact sheet for frame review.
"""
import subprocess, os, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

_HERE = os.path.dirname(os.path.abspath(__file__))
W = os.environ.get("WORK", os.path.join(_HERE, "work"))
SRC = os.environ.get("SRC", os.path.join(_HERE, "src"))  # folder with the original 20261011_*.mp4
AVATAR = os.path.join(_HERE, "avatar.png")
FONTS = os.environ.get("FONTS", "/usr/share/fonts/opentype/inter")  # Inter / Inter Display
FPS, SR = 30, 44100
HANDLE = "@riz1van.live"
# synthesized birds sounded artificial in review -> live sound only unless explicitly enabled
SYNTH_BIRDS = os.environ.get("SYNTH_BIRDS", "0") == "1"

# ---------------------------------------------------------------- grades
GRAIN = "noise=alls=5:allf=t"
GR = {
    "cine": "eq=contrast=1.14:saturation=1.32:gamma=0.97,curves=all='0/0 0.1/0.06 0.5/0.5 0.9/0.95 1/1',"
            "colorbalance=rs=-0.03:bs=0.035:rm=0.01:bm=-0.01:rh=0.045:bh=-0.05,vibrance=intensity=0.35,"
            f"unsharp=5:5:0.45,vignette=PI/7,{GRAIN}",
    "gold": "eq=contrast=1.17:saturation=1.4:gamma=0.95,curves=all='0/0 0.1/0.05 0.5/0.5 0.9/0.96 1/1',"
            "colorbalance=rs=-0.02:bs=0.03:rm=0.03:bm=-0.03:rh=0.06:bh=-0.07,vibrance=intensity=0.4,"
            f"unsharp=5:5:0.45,vignette=PI/6.5,{GRAIN}",
    "fog": "eq=contrast=1.22:saturation=1.3:gamma=0.95,curves=all='0/0 0.15/0.08 0.5/0.48 0.88/0.93 1/1',"
           "colorbalance=rs=-0.03:bs=0.04:rh=0.04:bh=-0.04,vibrance=intensity=0.35,"
           f"unsharp=5:5:0.4,vignette=PI/7,{GRAIN}",
    "night": "eq=contrast=1.1:saturation=1.1:gamma=1.08,colorbalance=rs=-0.04:bs=0.06:rh=0.03,"
             "vignette=PI/5,noise=alls=7:allf=t",
    "dusk": "eq=contrast=1.12:saturation=1.45:gamma=1.18,colorbalance=rs=-0.03:bs=0.05:rh=0.05:bh=-0.03,"
            "vibrance=intensity=0.4,vignette=PI/6,noise=alls=7:allf=t",
    # v2: no grain on the clean sky (heron shot) — denoise only
    "sky": "eq=contrast=1.3:saturation=1.45:gamma=0.92,curves=all='0/0 0.2/0.1 0.5/0.48 0.85/0.92 1/1',"
           "colorbalance=bs=0.03:bm=0.02:rh=0.03,hqdn3d=4:3:6:6,vignette=PI/6",
    "face": "eq=contrast=1.07:saturation=1.1:gamma=1.0,colorbalance=rs=-0.015:bs=0.02:rh=0.02:bh=-0.02,"
            "unsharp=5:5:0.6,vignette=PI/7,noise=alls=4:allf=t",
}

# shot: dict(src, ss, d, z=push-in, zb=base zoom, cx/cy=crop anchor 0..1, g=grade, mute, tin, speed, pan, voice)
P1 = [
    dict(src="20261011_062052", ss=4.4, d=3.2, z=0.13, g="gold"),                                    # 0 hook
    # v2: night car — weakest shot, cut 2.4 -> 1.5 s, no "05:03" stamp (clock is in frame)
    dict(src="20261011_050256", ss=0.3, d=1.5, z=0.05, g="night", mute=True, tin="cut"),             # 1
    dict(src="20261011_054232", ss=1.0, d=2.8, z=0.04, g="dusk", mute=True, tin="fade", speed=0.5),  # 2
    dict(src="20261011_060930", ss=0.0, d=2.0, z=0.08, g="gold", tin="cut"),                         # 3
    dict(src="20261011_060709", ss=0.6, d=3.0, z=0.09, g="gold", tin="fade"),                        # 4
    dict(src="20261011_062052", ss=7.2, d=2.6, z=0.07, g="gold", tin="cut"),                         # 5
    # v2: first frame was smeared -> start 0.5 s later
    dict(src="20261011_062052", ss=18.2, d=2.6, z=0.06, g="cine", tin="cut"),                        # 6
    # v2: head was cut by the centred push-in -> anchor crop to the top
    dict(src="20261011_063635", ss=0.0, d=2.6, z=0.05, cy=0.0, g="cine", tin="cut"),                 # 7
    dict(src="20261011_063635", ss=9.5, d=3.0, z=0.07, g="fog", tin="fade"),                         # 8
    dict(src="20261011_063635", ss=44.0, d=3.2, z=0.10, g="fog", tin="fade"),                        # 9
    dict(src="END", d=2.5, tin="black"),                                                             # 10
]
P2 = [
    dict(src="20261011_070410", ss=0.8, d=3.0, g="sky", pan=True, p0=0.35),                          # 0 hook
    # v2: herons were tiny -> 1.35x base zoom
    dict(src="20261011_064738", ss=2.0, d=2.6, z=0.08, zb=1.35, g="fog", tin="cut"),                 # 1
    dict(src="20261011_064940", ss=0.0, d=2.6, z=0.08, g="fog", tin="cut"),                          # 2
    dict(src="20261011_065238", ss=1.2, d=3.0, z=0.08, g="gold", tin="fade"),                        # 3
    # v2: 070447 ss=0.5 (3 s of empty haze) removed; next shot now enters with a fade
    dict(src="20261011_070447", ss=5.6, d=2.4, z=0.08, g="cine", tin="fade"),                        # 4
    # v2: bags/bottles in frame -> start at 11.0 (ends at 13.0, speech stays continuous)
    dict(src="20261011_074148", ss=11.0, d=2.0, z=0.04, g="face", tin="cut", voice=True),            # 5
    dict(src="20261011_074148", ss=13.0, d=3.4, z=0.05, g="face", tin="cut", voice=True),            # 6
    dict(src="END", d=2.5, tin="black"),                                                             # 7
]
TRANS = {"cut": ("fade", 1 / FPS), "fade": ("fade", 0.45), "black": ("fadeblack", 0.6)}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(map(str, cmd))[:600]); print(r.stderr[-2000:]); sys.exit(1)
    return r


def timeline(shots):
    starts, t = [], 0.0
    for i, s in enumerate(shots):
        if i:
            t -= TRANS[s.get("tin", "cut")][1]
        starts.append(round(t, 4)); t += s["d"]
    return starts, round(t, 4)


def clean_end(shots, starts, total, i):
    """Moment shot i stops being alone on screen (= start of the next transition)."""
    return starts[i + 1] if i + 1 < len(shots) else total


# ---------------------------------------------------------------- video
def render_shot(s, path):
    d = s["d"]; frames = int(round(d * FPS))
    sp = s.get("speed", 1.0)
    pre = f"setpts=PTS/{sp}," if sp != 1.0 else ""
    cover = "scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:1920"
    if s.get("pan"):
        geo = f"{cover},scale=1512:2688:flags=bicubic,crop=1080:1920:x='(iw-1080)*min(1,{s.get('p0',0.15)}+0.4*t)':y='(ih-1920)*0.5'"
    else:
        z = s.get("z", 0.06); zb = s.get("zb", 1.0); ze = f"{zb}+{z}*t/{d}"
        cx, cy = s.get("cx", 0.5), s.get("cy", 0.5)
        geo = (f"{cover},scale=w='trunc(1080*({ze})/2)*2':h='trunc(1920*({ze})/2)*2':eval=frame:flags=bicubic,"
               f"crop=1080:1920:x='(iw-1080)*{cx}':y='(ih-1920)*{cy}'")
    vf = f"{pre}fps={FPS},{geo},{GR[s['g']]},format=yuv420p"
    src_d = d * sp + 0.2
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["ss"]), "-t", str(src_d), "-i", f"{SRC}/{s['src']}.mp4",
         "-vf", vf, "-frames:v", str(frames), "-an", "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-r", str(FPS), path])


def make_endcard(prev_clip, out_dir, d):
    # background = last frame of previous shot, blurred and darkened
    bgp = f"{out_dir}/end_bg.png"
    run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.1", "-i", prev_clip, "-frames:v", "1", bgp])
    bg = Image.open(bgp).convert("RGB").filter(ImageFilter.GaussianBlur(28))
    dark = Image.new("RGB", bg.size, (8, 12, 10))
    bg = Image.blend(bg, dark, 0.62)
    # avatar circle with thin light ring
    av = Image.open(AVATAR).convert("RGB")
    m_ = int(av.width * 0.02)
    av = av.crop((m_, m_, av.width - m_, av.height - m_)).resize((400, 400), Image.LANCZOS)
    mask = Image.new("L", (400, 400), 0); ImageDraw.Draw(mask).ellipse((0, 0, 399, 399), fill=255)
    av = ImageEnhance.Color(av).enhance(0.82)
    av = ImageEnhance.Contrast(av).enhance(0.96)
    r_, g_, b_ = av.split()
    av = Image.merge("RGB", (r_.point(lambda v: int(v * 0.95)), g_, b_.point(lambda v: min(255, int(v * 1.02)))))
    ring = Image.new("RGBA", (440, 440), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((14, 14, 425, 425), outline=(255, 255, 255, 190), width=4)
    canvas = bg.convert("RGBA")
    x0, y0 = 540 - 220, 600  # v2: 40 px higher — larger end-card text below
    canvas.alpha_composite(ring, (x0, y0))
    avr = Image.new("RGBA", (400, 400)); avr.paste(av, (0, 0), mask)
    canvas.alpha_composite(avr, (x0 + 20, y0 + 20))
    canvas.convert("RGB").save(f"{out_dir}/end.png")
    frames = int(round(d * FPS))
    run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-i", f"{out_dir}/end.png", "-vf",
         f"scale=w='trunc(1080*(1+0.04*t/{d})/2)*2':h='trunc(1920*(1+0.04*t/{d})/2)*2':eval=frame,crop=1080:1920,"
         f"noise=alls=3:allf=t,format=yuv420p", "-frames:v", str(frames), "-r", str(FPS),
         "-c:v", "libx264", "-crf", "14", "-preset", "fast", f"{out_dir}/clip_end.mp4"])


def render_video(shots, out_dir, redo=None):
    clips = []
    for i, s in enumerate(shots):
        p = f"{out_dir}/clip{i:02d}.mp4"
        if s["src"] == "END":
            make_endcard(clips[-1], out_dir, s["d"]); p = f"{out_dir}/clip_end.mp4"
        elif redo is None or i in redo or not os.path.exists(p):
            render_shot(s, p)
        clips.append(p)
    # xfade chain
    starts, total = timeline(shots)
    args = ["ffmpeg", "-v", "error", "-y"]
    for c in clips: args += ["-i", c]
    fc = [f"[{i}:v]settb=AVTB,setpts=PTS-STARTPTS,fps={FPS},setsar=1,format=yuv420p[v{i}]" for i in range(len(clips))]
    last = "[v0]"
    for i in range(1, len(clips)):
        tname, td = TRANS[shots[i].get("tin", "cut")]
        off = starts[i]
        lab = f"[x{i}]"
        fc.append(f"{last}[v{i}]xfade=transition={tname}:duration={td:.4f}:offset={off:.4f}{lab}")
        last = lab
    args += ["-filter_complex", ";".join(fc), "-map", last, "-c:v", "libx264", "-crf", "14", "-preset", "fast",
             "-r", str(FPS), f"{out_dir}/video_raw.mp4"]
    run(args)
    return total


# ---------------------------------------------------------------- audio
def read_wav(p):
    with wave.open(p) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, 2)


def write_wav(p, a):
    a = np.clip(a, -1, 1)
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a * 32767).astype(np.int16).tobytes())


def ambience(shots, out_dir, total):
    starts, _ = timeline(shots)
    bus = np.zeros((int(total * SR) + SR, 2), np.float32)
    for i, s in enumerate(shots):
        if s["src"] == "END" or s.get("mute"):
            continue
        p = f"{out_dir}/amb{i:02d}.wav"
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(s["ss"]), "-t", str(s["d"] * s.get("speed", 1)), "-i",
             f"{SRC}/{s['src']}.mp4", "-vn", "-af", ("highpass=f=90,lowpass=f=12000,afftdn=nr=8,aresample=44100" if s.get("voice") else "highpass=f=140,lowpass=f=10000,aresample=44100"), "-ac", "2", p])
        a = read_wav(p)
        n = len(a); f = int(0.35 * SR)
        env = np.ones(n, np.float32); env[:f] = np.linspace(0, 1, f); env[-f:] = np.linspace(1, 0, f)
        # normalise each clip ambience to similar level; v2: voices noticeably louder than nature
        rms = np.sqrt(np.mean(a ** 2)) + 1e-5
        a = a * env[:, None] * min((0.12 if s.get("voice") else 0.05) / rms, 6.0)
        i0 = int(starts[i] * SR)
        bus[i0:i0 + n] += a[: len(bus) - i0]
    write_wav(f"{out_dir}/amb.wav", bus[: int(total * SR)])


def reverb(x, seconds=2.8, seed=1, wet=0.35):
    rng = np.random.default_rng(seed)
    n = int(seconds * SR); t = np.arange(n) / SR
    out = np.zeros_like(x)
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-t / (seconds / 6.5))
        ir[: int(0.012 * SR)] = 0
        ir /= np.sqrt(np.sum(ir ** 2))
        L = len(x) + n
        N = 1 << (L - 1).bit_length()
        y = np.fft.irfft(np.fft.rfft(x[:, ch], N) * np.fft.rfft(ir, N), N)[: len(x)]
        out[:, ch] = y
    return x * (1 - wet) + out * wet * 1.6


def nature(total, part, out_dir, starts, birds_from, crickets_to, gusts, duck=None):
    """No music: wind bed, crickets, wind gusts (+ synthesized birdsong if SYNTH_BIRDS).
    duck=(t0, t1): whole bed drops to 35% so voices sit on top."""
    n = int(total * SR) + SR
    mix = np.zeros((n, 2))
    rng = np.random.default_rng(300 + part)
    t_all = np.arange(n) / SR

    def add(sig, at, pan=0.0, g=1.0):
        i = int(at * SR)
        if i >= n or at < 0: return
        sig = sig[: n - i]
        mix[i:i + len(sig), 0] += sig * g * (1 - max(pan, 0))
        mix[i:i + len(sig), 1] += sig * g * (1 + min(pan, 0))

    # wind bed: brown-ish noise with slow swells, stereo decorrelated
    for ch in range(2):
        w = np.cumsum(rng.standard_normal(n)); w -= np.convolve(w, np.ones(4410) / 4410, "same")
        w /= np.abs(w).max() + 1e-9
        swell = 0.55 + 0.45 * np.sin(2 * np.pi * t_all / 7.3 + ch) * np.sin(2 * np.pi * t_all / 3.1 + 1.3 * ch)
        mix[:, ch] += w * swell * 0.05

    # gusts: rising airy swell
    for at, g in gusts:
        m = int(2.6 * SR); t = np.arange(m) / SR
        x = np.cumsum(rng.standard_normal(m)); x -= np.convolve(x, np.ones(120) / 120, "same")
        x /= np.abs(x).max() + 1e-9
        e = np.sin(np.pi * np.clip(t / 2.6, 0, 1)) ** 2
        st = at - 1.3
        sig = x * e * 0.14 * g
        if st < 0: sig = sig[int(-st * SR):]; st = 0.0
        add(sig, st, 0.0)

    # crickets (night/dusk)
    if crickets_to > 0:
        tt = 0.2
        while tt < crickets_to:
            m = int(0.35 * SR); t = np.arange(m) / SR
            f = 4300 + rng.uniform(-300, 300)
            pulses = (np.sin(2 * np.pi * 28 * t) > 0.2).astype(float)
            c = np.sin(2 * np.pi * f * t) * pulses * np.sin(np.pi * t / 0.35)
            fade = 1.0 if tt < crickets_to - 1.5 else max(0, (crickets_to - tt) / 1.5)
            add(c * 0.012 * fade, tt, rng.uniform(-0.7, 0.7))
            tt += rng.uniform(0.35, 0.9)

    # dawn birdsong: several "species" of trills/whistles at different distances
    def chirp(f0, f1, dur, harm=0.15):
        m = int(dur * SR); t = np.arange(m) / SR
        f = f0 + (f1 - f0) * (t / dur) ** 0.7
        ph = 2 * np.pi * np.cumsum(f) / SR
        e = np.sin(np.pi * t / dur) ** 1.5
        return (np.sin(ph) + harm * np.sin(2 * ph)) * e

    def song(kind):
        parts = []
        if kind == 0:  # quick descending trill
            base = rng.uniform(3800, 5200)
            for k in range(rng.integers(5, 10)):
                parts.append(chirp(base * (1 - 0.02 * k), base * 0.75, 0.05)); parts.append(np.zeros(int(0.025 * SR)))
        elif kind == 1:  # two-note whistle (tit-like "ti-tu")
            hi = rng.uniform(4500, 6000); lo = hi * 0.78
            for k in range(rng.integers(2, 4)):
                parts += [chirp(hi, hi * 1.02, 0.11, 0.05), np.zeros(int(0.05 * SR)), chirp(lo, lo * 0.98, 0.13, 0.05),
                          np.zeros(int(0.12 * SR))]
        else:  # warbling phrase
            base = rng.uniform(2600, 3600)
            for k in range(rng.integers(6, 12)):
                a_ = base * rng.uniform(0.8, 1.4); b_ = a_ * rng.uniform(0.7, 1.3)
                parts.append(chirp(a_, b_, rng.uniform(0.04, 0.09), 0.25)); parts.append(np.zeros(int(rng.uniform(0.01, 0.04) * SR)))
        return np.concatenate(parts)

    if SYNTH_BIRDS:
        tt = birds_from
        while tt < total - 1.0:
            kind = int(rng.integers(0, 3))
            sng = song(kind)
            dist = rng.uniform(0.3, 1.0)  # 1 = close
            g = 0.035 * dist
            fade_in = min(1.0, (tt - birds_from) / 1.5 + 0.2)
            add(sng * g * fade_in, tt, rng.uniform(-0.8, 0.8))
            tt += rng.uniform(0.6, 1.8)

    mix = reverb(mix, seconds=2.2, seed=part + 11, wet=0.3)
    mix *= np.clip((total - t_all) / 1.6, 0, 1)[:, None]
    mix *= np.clip(t_all / 0.3, 0, 1)[:, None]
    mix /= np.abs(mix).max() + 1e-9
    if duck:
        t0, t1 = duck  # smooth 0.4 s ramps down to 0.35 and back
        g = 1 - 0.65 * np.clip(np.minimum((t_all - t0 + 0.4) / 0.4, (t1 + 0.4 - t_all) / 0.4), 0, 1)
        mix *= g[:, None]
    write_wav(f"{out_dir}/music.wav", (mix * 0.5)[: int(total * SR)])


# ---------------------------------------------------------------- captions
GOLD = r"{\c&H6FC8F0&}"  # warm gold (BGR)
WHT = r"{\c&HFFFFFF&}"


def at(s):
    h = int(s // 3600); m = int(s % 3600 // 60); sec = s - h * 3600 - m * 60
    return f"{h}:{m:02d}:{sec:05.2f}"


def ass(events, out_dir):
    # v2: Kicker 40 -> 56 and Small 44 -> 64 (≈×1.5, limited by line width), new Cta style for the end-card call
    hdr = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Kicker,Inter Display SemiBold,56,&H00FFFFFF,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,4,0,1,3,0,5,40,40,40,1
Style: Hook,Inter Display ExtraBold,104,&H00FFFFFF,&H00FFFFFF,&H50000000,&H00000000,0,0,0,0,100,100,0,0,1,6,0,5,50,50,40,1
Style: Stamp,Inter Display Thin,150,&H00FFFFFF,&H00FFFFFF,&H6E000000,&H00000000,0,0,0,0,100,100,6,0,1,4,0,5,40,40,40,1
Style: Line,Inter Display SemiBold,72,&H00FFFFFF,&H00FFFFFF,&H5A000000,&H00000000,0,0,0,0,100,100,0,0,1,5,0,5,60,60,40,1
Style: Small,Inter Display Medium,64,&H00FFFFFF,&H00FFFFFF,&H5A000000,&H00000000,0,0,0,0,100,100,2,0,1,4,0,5,60,60,40,1
Style: Handle,Inter Display ExtraBold,78,&H00FFFFFF,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,3,0,5,40,40,40,1
Style: Cta,Inter Display ExtraBold,110,&H00FFFFFF,&H00FFFFFF,&H64000000,&H00000000,0,0,0,0,100,100,1,0,1,4,0,5,40,40,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for st, en, style, y, text in events:
        anim = r"\fad(350,250)" + rf"\move(540,{y + 18},540,{y},0,450)"
        # v2: soft dark pad under every line (invisible fill + wide blurred dark border) for bright sky/grass
        pad = r"{\blur24\bord22\1a&HFF&\3c&H000000&\3a&H78&" + anim + "}"
        lines.append(f"Dialogue: 0,{at(st)},{at(en)},{style},,0,0,0,,{pad}{text}")
        lines.append(f"Dialogue: 1,{at(st)},{at(en)},{style},,0,0,0,,{{\\blur6{anim}}}{text}")
    with open(f"{out_dir}/caps.ass", "w") as f:
        f.write(hdr + "\n".join(lines) + "\n")


def captions(part, shots):
    s, total = timeline(shots)
    # v2: e(i) = start of the next transition, so text never hangs over the next shot / end card
    e = lambda i: clean_end(shots, s, total, i)
    E = []
    if part == 1:
        E += [(0.15, e(0) - 0.15, "Kicker", 330, "УТРО ОХОТНИКА · ЧАСТЬ 1"),
              (0.25, e(0) - 0.1, "Hook", 860, "Сколько стоит"),
              (0.6, e(0) - 0.1, "Hook", 975, f"{GOLD}такой рассвет?"),
              (s[1] + 0.15, e(1) - 0.1, "Line", 1000, "Город ещё спит"),
              (s[2] + 0.3, e(2) - 0.2, "Stamp", 820, "05:42"),
              (s[2] + 0.6, e(2) - 0.2, "Line", 1000, f"Дорога {GOLD}в темноте"),
              (s[3] + 0.1, e(3) - 0.1, "Line", 1250, f"Всё {GOLD}готово"),
              (s[4] + 0.4, e(4) - 0.2, "Stamp", 820, "06:07"),
              (s[4] + 0.7, e(4) - 0.2, "Line", 1000, f"И тут — {GOLD}солнце"),
              (s[6] + 0.2, e(6) - 0.1, "Line", 1250, "Выходим на позицию"),
              # v2: stamp moved off the hunter's belt into the lower third
              (s[7] + 0.1, e(7) - 0.1, "Stamp", 1380, "06:36"),
              (s[7] + 0.4, e(7) - 0.1, "Line", 1540, f"Засидка. {GOLD}Ни звука."),
              (s[8] + 0.4, e(8) - 0.2, "Line", 1250, f"Туман ложится {GOLD}на воду"),
              (s[9] + 0.4, e(9) - 0.1, "Hook", 900, f"А потом {GOLD}из тумана…"),
              (s[9] + 1.2, e(9) - 0.1, "Small", 1040, "продолжение — часть 2 →"),
              ]
        end_lines = ["Подпишись, чтобы увидеть", "часть 2"]
    else:
        E += [(0.15, e(0) - 0.15, "Kicker", 330, "УТРО ОХОТНИКА · ЧАСТЬ 2"),
              (0.25, e(0) - 0.1, "Hook", 1180, "И тут из тумана —"),
              (1.0, e(0) - 0.1, "Hook", 1295, f"{GOLD}цапля"),
              (s[1] + 0.2, e(1) - 0.1, "Line", 1250, f"А в тростнике — {GOLD}ещё"),
              (s[2] + 0.2, e(2) - 0.1, "Line", 1250, "Поднялись в воздух"),
              (s[3] + 0.4, e(3) - 0.2, "Stamp", 820, "06:52"),
              (s[3] + 0.7, e(3) - 0.2, "Line", 1000, f"Солнце пробивает {GOLD}туман"),
              (s[4] + 0.2, e(4) - 0.1, "Line", 1250, f"Тишина, которую {GOLD}не купишь"),
              (s[5] + 0.1, e(5) - 0.05, "Line", 1250, "Охота — это не про трофей."),
              (s[6] + 0.15, e(6) - 0.1, "Line", 1210, f"Это про {GOLD}такие утра"),
              (s[6] + 0.9, e(6) - 0.1, "Line", 1300, f"и тех, {GOLD}кто рядом"),
              ]
        end_lines = ["Сохрани это утро", r"{\fs80}Часть 1 — в профиле"]
    # v2: end card 3.4 -> 2.5 s, larger text, CTA in its own big style
    ie = len(shots) - 1
    E += [(s[ie] + 0.3, total, "Handle", 1140, HANDLE),
          (s[ie] + 0.5, total, "Small", 1230, "Ризван · Дагестан и дальше"),
          (s[ie] + 0.75, total, "Small", 1370, end_lines[0]),
          (s[ie] + 0.95, total, "Cta", 1490, f"{GOLD}{end_lines[1]}")]
    return E


# ---------------------------------------------------------------- frame review
def contact_sheet(part, shots, video, out_dir):
    """3 frames per shot (start / middle / end of its clean part) with captions burned in -> one PNG."""
    s, total = timeline(shots)
    tiles = []
    for i in range(len(shots)):
        a, b = s[i] + (TRANS[shots[i].get("tin", "cut")][1] if i else 0), clean_end(shots, s, total, i)
        for k, t in enumerate((a + 0.05, (a + b) / 2, b - 0.08)):
            p = f"{out_dir}/sheet_{i:02d}_{k}.png"
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1",
                 "-vf", "scale=270:480", p])
            im = Image.open(p).convert("RGB")
            ImageDraw.Draw(im).text((6, 4), f"#{i} {t:.2f}s", fill=(255, 255, 0))
            tiles.append(im)
    cols = 6; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 274, rows * 484), (20, 20, 20))
    for j, im in enumerate(tiles):
        sheet.paste(im, ((j % cols) * 274 + 2, (j // cols) * 484 + 2))
    sheet.save(f"{W}/series/okhota_part{part}_sheet.png")


# ---------------------------------------------------------------- main
def build(part, steps, redo=None):
    shots = P1 if part == 1 else P2
    out = f"{W}/series/p{part}"; os.makedirs(out, exist_ok=True)
    starts, total = timeline(shots)
    if "video" in steps: render_video(shots, out, redo)
    if "audio" in steps:
        ambience(shots, out, total)
        s_ = starts
        if part == 1:
            nature(total, 1, out, s_, birds_from=s_[3] + 0.3, crickets_to=s_[3] + 1.0,
                   gusts=[(0.6, 0.8), (s_[9] + 1.2, 1.0), (s_[10] + 0.6, 0.6)])
        else:
            nature(total, 2, out, s_, birds_from=0.4, crickets_to=0,
                   gusts=[(0.6, 0.9), (s_[7] + 0.6, 0.6)], duck=(s_[5], s_[7]))
    if "ass" in steps: ass(captions(part, shots), out)
    name = f"{W}/series/okhota_part{part}"
    if "final" in steps:
        run(["ffmpeg", "-v", "error", "-y", "-i", f"{out}/music.wav", "-i", f"{out}/amb.wav", "-filter_complex",
             "[0:a]volume=0.9[m];[1:a]volume=1.0[a];[m][a]amix=inputs=2:duration=first:normalize=0,"
             "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=44100[o]", "-map", "[o]", f"{out}/mix.wav"])
        run(["ffmpeg", "-v", "error", "-y", "-i", f"{out}/video_raw.mp4", "-i", f"{out}/mix.wav",
             "-vf", f"ass={out}/caps.ass:fontsdir={FONTS}", "-c:v", "libx264", "-crf", "19", "-maxrate", "16M", "-bufsize", "32M", "-preset", "medium",
             "-pix_fmt", "yuv420p", "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart",
             "-t", f"{total}", f"{name}_HQ.mp4"])
        run(["ffmpeg", "-v", "error", "-y", "-i", f"{name}_HQ.mp4", "-c:v", "libx264", "-b:v", "6M", "-maxrate", "7M",
             "-bufsize", "14M", "-preset", "medium", "-c:a", "copy", "-movflags", "+faststart", f"{name}.mp4"])
    if "sheet" in steps and os.path.exists(f"{name}_HQ.mp4"):
        contact_sheet(part, shots, f"{name}_HQ.mp4", out)
    print("part", part, "total", total)


if __name__ == "__main__":
    part = int(sys.argv[1])
    steps = sys.argv[2:] or ["video", "audio", "ass", "final", "sheet"]
    redo = os.environ.get("REDO")
    build(part, steps, None if redo is None else {int(x) for x in redo.split(",") if x})
