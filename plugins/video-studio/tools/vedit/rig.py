"""rig: the paper-cutout animation engine behind video-studio (Vox-style 2.5D parallax, word-synced).

A project's build.py does:

    from vedit import rig
    rig.init(__file__, hold=1.0)          # optional palette={"RED": "#c8102e"} for brand colours
    from vedit.rig import *               # after init, so TOTAL and the colours are current

    def hook() -> str:
        p = "hook"
        t = ph(p, 1, 2)                       # time of word 2 of script line 1, local to the scene
        front = cut("hk-dave", "dave", 330, 560, 400, 7) + label("hk-t", "THIS IS DAVE.", 330, 450, 64, "yellow")
        js = hide("#hk-dave") + pop("#hk-dave", t) + hide("#hk-t") + type_in("#hk-t", t)
        return scene(p, back="", mid="", front=front, js=js)

    BUILDERS = [("hook", hook), ...]           # one per scene id in script.txt, in order
    def sfx():                                 # (file, absolute time, volume)
        return [("pop", at("hook", 1, 2), 0.35)]
    if __name__ == "__main__":
        build(BUILDERS, sfx, key_words={"DAVE"}, red_words={"BURNED"})

Coordinates are a 1080x1920 frame. Each scene is a diorama on three layers (back, mid, front) that drift at
different speeds while the camera pushes in; labels and stamps (class "abs ui") go on a static layer above.
Everything a scene shows must be hidden at t=0 with hide() and brought in with a motion helper, timed with ph().
Images are assets/cut/NAME.png (torn-paper cutouts), textures assets/tex/NAME.jpg, sounds assets/sfx/NAME.mp3.
See the make-video skill's references/rig.md for the full catalogue and layout rules.
"""

import json
import re
import subprocess
from pathlib import Path

W, H = 1080, 1920
SHIFT = 130  # scenes sit lower so captions and the Reels UI frame them
CAPTION_TOP = 1420

PAPER = "#ece6d8"
INK = "#1b1915"
YELLOW = "#f2c419"
RED = "#d2232a"
GREEN = "#3f7a4a"
BLUE = "#2f6f9f"
CREAM = "#f3eee0"

ROOT: Path = Path(".")
TIMING: dict = {}
SCENES: dict = {}
PHRASES: dict = {}
TOTAL: float = 0.0


def init(build_file: str, hold: float = 1.0, palette: dict | None = None, shift: int = SHIFT) -> None:
    """Load timing.json next to build.py. hold = seconds the last scene stays after the last word.
    palette may override PAPER, INK, YELLOW, RED, GREEN, BLUE, CREAM (e.g. a brand's colours)."""
    global ROOT, TOTAL, SHIFT
    ROOT = Path(build_file).resolve().parent
    # filled in place, so names imported with `from vedit.rig import *` see the data
    TIMING.clear(); TIMING.update(json.loads((ROOT / "timing.json").read_text()))
    SCENES.clear(); SCENES.update({s["id"]: s for s in TIMING["scenes"]})
    PHRASES.clear(); PHRASES.update({p["n"]: p for p in TIMING["phrases"]})
    TIMING["scenes"][-1]["dur"] = round(TIMING["scenes"][-1]["dur"] + hold, 3)
    TOTAL = round(TIMING["total"] + hold, 2)
    SHIFT = shift
    for k, v in (palette or {}).items():
        globals()[k.upper()] = v


def ph(scene: str, n: int, i: int = 0, nudge: float = 0.0) -> float:
    """Scene-local time (s) of word i (0-based) in phrase n (1-based line of script.txt). Never before 0.1."""
    words = PHRASES[n]["words"]
    w = words[min(i, len(words) - 1)]
    return round(max(0.1, w["start"] - SCENES[scene]["start"] + nudge), 3)


def fill(tpl: str, **vals) -> str:
    for k, v in vals.items():
        tpl = tpl.replace(f"<<{k}>>", str(v))
    return tpl


