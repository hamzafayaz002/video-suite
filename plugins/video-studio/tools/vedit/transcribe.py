"""Transcribe a video or audio file with Whisper (faster-whisper).

Writes word-level timestamps as JSON plus an .srt file next to the output path.
The JSON uses Remotion's Caption shape ({text, startMs, endMs, timestampMs, confidence})
so it can be dropped straight into studio/remotion/public/ as <video>.json.

Usage: python -m vedit.transcribe media/input/clip.mp4 [-m small] [-l en] [-o out.json]
"""

import argparse
import json
from pathlib import Path

from faster_whisper import WhisperModel


def _srt_time(seconds: float) -> str:
    ms = round(seconds * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def transcribe(path: Path, model_size: str = "small", language: str | None = None):
    model = WhisperModel(model_size, device="auto", compute_type="int8")
    segments, info = model.transcribe(str(path), language=language, word_timestamps=True, vad_filter=True)
    return list(segments), info


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("-m", "--model", default="small", help="tiny, base, small, medium, large-v3")
    parser.add_argument("-l", "--language", default=None, help="e.g. en; auto-detected if omitted")
    parser.add_argument("-o", "--output", type=Path, help="JSON output path (default: <input>.json)")
    args = parser.parse_args()

    segments, info = transcribe(args.input, args.model, args.language)

    captions = []
    for seg in segments:
        for w in seg.words or []:
            start_ms, end_ms = round(w.start * 1000), round(w.end * 1000)
            captions.append({
                "text": w.word,
                "startMs": start_ms,
                "endMs": end_ms,
                "timestampMs": (start_ms + end_ms) // 2,
                "confidence": round(w.probability, 3),
            })

    out = args.output or args.input.with_suffix(".json")
    out.write_text(json.dumps(captions, indent=2))

    srt = "\n".join(
        f"{i}\n{_srt_time(seg.start)} --> {_srt_time(seg.end)}\n{seg.text.strip()}\n"
        for i, seg in enumerate(segments, 1)
    )
    out.with_suffix(".srt").write_text(srt)

    print(f"language={info.language} words={len(captions)} -> {out}, {out.with_suffix('.srt')}")


if __name__ == "__main__":
    main()
