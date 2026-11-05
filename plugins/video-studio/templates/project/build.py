"""Scenes for this video. Run `vs build .` after `vs voice .`; then `vs snapshot . --at 1,3,5` and `vs render . -o out.mp4`.

Replace the demo scenes below with the story's scenes. Rules that keep it working:
- BUILDERS must list one function per scene id of script.txt, in the same order.
- Give every element a unique id with a scene prefix (hk-, id-, ct-...). hide() everything that should enter
  later, then animate it in at a word time from ph(scene, line, word).
- Labels and stamps (class "abs ui") hold text inside ONE inner div; use <span>s for anything nested.
- Keep important things between y=200 and y=1300; captions sit at y=1420 and the app UI covers the bottom.
"""

from vedit import rig

rig.init(__file__, hold=1.0)  # palette={"RED": "#d2232a", ...} to use brand colours
from vedit.rig import *  # noqa: E402,F403  (after init, so TOTAL and the colours are current)


def hook() -> str:
    p = "hook"
    t_sun, t_zero = ph(p, 1, 3), ph(p, 2, 2)
    back = sky("hk-sky") + cut("hk-cl1", "cloud", 40, 260, 380) + cut("hk-cl2", "cloud", 620, 420, 340)
    mid = lawn("hk-lawn", 980)
    front = (cut("hk-sun", "sun", 290, 420, 500, 3)
             + label("hk-t", "A PAPER SUN.", 300, 300, 64, "yellow", -3)
             + stamp("hk-s", "0 ARTISTS", 520, 960, 70, RED, -8))
    js = (slide("#hk-cl1", 0, -500, 1.0) + slide("#hk-cl2", 0, 600, 1.0)
          + hide("#hk-sun") + f'tl.fromTo("#hk-sun", {{ scale: 0.2, rotation: -40, opacity: 1, transformOrigin: "50% 50%" }}, '
            f'{{ scale: 1, rotation: 0, duration: 0.8, ease: "back.out(1.6)" }}, {t_sun - 0.3});\n'
          + hide("#hk-t") + type_in("#hk-t", t_sun, 0.04)
          + hide("#hk-s") + slam("#hk-s", t_zero))
    return scene(p, back, mid, front, js)


def idea() -> str:
    p = "idea"
    t_code, t_word = ph(p, 3, 5), ph(p, 4, 3)
    front = (sky("id-sky", "#e8dcc4")
             + torn_strip("id-g", "grass", 40, 1000, 1000, 960, 3, 2)
             + "".join(cut(f"id-c{i}", "cloud", 80 + i * 330, 520 + (i % 2) * 120, 280, 4) for i in range(3))
             + label("id-l1", "BUILT FROM CODE", 60, 240, 60, "dark", 0)
             + f'<div id="id-num" class="abs ui" style="left:300px;top:700px;z-index:22"><div class="big" style="font-size:200px;'
               f'background:{YELLOW};padding:16px 30px 2px"><span id="id-n">0</span> MS</div></div>'
             + label("id-l2", "WORD-SYNCED", 560, 1080, 52, "yellow", 2))
    js = ("".join(hide(f"#id-c{i}") + pop(f"#id-c{i}", round(0.2 + i * 0.15, 3), 0.4, "50% 50%") for i in range(3))
          + hide("#id-l1") + type_in("#id-l1", t_code - 0.3, 0.03)
          + hide("#id-num") + pop("#id-num", t_word - 0.4, 0.3, "50% 50%") + count("#id-n", t_word - 0.3, 900, 0, 0.8, "idc")
          + hide("#id-l2") + slam("#id-l2", t_word + 0.3))
    return scene(p, "", "", front, js)


def cta() -> str:
    p = "cta"
    t_own, t_topic = ph(p, 5, 3), ph(p, 6, 3)
    front = (sky("ct-sky", "#9fd0e3") + cut("ct-sun", "sun", 640, 200, 320, 2) + lawn("ct-lawn", 1000)
             + label("ct-l1", "NOW MAKE YOUR OWN.", 60, 420, 66, "red", -2)
             + label("ct-l2", "JUST TYPE A TOPIC", 160, 700, 56, "paper", 2))
    js = (rise("#ct-sun", 0.1, 600, 0.6) + hide("#ct-l1") + slam("#ct-l1", t_own - 0.2)
          + hide("#ct-l2") + type_in("#ct-l2", t_topic - 0.3, 0.035) + bob("#ct-sun", 1.0, 4, 10, 2.0))
    return scene(p, "", "", front, js, push=1.04)


BUILDERS = [("hook", hook), ("idea", idea), ("cta", cta)]


def sfx() -> list:
    """(sound, absolute time, volume). Sounds: whoosh, whoosh-short, pop, click-soft, typing, sizzle, beep,
    boing, shutter, riser, chime, ding. No bass booms."""
    cues = [("whoosh-short", s["start"] - 0.1, 0.3) for s in TIMING["scenes"][1:]]
    cues += [("pop", at("hook", 1, 3, -0.3), 0.35), ("typing", at("hook", 1, 3), 0.2), ("pop", at("hook", 2, 2), 0.35),
             ("typing", at("idea", 3, 5, -0.3), 0.2), ("pop", at("idea", 4, 3, 0.3), 0.35), ("chime", at("cta", 5, 3, -0.2), 0.3)]
    return cues


if __name__ == "__main__":
    build(BUILDERS, sfx, key_words={"SUN", "CODE", "TOPIC"}, red_words={"ZERO"},
          caption_text={"zero": "0"})