def chars(text: str) -> str:
    return "".join(f'<span class="ch">{"&nbsp;" if c == " " else c}</span>' for c in text)


def cut(id_: str, name: str, x: int, y: int, w: int, z: int = 1) -> str:
    return f'<img id="{id_}" class="cut" src="assets/cut/{name}.png" style="left:{x}px;top:{y}px;width:{w}px;z-index:{z}">'


def label(id_: str, text: str, x: int, y: int, size: int = 40, kind: str = "paper", rot: float = -2) -> str:
    return (f'<div id="{id_}" class="abs ui" style="left:{x}px;top:{y}px;z-index:20"><div class="lbl {kind}" '
            f'style="font-size:{size}px;transform:rotate({rot}deg)">{chars(text)}</div></div>')


def stamp(id_: str, text: str, x: int, y: int, size: int = 56, color: str | None = None, rot: float = -6) -> str:
    color = color or RED
    return (f'<div id="{id_}" class="abs ui" style="left:{x}px;top:{y}px;z-index:21"><div class="stamp" '
            f'style="font-size:{size}px;color:{color};border-color:{color};transform:rotate({rot}deg)">{text}</div></div>')


def torn_strip(id_: str, tex: str, x: int, y: int, w: int, h: int, seed: int, z: int = 2) -> str:
    """A strip of textured paper with a torn top edge (for the ground cutaway)."""
    import random
    r = random.Random(seed)
    pts = [f"{i * 100 / 24:.1f}% {r.uniform(0, 9):.1f}px" for i in range(25)]
    clip = "polygon(" + ", ".join(pts) + ", 100% 100%, 0 100%)"
    if x <= 40 and w >= 1000:  # full-width strips bleed past the frame so parallax never shows an edge
        x, w = -140, 1360
    return (f'<div id="{id_}" class="abs strip" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};'
            f'background:url(assets/tex/{tex}.jpg) center/cover;clip-path:{clip}"></div>')


# ---------------------------------------------------------------- motion helpers (GSAP strings)

def pop(sel: str, t: float, dur: float = 0.5, origin: str = "50% 100%") -> str:
    return (f'tl.fromTo("{sel}", {{ scale: 0, opacity: 1, transformOrigin: "{origin}" }}, '
            f'{{ scale: 1, duration: {dur}, ease: "back.out(1.7)" }}, {t});\n')


def rise(sel: str, t: float, dy: int = 500, dur: float = 0.7) -> str:
    return f'tl.fromTo("{sel}", {{ y: {dy}, opacity: 1 }}, {{ y: 0, duration: {dur}, ease: "power3.out" }}, {t});\n'


def slide(sel: str, t: float, dx: int, dur: float = 0.7, ease: str = "power3.out") -> str:
    return f'tl.fromTo("{sel}", {{ x: {dx}, opacity: 1 }}, {{ x: 0, duration: {dur}, ease: "{ease}" }}, {t});\n'


def hide(sel: str) -> str:
    return f'tl.set("{sel}", {{ opacity: 0 }}, 0);\n'


def type_in(sel: str, t: float, per: float = 0.04) -> str:
    return (f'tl.fromTo("{sel}", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01 }}, {t});\n'
            f'tl.fromTo("{sel} .ch", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.01, stagger: {per} }}, {t});\n')


def slam(sel: str, t: float, scale: float = 2.2) -> str:
    return (f'tl.fromTo("{sel}", {{ opacity: 0, scale: {scale} }}, {{ opacity: 1, scale: 1, duration: 0.16, ease: "power4.in" }}, {t});\n'
            f'tl.to("{sel}", {{ keyframes: [{{ x: -7 }}, {{ x: 6 }}, {{ x: -3 }}, {{ x: 0 }}], duration: 0.12 }}, {round(t + 0.16, 3)});\n')


