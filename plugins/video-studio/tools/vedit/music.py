"""Generate an original music bed with MusicGen and write a mix spec for it.

  vs music PROJECT --seconds 36 [--prompt "playful ukulele, claps, 112 bpm, no vocals"] [--seed 7]

Writes PROJECT/assets/bgm/bed.wav (the length asked, faded out) and PROJECT/bgm.json for
  vs mix RENDER.mp4 PROJECT/bgm.json OUT.mp4
LICENCE: facebook/musicgen-small weights are CC-BY-NC 4.0, so generated music is for non-commercial videos.
For client ads use a licensed track (put it in assets/bgm and point bgm.json at it) or add music in the app.
"""

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def rms_db(x: np.ndarray, sr: int, win: float = 2.0) -> list[float]:
    n = int(sr * win)
    return [20 * np.log10(np.sqrt(np.mean(x[i:i + n] ** 2)) + 1e-9) for i in range(0, len(x) - n + 1, n)]


def tame(x: np.ndarray, sr: int) -> np.ndarray:
    """MusicGen sometimes runs away into a loud tail: cut at the first 2 s window 8 dB over the median."""
    r = rms_db(x, sr)
    if not r:
        return x
    med = float(np.median(r))
    for k, v in enumerate(r):
        if v > med + 8:
            return x[: k * 2 * sr]
    return x


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project", type=Path)
    p.add_argument("--seconds", type=float, required=True)
    p.add_argument("--prompt", default="light playful documentary underscore, pizzicato strings, marimba, soft bass, brushed drums, 100 bpm, no vocals")
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    import soundfile as sf
    import torch
    from transformers import AutoProcessor, MusicgenForConditionalGeneration

    print("note: MusicGen output is licensed for non-commercial use only (CC-BY-NC 4.0)", file=sys.stderr)
    torch.manual_seed(a.seed)
    torch.set_num_threads(max(1, (torch.get_num_threads() or 4)))
    proc = AutoProcessor.from_pretrained("facebook/musicgen-small")
    model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
    sr = model.config.audio_encoder.sampling_rate

    def gen(seconds: float, prompt_audio=None) -> np.ndarray:
        kw = dict(text=[a.prompt], padding=True, return_tensors="pt")
        if prompt_audio is not None:
            kw.update(audio=prompt_audio, sampling_rate=sr)
        t = time.time()
        with torch.no_grad():
            w = model.generate(**proc(**kw), do_sample=True, guidance_scale=3.0, max_new_tokens=int(seconds * 50))[0, 0].numpy()
        print(f"  {seconds:.0f}s of music in {time.time() - t:.0f}s", flush=True)
        return w

    want = a.seconds + 1.0
    bed = tame(gen(min(30.0, want)), sr)
    while len(bed) / sr < want:
        ctx = bed[-10 * sr:]
        nxt = gen(min(30.0, want - len(bed) / sr + 10.5), ctx)
        new = tame(nxt[len(ctx):], sr)  # continuation output starts with the prompt audio
        if len(new) < sr:
            break
        bed = np.concatenate([bed, new])
    bed = bed[: int(want * sr)]
    fade = int(min(2.5, len(bed) / sr / 4) * sr)
    bed[-fade:] *= np.linspace(1, 0, fade)
    out = a.project / "assets" / "bgm"
    out.mkdir(parents=True, exist_ok=True)
    sf.write(out / "bed.wav", bed, sr)
    spec = {"bed_volume": 0.3, "segments": [{"file": "assets/bgm/bed.wav", "from": 0, "to": round(len(bed) / sr, 2), "at": 0,
                                               "fade_in": 0.4, "fade_out": 0.05, "volume": 1.0}]}
    (a.project / "bgm.json").write_text(json.dumps(spec, indent=1))
    print(f"{len(bed) / sr:.1f}s -> {out / 'bed.wav'}, spec -> {a.project / 'bgm.json'}")


if __name__ == "__main__":
    main()
