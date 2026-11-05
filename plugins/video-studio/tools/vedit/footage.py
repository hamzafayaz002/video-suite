"""Clean up raw footage: find the bad parts, plan the cut, render it vertical with captions.

  vs footage scan IN... [-o scan.json]           black, frozen, blurry and silent stretches + scene cuts, per clip
  vs footage words IN... [-o words.json]         word timings (whisper) for each clip
  vs footage plan scan.json [--words words.json] [-o edl.json] [--keep-silence 0.25] [--no-fillers]
        keep-list (EDL) without bad stretches, long pauses trimmed, "um/uh" removed and false starts
        (a sentence restarted with the same first words) dropped. Edit edl.json by hand if needed.
  vs footage cut edl.json OUT.mp4 [--frame crop|blur|keep]    render the EDL, 1080x1920 30 fps by default
  vs footage captions IN.mp4 OUT.mp4 [--words N]  burn bold word captions (N words per line, default 3)

EDL: {"segments": [{"file": "a.mp4", "start": 1.2, "end": 4.8}, ...]} played in order.
"""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

W, H, FPS = 1080, 1920, 30
FILLERS = {"um", "uh", "erm", "uhm", "hmm", "ah"}


def ff(args: list[str]) -> str:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr


def duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def has_audio(path: Path) -> bool:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return bool(out.strip())


def intervals(log: str, start_key: str, end_key: str) -> list[list[float]]:
    starts = [float(x) for x in re.findall(start_key + r"[:=]\s*([\d.]+)", log)]
    ends = [float(x) for x in re.findall(end_key + r"[:=]\s*([\d.]+)", log)]
    return [[round(s, 3), round(e, 3)] for s, e in zip(starts, ends)]