def wipe(sel: str, t: float, dur: float = 0.8, ease: str = "power1.inOut") -> str:
    return f'tl.fromTo("{sel}", {{ clipPath: "inset(0 100% 0 0)" }}, {{ clipPath: "inset(0 0% 0 0)", duration: {dur}, ease: "{ease}" }}, {t});\n'


def shake(sel: str, t: float, amp: int = 12) -> str:
    return (f'tl.to("{sel}", {{ keyframes: [{{ x: -{amp}, y: {amp // 2} }}, {{ x: {amp}, y: -{amp // 2} }}, {{ x: -{amp // 2}, y: {amp // 3} }}, '
            f'{{ x: 0, y: 0 }}], duration: 0.28 }}, {t});\n')


def bob(sel: str, t: float, n: int = 6, amp: int = 12, dur: float = 1.4) -> str:
    frames = ", ".join(f"{{ y: {-amp if k % 2 == 0 else 0} }}" for k in range(n * 2))
    return f'tl.to("{sel}", {{ keyframes: [{frames}], duration: {dur}, ease: "none" }}, {t});\n'


def count(sel: str, t: float, a: float, b: float, dur: float, var: str) -> str:
    return (f'const {var} = {{ v: {a} }};\n'
            f'tl.fromTo({var}, {{ v: {a} }}, {{ v: {b}, duration: {dur}, ease: "power2.out", '
            f'onUpdate: () => {{ document.querySelector("{sel}").textContent = Math.round({var}.v); }} }}, {t});\n')




def total() -> float:
    """Video length in seconds including the end hold (use this, not the TOTAL name, inside build.py)."""
    return TOTAL


def at(scene: str, n: int, i: int = 0, nudge: float = 0.0) -> float:
    """Absolute video time of word i in phrase n (for sound cues)."""
    return SCENES[scene]["start"] + ph(scene, n, i, nudge)


# ---------------------------------------------------------------- scene shell

def base_css() -> str:
    return f"""
#root {{ position: absolute; inset: 0; overflow: hidden; background: {PAPER}; }}
.bg {{ position: absolute; inset: 0; background: url(assets/tex/paper-light.jpg) center / cover; }}
.cam, .lay {{ position: absolute; inset: 0; }}
.abs {{ position: absolute; }}
.cut {{ position: absolute; display: block; height: auto; filter: drop-shadow(0 10px 14px rgba(40,30,15,.35)); }}
.strip {{ box-shadow: 0 8px 18px rgba(0,0,0,.3); }}
.lbl {{ display: inline-block; font-family: 'Playfair Display', serif; font-weight: 900; line-height: 1; padding: 12px 20px 9px; white-space: nowrap;
  box-shadow: 0 6px 14px rgba(0,0,0,.25); clip-path: polygon(0 5%, 3% 0, 35% 4%, 70% 0, 100% 3%, 99% 55%, 100% 97%, 65% 100%, 30% 96%, 4% 100%, 0 94%, 1% 45%); }}
.lbl.paper {{ background: {CREAM}; color: {INK}; }}
.lbl.yellow {{ background: {YELLOW}; color: {INK}; }}
.lbl.red {{ background: {RED}; color: #fff; }}
.cut.smoke {{ filter: grayscale(1) brightness(.62) drop-shadow(0 10px 14px rgba(40,30,15,.35)); }}
.lbl.dark {{ background: {INK}; color: {CREAM}; font-family: 'Inter', sans-serif; letter-spacing: .06em; }}
.stamp {{ display: inline-block; border: 9px solid; font-family: 'Archivo Black', sans-serif; text-transform: uppercase; line-height: 1;
  padding: 14px 22px 9px; letter-spacing: .04em; mix-blend-mode: multiply; opacity: .92; white-space: nowrap; background: rgba(243,238,224,.55); }}
.big {{ font-family: 'League Gothic', 'Oswald', sans-serif; color: {INK}; line-height: .85; font-variant-numeric: tabular-nums; }}
.ch {{ display: inline-block; }}
"""


