"""reel_maker.py - make a 1080x1920 text/terminal reel (no footage, no AI images) from a JSON spec.

Usage: python reel_maker.py spec.json out.mp4 [--still SECONDS out.png]

Spec: {"accent":"#FF7A1A", "scenes":[ ... ]}  scene types:
  hook  : {"type":"hook","label":"// CLAUDE CODE","title":"8 *commands* I use daily","chips":["8 COMMANDS"],"dur":3}
  term  : {"type":"term","label":"COMMAND 01 / 08","title":"*/init* sets the rules","lines":["$ /init","> CLAUDE.md created"],"note":"...","dur":4}
  bars  : {"type":"bars","label":"...","title":"...","bars":[["youtube.com",21.1],...],"unit":"%","note":"...","dur":6}
  tips  : {"type":"tips","label":"...","title":"...","items":["...","..."],"dur":5}
  "instant_hook": true at spec top level = first scene fully visible from frame 0 (better Shorts retention/thumbnail)
  cta   : {"type":"cta","label":"// BEFORE YOU SCROLL","title":"*Save* this","chips":["Save","Follow"],"note":"...","dur":3}
Title: wrap *word* in asterisks for the accent colour + underline.
Audio: soft synthesised pad + a tick on every scene start (no licensed music needed).
"""
import json, math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
F = "C:/Windows/Fonts/"
def font(name, size): return ImageFont.truetype(F + name, size)
TITLE = font("seguibl.ttf", 102); LABEL = font("consolab.ttf", 34); MONO = font("consola.ttf", 46)
MONOB = font("consolab.ttf", 46); CHIP = font("segoeuib.ttf", 36); NOTE = font("seguisb.ttf", 46)
BAR = font("segoeuib.ttf", 44); BIG = font("seguibl.ttf", 64); TIP = font("seguisb.ttf", 46)
WHITE = (245, 245, 240); MUTED = (150, 155, 165); PANEL = (24, 27, 33); EDGE = (48, 52, 60)
X0, XMAX = 90, 960

def hexc(h): h = h.lstrip("#"); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def ease(t): t = max(0.0, min(1.0, t)); return 1 - (1 - t) ** 3
def appear(t, start, dur=0.45): return ease((t - start) / dur)

def background():
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt((x - 150) ** 2 + (y - 120) ** 2) / 1500
    glow = np.clip(1 - d, 0, 1) ** 2
    base = np.array([14, 16, 20], np.float32); warm = np.array([70, 40, 18], np.float32)
    img = base + glow[..., None] * (warm - base) * 0.9
    return Image.fromarray(img.astype(np.uint8))

def parse_title(s):
    out = []
    for i, part in enumerate(s.split("*")):
        for w in part.split():
            if out and all(ch in ".,!?:;" for ch in w) and part.startswith(w):
                out[-1] = (out[-1][0] + w, out[-1][1]); continue
            out.append((w, i % 2 == 1))
    return out

def wrap_title(words, fnt, maxw):
    lines, cur, cw = [], [], 0
    sp = fnt.getlength(" ")
    for w, acc in words:
        wl = fnt.getlength(w)
        if cur and cw + sp + wl > maxw:
            lines.append(cur); cur, cw = [], 0
        cur.append((w, acc)); cw += (sp if len(cur) > 1 else 0) + wl
    if cur: lines.append(cur)
    return lines

class Layer:
    """draw onto an RGBA overlay with per-element alpha and y-offset"""
    def __init__(self, base): self.base = base
    def put(self, fn, alpha, dy=0):
        if alpha <= 0: return
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        fn(d, dy)
        if alpha < 1:
            a = ov.split()[3].point(lambda v: int(v * alpha)); ov.putalpha(a)
        self.base.alpha_composite(ov)

def draw_label(d, y, text, acc):
    d.text((X0, y), text, font=LABEL, fill=acc)

def draw_title(d, y, title, acc, fnt=TITLE, maxw=XMAX - X0):
    lines = wrap_title(parse_title(title), fnt, maxw)
    lh = int(fnt.size * 1.08); sp = fnt.getlength(" ")
    for li, line in enumerate(lines):
        x = X0; yy = y + li * lh
        for w, accent in line:
            col = acc if accent else WHITE
            d.text((x, yy), w, font=fnt, fill=col)
            wl = fnt.getlength(w)
            if accent:
                d.rectangle([x, yy + fnt.size * 1.02, x + wl, yy + fnt.size * 1.02 + 7], fill=acc)
            x += wl + sp
    return y + len(lines) * lh

def draw_chips(d, y, chips, acc, x=X0):
    for i, c in enumerate(chips):
        tw = CHIP.getlength(c); w = tw + 44
        fill, tc = ((255, 255, 255), (20, 20, 20)) if i == 0 else (acc, (20, 20, 20))
        d.rounded_rectangle([x, y, x + w, y + 64], 12, fill=fill)
        d.text((x + 22, y + 10), c, font=CHIP, fill=tc)
        x += w + 18

