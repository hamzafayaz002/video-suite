"""Generate the studio's sound-effect pack from code (no samples, so no licence questions).

  vs sfx OUT_DIR        writes whoosh, whoosh-short, pop, click-soft, typing, sizzle, beep, boing, shutter,
                        riser, chime and ding as .mp3 (44.1 kHz)

There is deliberately no bass "boom": reviewers found it annoying. Add one per project only if asked.
"""

import argparse
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 44100
rng = np.random.default_rng(11)


def t(d: float) -> np.ndarray:
    return np.arange(int(d * SR)) / SR


def lowpass(x: np.ndarray, k: int) -> np.ndarray:
    return np.convolve(x, np.ones(k) / k, "same") if k > 1 else x


def env(d: float, attack: float, release: float) -> np.ndarray:
    tt = t(d)
    return np.minimum(1, tt / max(attack, 1e-4)) * np.minimum(1, (d - tt) / max(release, 1e-4))


def whoosh(d: float) -> np.ndarray:
    n = rng.standard_normal(int(d * SR))
    # sweep a moving low-pass: dull -> bright -> dull, plus slight stereo-free air
    out = np.zeros_like(n)
    seg = 512
    for i in range(0, len(n), seg):
        ph = i / len(n)
        k = int(2 + 40 * (1 - np.sin(np.pi * ph)))
        out[i:i + seg] = lowpass(n[max(0, i - 64):i + seg + 64], k)[64 if i else 0:][:len(n[i:i + seg])]
    return out * np.sin(np.pi * t(d) / d) ** 1.5


def pop() -> np.ndarray:
    tt = t(0.18)
    f = 900 * np.exp(-tt * 28) + 180
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30)
    click = np.zeros_like(tt); click[:60] = rng.standard_normal(60) * np.linspace(1, 0, 60)
    return tone + click * 0.4


def click_soft() -> np.ndarray:
    x = np.zeros(int(0.12 * SR)); k = rng.standard_normal(500) * np.exp(-np.arange(500) / 70)
    x[:500] = lowpass(k, 3)
    return x


def typing() -> np.ndarray:
    x = np.zeros(int(1.4 * SR)); pos = 0.02
    while pos < 1.3:
        i = int(pos * SR); k = rng.standard_normal(400) * np.exp(-np.arange(400) / 45) * rng.uniform(0.5, 1)
        x[i:i + 400] += lowpass(k, 2); pos += rng.uniform(0.06, 0.14)
    return x


def sizzle() -> np.ndarray:
    d = 2.0; n = rng.standard_normal(int(d * SR)); n = n - lowpass(n, 6)
    pops = (rng.random(n.size) > 0.9993) * rng.standard_normal(n.size) * 6
    return (n * (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t(d))) + np.convolve(pops, np.exp(-np.arange(200) / 30), "same")) * env(d, 0.12, 0.3)


def beep() -> np.ndarray:
    one = np.concatenate([np.sign(np.sin(2 * np.pi * 3100 * t(0.32))) * 0.5, np.zeros(int(0.22 * SR))])
    return np.concatenate([one] * 3)


def boing() -> np.ndarray:
    tt = t(0.6); f = 220 + 380 * np.exp(-tt * 6)
    return np.sin(2 * np.pi * np.cumsum(f * (1 + 0.15 * np.sin(2 * np.pi * 18 * tt))) / SR) * np.exp(-tt * 4.5)


def shutter() -> np.ndarray:
    c = np.zeros(int(0.3 * SR)); k = rng.standard_normal(600) * np.exp(-np.arange(600) / 90)
    c[:600] += k; c[5000:5600] += k * 0.8
    return c


def riser() -> np.ndarray:
    d = 1.5; tt = t(d); f = 200 * 2 ** (tt / d * 2.5)
    tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    return (tone + lowpass(rng.standard_normal(tt.size), 8) * (tt / d)) * (tt / d) ** 2


def bell(freqs: list[float], d: float) -> np.ndarray:
    tt = t(d)
    return sum(np.sin(2 * np.pi * f * tt) * np.exp(-tt * (3 + i)) / (i + 1) for i, f in enumerate(freqs))


def chime() -> np.ndarray:
    a = bell([1046.5, 2093, 3140], 0.9); b = bell([1568, 3136, 4704], 1.2)
    out = np.zeros(int(1.4 * SR)); out[:a.size] += a; out[int(0.16 * SR):int(0.16 * SR) + b.size] += b
    return out


SOUNDS = {
    "whoosh": lambda: whoosh(0.6), "whoosh-short": lambda: whoosh(0.35), "pop": pop, "click-soft": click_soft,
    "typing": typing, "sizzle": sizzle, "beep": beep, "boing": boing, "shutter": shutter, "riser": riser,
    "chime": chime, "ding": lambda: bell([1760, 3520], 1.0),
}


def write(name: str, x: np.ndarray, out_dir: Path) -> None:
    x = np.clip(x / max(1e-9, np.abs(x).max()) * 0.8, -1, 1)
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp) / f"{name}.wav"
        with wave.open(str(w), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes((x * 32767).astype("<i2").tobytes())
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(w), "-ar", str(SR), "-b:a", "160k",
                        str(out_dir / f"{name}.mp3")], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out_dir", type=Path)
    a = p.parse_args()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    for name, make in SOUNDS.items():
        write(name, make(), a.out_dir)
    print(f"{len(SOUNDS)} sounds -> {a.out_dir}")


if __name__ == "__main__":
    main()