UI_RE = re.compile(r'<div id="[^"]+" class="abs ui"[^>]*><div[^>]*>.*?</div></div>', re.S)


def scene(p: str, back: str, mid: str, front: str, js: str, drift: tuple = (-18, -45, -90), push: float = 1.06) -> str:
    dur = SCENES[p]["dur"]
    ui = "".join(UI_RE.findall(back + mid + front))
    back, mid, front = (UI_RE.sub("", x) for x in (back, mid, front))
    entry = ("" if p == TIMING["scenes"][0]["id"] else
             f'tl.fromTo("#{p}-cam", {{ scale: 1.25, filter: "blur(14px)" }}, {{ scale: 1, filter: "blur(0px)", duration: 0.35, ease: "power3.out" }}, 0);\n')
    push_js = (f'tl.fromTo("#{p}-push", {{ scale: 1 }}, {{ scale: {push}, duration: {dur}, ease: "none" }}, 0);' if push != 1.0 else "")
    par = "".join(f'tl.fromTo("#{p}-{n}", {{ x: 0 }}, {{ x: {d}, duration: {dur}, ease: "none" }}, 0);\n'
                  for n, d in zip(("back", "mid", "front"), drift))
    return fill(f"""<template>
  <style>
{base_css()}
  </style>
  <div id="root" data-composition-id="<<p>>" data-width="{W}" data-height="{H}">
    <div class="bg"></div>
    <div id="<<p>>-cam" class="cam" style="top:{SHIFT}px;bottom:-{SHIFT}px" data-layout-allow-overflow data-layout-allow-overlap>
      <div id="<<p>>-push" class="cam" data-layout-allow-overflow data-layout-allow-overlap>
        <div id="<<p>>-back" class="lay" data-layout-allow-overflow data-layout-allow-overlap>{back}</div>
        <div id="<<p>>-mid" class="lay" data-layout-allow-overflow data-layout-allow-overlap>{mid}</div>
        <div id="<<p>>-front" class="lay" data-layout-allow-overflow data-layout-allow-overlap>{front}</div>
      </div>
      <div id="<<p>>-ui" class="lay" data-layout-allow-overlap>{ui}</div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{entry}{push_js}
{par}{js}
    window.__timelines["<<p>>"] = tl;
  </script>
</template>
""", p=p)



def lawn(id_: str, y: int = 860, z: int = 2) -> str:
    return (f'<div id="{id_}" class="abs" style="left:-160px;top:{y}px;width:1400px;height:{1960 - y}px;z-index:{z};background:#7d9a55;'
            f'clip-path:polygon(0 6%, 12% 2%, 30% 5%, 50% 0, 70% 4%, 88% 1%, 100% 5%, 100% 100%, 0 100%)"></div>')

def drops(p: str, n: int, x0: int, y0: int) -> str:
    return "".join(f'<div id="{p}-dr{i}" class="abs" style="left:{x0 + i * 95}px;top:{y0}px;width:20px;height:30px;z-index:9;'
                   f'border-radius:50% 50% 50% 50% / 60% 60% 40% 40%;background:#4f8fb8"></div>' for i in range(n))


def steam(p: str, xs: list, y: int) -> str:
    return "".join(f'<div id="{p}-sm{i}" class="abs" style="left:{x}px;top:{y}px;width:70px;height:170px;z-index:8;border-radius:50%;'
                   f'background:radial-gradient(ellipse, rgba(255,255,255,.8), rgba(255,255,255,0) 70%)"></div>' for i, x in enumerate(xs))


def steam_js(p: str, n: int, t: float, dur: float = 2.6) -> str:
    return "".join(f'tl.fromTo("#{p}-sm{i}", {{ y: 40, opacity: 0 }}, {{ keyframes: [{{ y: 0, opacity: .9 }}, {{ y: -150, opacity: 0 }}], duration: {dur}, ease: "none" }}, {round(t + i * 0.3, 3)});\n'
                   for i in range(n))