def draw_note(d, y, text, acc):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if NOTE.getlength(t) > XMAX - X0 - 60: lines.append(cur); cur = w
        else: cur = t
    lines.append(cur)
    h = 34 + len(lines) * 60
    d.rounded_rectangle([X0, y, XMAX, y + h], 18, fill=(30, 33, 40), outline=EDGE, width=2)
    d.ellipse([X0 + 26, y + 34, X0 + 40, y + 48], fill=acc)
    for i, l in enumerate(lines):
        d.text((X0 + 60, y + 14 + i * 60), l, font=NOTE, fill=WHITE)
    return y + h

def terminal(d, y, lines, t, start, acc, title="~/my-project - terminal"):
    h = 130 + max(3, len(lines)) * 68
    d.rounded_rectangle([X0, y, XMAX, y + h], 22, fill=PANEL, outline=EDGE, width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([X0 + 28 + i * 34, y + 28, X0 + 48 + i * 34, y + 48], fill=c)
    d.text((X0 + 300, y + 24), title, font=font("consola.ttf", 28), fill=MUTED)
    cps = 22; tt = t - start; yy = y + 90
    for i, line in enumerate(lines):
        is_cmd = line.startswith("$")
        if is_cmd:
            n = int(max(0, tt) * cps); shown = line[:n]; tt -= len(line) / cps + 0.35
            done = n >= len(line)
        else:
            if tt < 0: break
            shown, done = line, True; tt -= 0.45
        col = WHITE if is_cmd else ((120, 220, 140) if line.startswith(("✓", "+")) else MUTED)
        d.text((X0 + 32, yy), shown, font=MONOB if is_cmd else MONO, fill=col)
        if is_cmd and not done:
            cx = X0 + 32 + MONOB.getlength(shown)
            if int(t * 2.5) % 2 == 0: d.rectangle([cx + 4, yy + 4, cx + 26, yy + 52], fill=acc)
            break
        yy += 68
    return y + h

def scene_frame(sc, t, bg, acc):
    img = bg.copy().convert("RGBA"); L = Layer(img); typ = sc["type"]
    y0 = 360
    def slide(start): a = appear(t, start); return a, int((1 - a) * 40)
    if typ in ("hook", "cta"):
        a, dy = slide(0.0)
        L.put(lambda d, _: draw_label(d, y0 + dy, sc.get("label", ""), acc), a)
        a2, dy2 = slide(0.15)
        endy = [y0 + 60]
        def tl(d, _):
            endy[0] = draw_title(d, y0 + 60 + dy2, sc["title"], acc, fnt=font("seguibl.ttf", 112))
        L.put(tl, a2)
        a3, dy3 = slide(0.6)
        L.put(lambda d, _: draw_chips(d, endy[0] + 50 + dy3, sc.get("chips", []), acc), a3)
        for gi, g in enumerate(sc.get("grid", [])):
            ag, dyg = slide(0.9 + gi * 0.12)
            def gd(d, _, gi=gi, g=g, dyg=dyg):
                cx = X0 + (gi % 2) * 445; cy = endy[0] + 170 + (gi // 2) * 130 + dyg
                d.rounded_rectangle([cx, cy, cx + 420, cy + 108], 18, fill=PANEL, outline=EDGE, width=2)
                d.text((cx + 28, cy + 26), g, font=font("consolab.ttf", 50), fill=acc if gi % 3 == 0 else WHITE)
            L.put(gd, ag)
        if sc.get("note"):
            a4, dy4 = slide(1.0)
            L.put(lambda d, _: draw_note(d, endy[0] + 170 + dy4, sc["note"], acc), a4)
    elif typ == "term":
        a, dy = slide(0.0)
        L.put(lambda d, _: draw_label(d, y0 + dy, sc["label"], acc), a)
        endy = [0]
        def tl(d, _): endy[0] = draw_title(d, y0 + 55 + dy, sc["title"], acc)
        L.put(tl, a)
        a2, dy2 = slide(0.25)
        ty = [0]
        def tm(d, _): ty[0] = terminal(d, endy[0] + 50 + dy2, sc["lines"], t, 0.6, acc)
        L.put(tm, a2)
        if sc.get("note"):
            a3, dy3 = slide(sc.get("note_at", 2.2))
            L.put(lambda d, _: draw_note(d, ty[0] + 40 + dy3, sc["note"], acc), a3)
    elif typ == "bars":
        a, dy = slide(0.0)
        L.put(lambda d, _: draw_label(d, y0 + dy, sc["label"], acc), a)
        endy = [0]
        def tl(d, _): endy[0] = draw_title(d, y0 + 55 + dy, sc["title"], acc)
        L.put(tl, a)
        bars = sc["bars"]; mx = max(v for _, v in bars); unit = sc.get("unit", "")
        def bd(d, _):
            y = endy[0] + 60
            for i, (name, v) in enumerate(bars):
                p = appear(t, 0.5 + i * 0.25, 0.7)
                if p <= 0: break
                d.text((X0, y), name, font=BAR, fill=WHITE if i < sc.get("hi", 3) else MUTED)
                bw = (XMAX - X0 - 170) * (v / mx) * p
                col = acc if i < sc.get("hi", 3) else (70, 75, 85)
                d.rounded_rectangle([X0, y + 56, X0 + max(bw, 12), y + 92], 8, fill=col)
                d.text((X0 + bw + 18, y + 50), f"{v * p:.{sc.get("dec", 1)}f}{unit}", font=BAR, fill=WHITE)
                y += 132
            endy[0] = y
        L.put(bd, 1)
        if sc.get("note"):
            a3, dy3 = slide(sc.get("note_at", 0.5 + len(bars) * 0.25 + 0.8))
            L.put(lambda d, _: draw_note(d, endy[0] + 20 + dy3, sc["note"], acc), a3)
    elif typ == "tips":
        a, dy = slide(0.0)
        L.put(lambda d, _: draw_label(d, y0 + dy, sc["label"], acc), a)
        endy = [0]
        def tl(d, _): endy[0] = draw_title(d, y0 + 55 + dy, sc["title"], acc)
        L.put(tl, a)
        step = sc.get("step", 1.3)
        for i, it in enumerate(sc["items"]):
            ai, dyi = slide(0.5 + i * step)
            def td(d, _, i=i, it=it, dyi=dyi):
                y = endy[0] + 60 + i * 210 + dyi
                d.rounded_rectangle([X0, y, XMAX, y + 180], 20, fill=PANEL, outline=EDGE, width=2)
                d.text((X0 + 30, y + 22), f"{i + 1:02d}", font=BIG, fill=acc)
                head, _, body = it.partition("|")
                d.text((X0 + 140, y + 26), head, font=font("segoeuib.ttf", 48), fill=WHITE)
                d.text((X0 + 140, y + 98), body.strip(), font=font("segoeui.ttf", 38), fill=MUTED)
            L.put(td, ai)
    # progress bar at the very top of the safe area
    return img.convert("RGB")

def synth_audio(spec, total, path):
    sr = 44100; n = int(total * sr); t = np.arange(n) / sr
    chord = [110.0, 164.81, 220.0, 277.18]  # A minor-ish pad
    pad = sum(np.sin(2 * np.pi * f * t + i) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t + i)) for i, f in enumerate(chord))
    pad = pad / len(chord) * 0.16
    env = np.minimum(1, t / 1.5) * np.minimum(1, (total - t) / 1.5)
    out = pad * env
    tstart = 0.0
    for sc in spec["scenes"]:
        i0 = int(tstart * sr); k = np.arange(int(0.09 * sr)) / sr
        tick = np.sin(2 * np.pi * 1400 * k) * np.exp(-k * 60) * 0.35
        out[i0:i0 + len(tick)] += tick[: max(0, min(len(tick), n - i0))]
        tstart += sc["dur"]
    st = np.stack([out, out], 1); st = np.clip(st, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((st * 32767).astype(np.int16).tobytes())

def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8")); out = sys.argv[2]
    acc = hexc(spec.get("accent", "#FF7A1A")); bg = background()
    if "--still" in sys.argv:
        s = float(sys.argv[sys.argv.index("--still") + 1]); t0 = 0
        for sc in spec["scenes"]:
            if s < t0 + sc["dur"]:
                scene_frame(sc, s - t0, bg, acc).save(out); return
            t0 += sc["dur"]
        return
    total = sum(sc["dur"] for sc in spec["scenes"])
    wav = out + ".wav"; synth_audio(spec, total, wav)
    cmd = ["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5", "-shortest", "-movflags", "+faststart", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for si, sc in enumerate(spec["scenes"]):
        nf = int(round(sc["dur"] * FPS))
        skip = 2.0 if (si == 0 and spec.get("instant_hook")) else 0.0  # first frame fully drawn (thumbnail + no blank start)
        for f in range(nf):
            t = f / FPS; img = scene_frame(sc, t + skip, bg, acc)
            fo = min(1.0, (sc["dur"] - t) / 0.25)  # quick fade-out to next scene
            if fo < 1: img = Image.blend(bg, img, max(0, fo))
            p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    import os; os.remove(wav)
    print("done", out, f"{total:.1f}s", "exit", p.returncode)

if __name__ == "__main__":
    main()