def blur_runs(path: Path, total: float, fps: float = 2.0, rel: float = 0.25) -> list[list[float]]:
    """Stretches whose sharpness (Laplacian variance) falls below rel x the clip's median."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={fps},scale=320:-2,format=gray",
                        f"{tmp}/%05d.png"], check=True)
        scores = []
        for f in sorted(Path(tmp).glob("*.png")):
            a = np.asarray(Image.open(f), np.float32)
            lap = a[1:-1, 1:-1] * -4 + a[:-2, 1:-1] + a[2:, 1:-1] + a[1:-1, :-2] + a[1:-1, 2:]
            scores.append(float(lap.var()))
    if not scores:
        return []
    cut = np.median(scores) * rel
    runs, cur = [], None
    for k, s in enumerate(scores):
        t = k / fps
        if s < cut and cur is None:
            cur = t
        elif s >= cut and cur is not None:
            runs.append([round(cur, 2), round(t, 2)]); cur = None
    if cur is not None:
        runs.append([round(cur, 2), round(total, 2)])
    return [r for r in runs if r[1] - r[0] >= 0.5]


def scan(path: Path) -> dict:
    total = duration(path)
    log = ff(["-i", str(path), "-vf", "blackdetect=d=0.3:pix_th=0.10,freezedetect=n=-60dB:d=0.8,select='gt(scene,0.3)',showinfo",
              "-an", "-f", "null", "-"])
    rep = {"file": str(path), "duration": round(total, 3),
           "black": intervals(log, "black_start", "black_end"),
           "frozen": intervals(log, "freeze_start", "freeze_end"),
           "cuts": [round(float(x), 2) for x in re.findall(r"pts_time:([\d.]+)", log)],
           "blurry": blur_runs(path, total), "silence": []}
    if has_audio(path):
        alog = ff(["-i", str(path), "-af", "silencedetect=n=-35dB:d=0.6", "-vn", "-f", "null", "-"])
        rep["silence"] = intervals(alog, "silence_start", "silence_end")
    return rep


def subtract(span: list[float], bad: list[list[float]]) -> list[list[float]]:
    out = [span]
    for b0, b1 in sorted(bad):
        nxt = []
        for s, e in out:
            if b1 <= s or b0 >= e:
                nxt.append([s, e]); continue
            if b0 > s:
                nxt.append([s, b0])
            if b1 < e:
                nxt.append([b1, e])
        out = nxt
    return [[round(s, 3), round(e, 3)] for s, e in out if e - s >= 0.3]


def false_starts(words: list[dict]) -> list[list[float]]:
    """A sentence restarted with the same opening words (fillers ignored): drop the earlier attempt."""
    sents, cur = [], []
    for w in words:
        cur.append(w)
        if re.search(r"[.!?]$", w["text"]):
            sents.append(cur); cur = []
    if cur:
        sents.append(cur)
    norm = lambda s: [t for t in (re.sub(r"\W", "", w["text"].lower()) for w in s) if t and t not in FILLERS]
    out = []
    for a, b in zip(sents, sents[1:]):
        ka, kb = norm(a), norm(b)
        n = min(3, len(ka))
        if n >= 2 and kb[:n] == ka[:n]:
            out.append([a[0]["start"], b[0]["start"]])
    return out


def plan(scans: list[dict], words: dict, keep_silence: float, fillers: bool) -> dict:
    segs = []
    for rep in scans:
        bad = rep["black"] + rep["frozen"] + rep["blurry"]
        pad = keep_silence / 2
        bad += [[s + pad, e - pad] for s, e in rep["silence"] if e - s > keep_silence]
        ws = words.get(rep["file"], [])
        if fillers:
            bad += [[w["start"], w["end"]] for w in ws if re.sub(r"\W", "", w["text"].lower()) in FILLERS]
        bad += false_starts(ws)
        segs += [{"file": rep["file"], "start": s, "end": e} for s, e in subtract([0.0, rep["duration"]], bad)]
    kept = sum(s["end"] - s["start"] for s in segs)
    return {"segments": segs, "kept_seconds": round(kept, 2), "source_seconds": round(sum(r["duration"] for r in scans), 2)}


def frame_filter(mode: str) -> str:
    if mode == "blur":
        return (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20[bg];"
                f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    if mode == "crop":
        return f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    return f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2"


def cut(edl: dict, out: Path, mode: str) -> None:
    files = list(dict.fromkeys(s["file"] for s in edl["segments"]))
    inputs = sum((["-i", f] for f in files), [])
    chains, labels = [], ""
    for k, s in enumerate(edl["segments"]):
        i = files.index(s["file"])
        chains.append(f"[{i}:v]trim={s['start']}:{s['end']},setpts=PTS-STARTPTS,{frame_filter(mode)},fps={FPS},setsar=1[v{k}]")
        if has_audio(Path(s["file"])):
            chains.append(f"[{i}:a]atrim={s['start']}:{s['end']},asetpts=PTS-STARTPTS,aresample=48000,"
                          f"afade=t=in:d=0.02,afade=t=out:st={max(0, s['end'] - s['start'] - 0.03)}:d=0.03[a{k}]")
        else:
            chains.append(f"anullsrc=r=48000:cl=stereo,atrim=0:{s['end'] - s['start']}[a{k}]")
        labels += f"[v{k}][a{k}]"
    chains.append(f"{labels}concat=n={len(edl['segments'])}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs, "-filter_complex", ";".join(chains),
                    "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out)], check=True)


def transcribe_words(path: Path, model: str = "base") -> list[dict]:
    import os
    from faster_whisper import WhisperModel
    m = WhisperModel(model, device="cpu", compute_type="int8",
                     download_root=os.path.join(os.environ.get("VS_HOME", os.path.expanduser("~/.video-studio")), "models", "whisper"))
    segs, _ = m.transcribe(str(path), word_timestamps=True, vad_filter=False)
    return [{"text": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)} for s in segs for w in s.words]


def ass_time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def captions(src: Path, dst: Path, per: int) -> None:
    words = [w for w in transcribe_words(src) if w["text"]]
    head = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, "
            "StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            "Style: Cap,Arial Black,78,&H00FFFFFF,&H0000D7FF,&H00141414,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,60,60,520,1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    lines = []
    for g in range(0, len(words), per):
        grp = words[g:g + per]
        nxt = words[g + per]["start"] if g + per < len(words) else None
        for k, w in enumerate(grp):  # the spoken word turns yellow
            end = grp[k + 1]["start"] if k + 1 < len(grp) else w["end"] + 0.25
            if nxt is not None:
                end = min(end, nxt)
            txt = " ".join((r"{\c&H0019C4F2&}" + x["text"].upper() + r"{\c&H00FFFFFF&}") if j == k else x["text"].upper()
                           for j, x in enumerate(grp))
            lines.append(f"Dialogue: 0,{ass_time(w['start'])},{ass_time(end)},Cap,,0,0,0,,{txt}")
    with tempfile.NamedTemporaryFile("w", suffix=".ass", delete=False) as f:
        f.write(head + "\n".join(lines) + "\n")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-vf", f"ass={f.name}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", str(dst)], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan"); s.add_argument("inputs", type=Path, nargs="+"); s.add_argument("-o", type=Path, default=Path("scan.json"))
    s = sub.add_parser("words"); s.add_argument("inputs", type=Path, nargs="+"); s.add_argument("-o", type=Path, default=Path("words.json"))
    s.add_argument("--model", default="base")
    s = sub.add_parser("plan"); s.add_argument("scan", type=Path); s.add_argument("--words", type=Path)
    s.add_argument("-o", type=Path, default=Path("edl.json")); s.add_argument("--keep-silence", type=float, default=0.25)
    s.add_argument("--no-fillers", action="store_true")
    s = sub.add_parser("cut"); s.add_argument("edl", type=Path); s.add_argument("output", type=Path)
    s.add_argument("--frame", choices=["crop", "blur", "keep"], default="crop")
    s = sub.add_parser("captions"); s.add_argument("input", type=Path); s.add_argument("output", type=Path)
    s.add_argument("--words", type=int, default=3)
    a = p.parse_args()
    if a.cmd == "scan":
        reps = [scan(f) for f in a.inputs]
        a.o.write_text(json.dumps(reps, indent=1))
        for r in reps:
            print(f"{r['file']}: {r['duration']}s  black {len(r['black'])}  frozen {len(r['frozen'])}  blurry {len(r['blurry'])}  "
                  f"silences {len(r['silence'])}  cuts {len(r['cuts'])}")
    elif a.cmd == "words":
        out = {str(f): transcribe_words(f, a.model) for f in a.inputs}
        a.o.write_text(json.dumps(out, indent=1))
        print(f"{sum(len(v) for v in out.values())} words -> {a.o}")
    elif a.cmd == "plan":
        words = json.loads(a.words.read_text()) if a.words else {}
        edl = plan(json.loads(a.scan.read_text()), words, a.keep_silence, not a.no_fillers)
        a.o.write_text(json.dumps(edl, indent=1))
        print(f"keep {len(edl['segments'])} segments, {edl['kept_seconds']}s of {edl['source_seconds']}s -> {a.o}")
    elif a.cmd == "cut":
        cut(json.loads(a.edl.read_text()), a.output, a.frame)
        print(a.output)
    elif a.cmd == "captions":
        captions(a.input, a.output, a.words)
        print(a.output)


if __name__ == "__main__":
    main()