# ---------------------------------------------------------------- scenery

def sky(id_: str, color: str = "#a9cfdc") -> str:
    return f'<div id="{id_}" class="abs" style="left:-160px;top:-260px;width:1400px;height:1500px;z-index:0;background:{color}"></div>'


def fences(p: str, y: int = 760) -> str:
    return "".join(cut(f"{p}-fn{i}", "fence", -120 + i * 470, y, 520, 1) for i in range(3))


def deck(id_: str, x: int, y: int, w: int, h: int, z: int = 2) -> str:
    return (f'<div id="{id_}" class="abs strip" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};'
            f'background:repeating-linear-gradient(0deg,#9a6a3e 0 46px,#6e4826 46px 52px);'
            f'clip-path:polygon(0 3%, 30% 0, 62% 2%, 100% 0, 100% 100%, 0 100%)"></div>')


FLAME = ("M50 0 C58 28 96 48 92 84 C90 110 72 126 50 126 C28 126 10 110 8 84 C6 60 30 52 34 30 C40 40 44 44 46 46 C48 30 50 16 50 0 Z")


def flames(p: str, xs: list, y: int, size: int = 120) -> str:
    return "".join(f'<svg id="{p}-fl{i}" class="abs" style="left:{x}px;top:{y}px;z-index:7;overflow:visible" width="{size}" height="{int(size * 1.26)}" '
                   f'viewBox="0 0 100 126"><path d="{FLAME}" fill="#e8461c"/><path d="{FLAME}" fill="#f7a21b" transform="translate(20 38) scale(.6)"/>'
                   f'<path d="{FLAME}" fill="#ffe27a" transform="translate(33 72) scale(.34)"/></svg>' for i, x in enumerate(xs))


def flames_js(p: str, n: int, t: float, scale: float = 1.0, dur: float = 1.2) -> str:
    return "".join(f'tl.fromTo("#{p}-fl{i}", {{ scale: 0, opacity: 1, transformOrigin: "50% 100%" }}, '
                   f'{{ keyframes: [{{ scale: {scale}, duration: 0.25 }}, {{ scale: {scale * 0.75}, duration: 0.2 }}, {{ scale: {scale * 1.1}, duration: 0.2 }}, '
                   f'{{ scale: {scale * 0.85}, duration: {dur - 0.65} }}] }}, {round(t + i * 0.06, 3)});\n' for i in range(n))


def smoke(p: str, spots: list) -> str:
    return "".join(cut(f"{p}-sk{i}", "cloud_cream", x, y, w, 9).replace('class="cut"', 'class="cut smoke"')
                   for i, (x, y, w) in enumerate(spots))


def smoke_js(p: str, n: int, t: float, step: float = 0.18) -> str:
    return "".join(f'tl.fromTo("#{p}-sk{i}", {{ scale: 0.2, y: 260, opacity: 0, transformOrigin: "50% 100%" }}, '
                   f'{{ scale: 1, y: 0, opacity: 0.95, duration: 1.1, ease: "power2.out" }}, {round(t + i * step, 3)});\n' for i in range(n))


def ring(p: str, n: int, cx: int, cy: int, r: int, color: str | None = None) -> str:
    color = color or RED
    return "".join(f'<div id="{p}-rg{i}" class="abs" style="left:{cx - r}px;top:{cy - r}px;width:{2 * r}px;height:{2 * r}px;z-index:8;'
                   f'border-radius:50%;border:10px solid {color}"></div>' for i in range(n))


def ring_js(p: str, n: int, t: float, every: float = 0.35, reps: int = 2) -> str:
    out = ""
    for k in range(reps):
        for i in range(n):
            out += (f'tl.fromTo("#{p}-rg{i}", {{ scale: 0.3, opacity: 1 }}, {{ scale: 1.6, opacity: 0, duration: 0.6, ease: "power1.out", immediateRender: false }}, '
                    f'{round(t + (k * n + i) * every, 3)});\n')
    return hide(",".join(f"#{p}-rg{i}" for i in range(n))) + out


