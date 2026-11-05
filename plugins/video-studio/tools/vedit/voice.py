"""Record a voiceover phrase by phrase and time every word.

  vs voice PROJECT [--voice af_heart] [--whisper base]

Reads PROJECT/script.txt, one phrase per line:   scene|speed|pause_after|text
  scene        id of the scene the phrase belongs to (lowercase word, e.g. hook, problem, cta)
  speed        1.0 = normal; 0.9 slows a punchline, 1.1 speeds a list
  pause_after  seconds of silence after the phrase (0.15 between list items, 0.5-0.8 before a reveal)
Lines starting with # are ignored.

Writes PROJECT/assets/vo/voice.wav, PROJECT/assets/vo/ph/NN.wav and PROJECT/timing.json:
  {"total": s, "scenes": [{id, vo_start, start, end, dur}], "phrases": [{n, scene, text, start, end, words: [{text, start, end}]}]}
Each scene starts where the previous one ends and ends 0.1 s before the next scene's first word.
Voices: af_heart (warm female, default), am_michael, am_adam, bf_emma, bm_george and the rest of Kokoro v1.0.
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000
LEAD = 0.15
VS_HOME = Path(os.environ.get("VS_HOME", Path.home() / ".video-studio"))


def read_script(path: Path) -> list[tuple[str, float, float, str]]:
    rows = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        scene, speed, pause, text = line.split("|", 3)
        rows.append((scene.strip(), float(speed), float(pause), text.strip()))
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("project", type=Path)
    p.add_argument("--voice", default="af_heart")
    p.add_argument("--whisper", default="base", help="tiny, base, small (bigger = better word timing, slower)")
    a = p.parse_args()

    from faster_whisper import WhisperModel
    from kokoro_onnx import Kokoro

    root = a.project
    rows = read_script(root / "script.txt")
    kdir = VS_HOME / "models" / "kokoro"
    kokoro = Kokoro(str(kdir / "kokoro-v1.0.onnx"), str(kdir / "voices-v1.0.bin"))
    whisper = WhisperModel(a.whisper, device="cpu", compute_type="int8", download_root=str(VS_HOME / "models" / "whisper"))
    ph_dir = root / "assets" / "vo" / "ph"
    ph_dir.mkdir(parents=True, exist_ok=True)
    audio, t, phrases = [np.zeros(int(LEAD * SR), np.float32)], LEAD, []
    for n, (scene, speed, pause, text) in enumerate(rows, 1):
        samples, _ = kokoro.create(text, voice=a.voice, speed=speed, lang="en-us")
        nz = np.nonzero(np.abs(samples) > 0.01)[0]  # trim leading/trailing silence
        samples = samples[max(0, nz[0] - 600): nz[-1] + 1200].astype(np.float32)
        sf.write(ph_dir / f"{n:02d}.wav", samples, SR)
        segs, _ = whisper.transcribe(str(ph_dir / f"{n:02d}.wav"), word_timestamps=True, language="en")
        words = [{"text": w.word.strip(), "start": round(t + w.start, 3), "end": round(t + w.end, 3)} for s in segs for w in s.words]
        if not words:  # whisper heard nothing: spread the script words evenly so timing still works
            ws = text.split()
            words = [{"text": w, "start": round(t + i * len(samples) / SR / len(ws), 3),
                      "end": round(t + (i + 1) * len(samples) / SR / len(ws), 3)} for i, w in enumerate(ws)]
        dur = len(samples) / SR
        phrases.append({"n": n, "scene": scene, "text": text, "start": round(t, 3), "end": round(t + dur, 3), "words": words})
        audio += [samples, np.zeros(int(pause * SR), np.float32)]
        t += dur + pause
        print(f"{n:2d} {scene:10s} {dur:5.2f}s  {' '.join(w['text'] for w in words)}", flush=True)
    total = round(t, 2)
    sf.write(root / "assets" / "vo" / "voice.wav", np.concatenate(audio), SR)
    order = list(dict.fromkeys(ph["scene"] for ph in phrases))
    firsts = {s: next(ph["start"] for ph in phrases if ph["scene"] == s) for s in order}
    scenes, start = [], 0.0
    for i, s in enumerate(order):
        end = round(firsts[order[i + 1]] - 0.1, 3) if i + 1 < len(order) else total
        scenes.append({"id": s, "vo_start": firsts[s], "start": start, "end": end, "dur": round(end - start, 3)})
        start = end
    (root / "timing.json").write_text(json.dumps({"total": total, "scenes": scenes, "phrases": phrases}, indent=1))
    print(f"total {total}s, {len(scenes)} scenes -> {root / 'timing.json'}")


if __name__ == "__main__":
    main()
