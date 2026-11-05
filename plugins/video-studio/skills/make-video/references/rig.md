# rig: the scene engine (vedit.rig)

build.py starts with:
```python
from vedit import rig
rig.init(__file__, hold=1.0)            # hold: seconds the end card stays; palette={"RED": "#c8102e"} for brand colours
from vedit.rig import *                 # helpers, colours, TIMING, SCENES, total()
```
and ends with `build(BUILDERS, sfx, key_words=..., red_words=..., caption_text=..., no_caption={"cta"})`.
`vs build PROJECT` runs it. The frame is 1080x1920; scene content is shifted down 130 px automatically.

## Timing
- `ph(scene, line, word=0, nudge=0.0)`: scene-local seconds of a word. `line` is the 1-based line number in
  script.txt (comments and blank lines not counted), `word` the 0-based word in that line as whisper heard it
  (index past the end clamps to the last word). Use it for every entrance: things appear ON the word.
- `at(scene, line, word, nudge)`: the same as absolute video time, for sound cues.
- Scenes run back to back; each ends 0.1 s before the next scene's first word. The last gets `hold` extra.
- Entrances 0.1-0.4 s before the word read as on time. Nothing should start before 0.1 s in a scene.

## Elements (return HTML strings; concatenate them)
| Helper | What |
|---|---|
| `cut(id, name, x, y, w, z=1)` | image assets/cut/NAME.png, width w (height auto), z order |
| `label(id, text, x, y, size=40, kind="paper", rot=-2)` | torn-paper text label. kinds: paper, yellow, red, dark |
| `stamp(id, text, x, y, size=56, color=RED, rot=-6)` | rubber stamp text (verdicts, numbers, punchlines) |
| `torn_strip(id, tex, x, y, w, h, seed, z=2)` | textured strip with a torn top edge (ground, layers, cutaways); tex = paper-light, kraft, asphalt, soil, gravel, grass, wood |
| `sky(id, color)` | full-bleed background colour block (z 0) |
| `lawn(id, y=860)` | green ground with a wavy top |
| `deck(id, x, y, w, h)` | wooden planks |
| `steam(p, xs, y)` / `smoke(p, spots)` / `flames(p, xs, y, size)` / `drops(p, n, x0, y0)` / `ring(p, n, cx, cy, r)` | effects with ids p-sm0.., p-sk0.., p-fl0.., p-dr0.., p-rg0.. (p = scene id) |
| `grate(id, x, y, w, h, z, bar, gap, gap_color)` | bars (grill grate, fence, prison, chart bars) |
| raw HTML | any `<div id=.. class="abs" style="left:..;top:..;width:..;height:..;z-index:..">` with CSS (shapes, panels, flyers) |
| big numbers | `<div id="x-num" class="abs ui" style="left:..;top:..;z-index:22"><div class="big" style="font-size:190px;background:{YELLOW};padding:16px 30px 2px"><span id="x-n">0</span> SQ IN</div></div>` + `count("#x-n", t, 0, 225, 0.8, "var1")` |

## Motion (return GSAP lines; concatenate)
| Helper | Use |
|---|---|
| `hide(sel)` | invisible at t=0. Call before every entrance below except rise/slide of always-visible scenery |
| `pop(sel, t, dur=0.5, origin="50% 100%")` | scale up from 0 with a bounce (people, objects) |
| `rise(sel, t, dy=500, dur=0.7)` / `slide(sel, t, dx, dur, ease)` | come in from below / the side |
| `type_in(sel, t, per=0.04)` | typewriter for label() text |
| `slam(sel, t, scale=2.2)` | stamp lands with a shake (punchlines, verdicts, prices) |
| `wipe(sel, t, dur)` | reveal left to right (coatings, bars, progress) |
| `shake(sel, t, amp)` / `wobble(sel, t, dur, amp)` / `bob(sel, t, n, amp, dur)` | life: impact, nervous, walking/bouncing |
| `count(sel, t, a, b, dur, var)` | number counting from a to b; var must be a unique JS name |
| `steam_js(p, n, t)` / `smoke_js(p, n, t)` / `flames_js(p, n, t, scale)` / `ring_js(p, n, t)` | animate the effects |
| raw GSAP | `f'tl.to("#id", {{ x: 600, scale: 0.75, duration: 1.2, ease: "power1.inOut" }}, {t});\n'` (double the braces in f-strings) |

`scene(p, back, mid, front, js, drift=(-18, -45, -90), push=1.06)` wraps it all: back/mid/front drift
sideways by those pixels over the scene (parallax) and the camera pushes in by `push`. Labels and stamps are
lifted onto a static layer automatically. For a zoom on one object animate `#<scene>-push` (scale, x, y) and
pass push=1.0. The first scene has no entry blur; the others zoom out of a blur.

## Rules that prevent broken frames
- Every id unique across the whole video: prefix with a short scene code (hk-, pr-, st-...). build() lists duplicates.
- A `class="abs ui"` element holds exactly one inner `<div>`; nest `<span style="display:block">` inside it,
  never more divs (the layer lifter cuts at the first `</div></div>`).
- Text width: label() and stamp() do not wrap. Roughly 0.6 x size px per character for labels, 0.75 x size
  for stamps; keep x + width under 1040.
- Full-width backgrounds bleed off frame (left:-140px; width:1360px) so parallax never shows an edge.
- Do not animate the same property of the same element twice at overlapping times (`vs check` warns).
- Use `total()` for the video length inside build.py.
- After `vs build`, take snapshots at a late moment of every scene and look at them before rendering.

## Sounds
sfx() returns `[(name, absolute_time, volume)]`. Available: whoosh, whoosh-short, pop, click-soft, typing,
sizzle, beep, boing, shutter, riser, chime, ding (in assets/sfx; add your own .mp3 there). Typical: a
whoosh-short 0.1 s before each scene change at 0.3, a pop per entrance at 0.3-0.35, typing under labels at 0.2,
one themed sound per scene, a chime on the end card. build() spreads overlapping sounds over audio tracks.

## Captions
Automatic from script.txt and the word timings: 3 words per line, numbers and `key_words` in yellow boxes,
`red_words` in red. `caption_text` maps spoken words to written ones ("twelve" -> "12").
`no_caption={"cta"}` drops captions from scenes whose text is already on screen (end cards).