def grate(id_: str, x: int, y: int, w: int, h: int, z: int = 4, bar: int = 30, gap: int = 26, gap_color: str = "#0d0c0b") -> str:
    return (f'<div id="{id_}" class="abs" style="left:{x}px;top:{y}px;width:{w}px;height:{h}px;z-index:{z};border-radius:22px;'
            f'border:16px solid #171615;box-shadow:0 18px 30px rgba(0,0,0,.4);'
            f'background:repeating-linear-gradient(90deg,#3b3936 0,#57534e {bar // 2}px,#2a2826 {bar}px,{gap_color} {bar}px {bar + gap}px)"></div>')


def wobble(sel: str, t: float, dur: float, amp: float = 3) -> str:
    return (f'tl.to("{sel}", {{ keyframes: [{{ rotation: -{amp} }}, {{ rotation: {amp} }}, {{ rotation: -{amp} }}, {{ rotation: {amp} }}, {{ rotation: 0 }}], '
            f'duration: {dur}, transformOrigin: "50% 100%" }}, {t});\n')



# ---------------------------------------------------------------- captions

def _norm(word: str) -> str:
    return re.sub(r"[^\w$%'-]", "", word.upper())


def caption_words(caption_text: dict, no_caption: set) -> list[dict]:
    """Script words (with caption_text swaps, e.g. "twelve" -> "12") on whisper timings; spread by length when counts differ."""
    out = []
    for p in TIMING["phrases"]:
        if p["scene"] in no_caption:
            continue
        text = p["text"]
        for a, b in caption_text.items():
            text = text.replace(a, b)
        script = re.sub(r"\s+", " ", text).strip().split(" ")
        ws = p["words"]
        if len(script) == len(ws):
            times = [(w["start"], w["end"]) for w in ws]
        else:
            t0, t1 = ws[0]["start"], ws[-1]["end"]
            weights = [len(s) + 2 for s in script]
            acc, times = 0, []
            for wgt in weights:
                a = t0 + (t1 - t0) * acc / sum(weights)
                acc += wgt
                times.append((round(a, 3), round(t0 + (t1 - t0) * acc / sum(weights), 3)))
        for t, (s, e) in zip(script, times):
            out.append({"text": t.upper(), "start": s, "end": e, "n": p["n"]})
    return out


def caption_groups(caption_text: dict, no_caption: set) -> list[dict]:
    words = caption_words(caption_text, no_caption)
    groups, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        if len(cur) == 3 or w["text"][-1] in ".,?!" or nxt is None or nxt["n"] != w["n"] or nxt["start"] - w["end"] >= 0.2:
            groups.append(cur)
            cur = []
    out = []
    for g, ws in enumerate(groups):
        start = max(0.15, ws[0]["start"] - 0.04)
        nstart = groups[g + 1][0]["start"] - 0.04 if g + 1 < len(groups) else TOTAL
        out.append({"words": ws, "start": round(start, 3), "end": round(min(nstart, ws[-1]["end"] + 0.45), 3)})
    return out


def captions(key_words: set, red_words: set, caption_text: dict, no_caption: set) -> str:
    """Bold word captions, 3 words at a time. Numbers and key_words get a yellow box, red_words a red one."""
    key, red = {_norm(w) for w in key_words}, {_norm(w) for w in red_words}

    def emphasis(text: str) -> str:
        n = _norm(text)
        return "red" if n in red else "hl" if (re.search(r"\d", n) or n in key) else ""

    items, js = "", ""
    for i, g in enumerate(caption_groups(caption_text, no_caption)):
        spans = ""
        for j, w in enumerate(g["words"]):
            e = emphasis(w["text"])
            spans += f'<span id="cap{i}-{j}" class="w {e}">{w["text"]}</span> '
            if e:
                js += (f'tl.fromTo("#cap{i}-{j}", {{ scale: 1.5, rotation: -5 }}, {{ scale: 1, rotation: -2, duration: 0.18, ease: "back.out(2.2)" }}, '
                       f'{round(max(g["start"], w["start"] - 0.02), 3)});\n')
        items += (f'<div id="cap{i}" class="cap clip" data-start="{g["start"]}" data-duration="{round(g["end"] - g["start"], 3)}" '
                  f'data-track-index="1"><div id="cap{i}-in" class="in">{spans.strip()}</div></div>\n')
        js += f'tl.fromTo("#cap{i}-in", {{ y: 14, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.12, ease: "power2.out" }}, {g["start"]});\n'
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; }}
    .cap {{ position: absolute; left: 0; width: {W}px; top: {CAPTION_TOP}px; text-align: center; overflow: visible; }}
    .cap .in {{ display: inline-block; }}
    .w {{ display: inline-block; font: 900 56px 'Inter', sans-serif; letter-spacing: .01em; color: #fff;
      -webkit-text-stroke: 11px {INK}; paint-order: stroke fill; text-shadow: 0 5px 0 rgba(0,0,0,.3); margin: 0 3px; }}
    .w.hl, .w.red {{ -webkit-text-stroke: 0; text-shadow: none; padding: 6px 14px 2px; font-size: 64px; box-shadow: 0 5px 0 rgba(0,0,0,.28); }}
    .w.hl {{ background: {YELLOW}; color: {INK}; }}
    .w.red {{ background: {RED}; color: #fff; }}
  </style>
  <div id="root" data-composition-id="captions" data-width="{W}" data-height="{H}">
{items}  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}    window.__timelines["captions"] = tl;
  </script>
</template>
"""


def overlay() -> str:
    """Moving film grain and a soft vignette over everything."""
    js = (f'const grain = document.querySelector("#ov-grain"); const clock = {{ t: 0 }};\n'
          f'tl.fromTo(clock, {{ t: 0 }}, {{ t: {TOTAL}, duration: {TOTAL}, ease: "none", onUpdate: () => {{\n'
          f'  const k = Math.floor(clock.t * 12); const h = (n) => ((Math.sin(n * 127.1 + k * 311.7) * 43758.5453) % 1 + 1) % 1;\n'
          f'  grain.style.transform = `translate(${{Math.round(h(1) * 100 - 50)}}px, ${{Math.round(h(2) * 100 - 50)}}px)`; }} }}, 0);\n')
    return f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; pointer-events: none; }}
    #ov-grain {{ position: absolute; inset: -60px; background: url(assets/tex/grain.png); opacity: .1; mix-blend-mode: overlay; }}
    #ov-vig {{ position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 58%, rgba(40,28,12,.32) 100%); }}
  </style>
  <div id="root" data-composition-id="overlay" data-width="{W}" data-height="{H}">
    <div id="ov-grain" data-layout-ignore></div>
    <div id="ov-vig" data-layout-ignore></div>
  </div>
  <script>
    const tl = gsap.timeline({{ paused: true }});
{js}    window.__timelines["overlay"] = tl;
  </script>
</template>
"""


# ---------------------------------------------------------------- assembly

_DUR: dict = {}


def sound_length(name: str) -> float:
    if name not in _DUR:
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              str(ROOT / "assets" / "sfx" / f"{name}.mp3")], capture_output=True, text=True)
        _DUR[name] = float(out.stdout.strip() or 0.5)
    return _DUR[name]


def index(cues: list) -> str:
    hosts = ""
    for sc in TIMING["scenes"]:
        hosts += (f'      <div id="{sc["id"]}" data-composition-id="{sc["id"]}" data-composition-src="compositions/{sc["id"]}.html" '
                  f'data-start="{sc["start"]}" data-duration="{sc["dur"]}" data-track-index="1" data-track-kind="graphics" '
                  f'data-width="{W}" data-height="{H}" style="z-index:1"></div>\n')
    hosts += (f'      <div id="overlay" data-composition-id="overlay" data-composition-src="compositions/overlay.html" data-start="0" '
              f'data-duration="{TOTAL}" data-track-index="2" data-track-kind="graphics" data-width="{W}" data-height="{H}" style="z-index:5"></div>\n'
              f'      <div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" '
              f'data-duration="{TOTAL}" data-track-index="3" data-track-kind="captions" data-width="{W}" data-height="{H}" style="z-index:6"></div>\n')
    audio = f'      <audio id="vo" class="clip" src="assets/vo/voice.wav" data-start="0" data-duration="{TOTAL}" data-track-index="4" data-volume="1"></audio>\n'
    lane_end: list = []
    for k, (f, t, v) in enumerate(sorted(cues, key=lambda c: c[1])):
        d = min(sound_length(f), round(TOTAL - t, 3))
        if d <= 0.05:
            continue
        lane = next((i for i, e in enumerate(lane_end) if e <= t), len(lane_end))
        if lane == len(lane_end):
            lane_end.append(0.0)
        lane_end[lane] = t + d
        audio += (f'      <audio id="sfx{k}" class="clip" src="assets/sfx/{f}.mp3" data-start="{t}" data-duration="{round(d, 3)}" '
                  f'data-track-index="{5 + lane}" data-volume="{v}"></audio>\n')
    return f"""<!doctype html>
<html lang="en" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={W}, height={H}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {W}px; height: {H}px; overflow: hidden; background: {PAPER}; }}
      #root {{ position: relative; width: 100%; height: 100%; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="{W}" data-height="{H}">
{hosts}{audio}    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
    </script>
  </body>
</html>
"""


def build(builders: list, sfx=None, key_words: set = frozenset(), red_words: set = frozenset(),
          caption_text: dict | None = None, no_caption: set = frozenset()) -> None:
    """Write compositions/*.html and index.html. builders: [(scene_id, fn)] in script order.
    sfx: function returning [(sound, absolute_time, volume)]. no_caption: scene ids without captions (end cards)."""
    ids = [s["id"] for s in TIMING["scenes"]]
    names = [n for n, _ in builders]
    if names != ids:
        raise SystemExit(f"BUILDERS {names} must match the scenes in script.txt, in order: {ids}")
    (ROOT / "compositions").mkdir(exist_ok=True)
    html = ""
    for name, fn in builders:
        out = fn()
        html += out
        (ROOT / "compositions" / f"{name}.html").write_text(out)
    caps = captions(set(key_words), set(red_words), caption_text or {}, set(no_caption))
    (ROOT / "compositions" / "captions.html").write_text(caps)
    (ROOT / "compositions" / "overlay.html").write_text(overlay())
    cues = [(f, round(max(0.0, t), 3), v) for f, t, v in (sfx() if sfx else [])]
    unknown = sorted({f for f, _, _ in cues if not (ROOT / "assets" / "sfx" / f"{f}.mp3").exists()})
    if unknown:
        raise SystemExit(f"unknown sounds {unknown}; available: {sorted(p.stem for p in (ROOT / 'assets' / 'sfx').glob('*.mp3'))}")
    (ROOT / "index.html").write_text(index(cues))
    missing = sorted({m for m in re.findall(r"assets/cut/([\w-]+)\.png", html) if not (ROOT / "assets" / "cut" / f"{m}.png").exists()})
    ids_used = re.findall(r'id="([^"]+)"', html)
    dupes = sorted({i for i in ids_used if i != "root" and ids_used.count(i) > 1})
    groups = caps.count('class="cap clip')
    print(f"built {len(builders)} scenes, {groups} caption groups, {len(cues)} sounds, {TOTAL}s")
    if missing:
        print(f"MISSING images in assets/cut: {missing}")
    if dupes:
        print(f"DUPLICATE element ids (each id must be unique across scenes): {dupes}")
