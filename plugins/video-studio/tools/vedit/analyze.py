"""Break a reference video down so its style can be studied.

Outputs into OUT_DIR:
  shots.json      cut times, shot lengths, pacing stats, video/audio info
  shots/NNN.jpg   one frame from the middle of every shot
  frames/NNN.jpg  a frame every --every seconds (catches motion inside a shot)
  sheet.jpg       contact sheet of the per-shot frames

Usage: python -m vedit.analyze IN OUT_DIR [--threshold 0.3] [--every 0.5]
"""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from vedit.ffmpeg import probe


def detect_cuts(src: Path, threshold: float) -> list[float]:
    """Timestamps (s) where FFmpeg's scene score exceeds threshold."""
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(src), "-vf", f"select='gt(scene,{threshold})',showinfo",
         "-an", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", proc.stderr)]


def grab(src: Path, t: float, dst: Path) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(src),
                    "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "3", str(dst)], check=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--threshold", type=float, default=0.3, help="scene-change sensitivity (lower = more cuts)")
    p.add_argument("--every", type=float, default=0.5, help="seconds between sampled frames")
    a = p.parse_args()

    info = probe(a.input)
    duration = float(info["format"]["duration"])
    video = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])

    for sub in ("shots", "frames"):
        shutil.rmtree(a.out_dir / sub, ignore_errors=True)
        (a.out_dir / sub).mkdir(parents=True)

    bounds = [0.0, *detect_cuts(a.input, a.threshold), duration]
    shots = []
    for i, (start, end) in enumerate(zip(bounds, bounds[1:]), 1):
        if end - start < 0.05:
            continue
        frame = a.out_dir / "shots" / f"{i:03}.jpg"
        grab(a.input, (start + end) / 2, frame)
        shots.append({"shot": i, "start": round(start, 3), "end": round(end, 3),
                      "length": round(end - start, 3), "frame": str(frame.relative_to(a.out_dir))})

    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a.input),
                    "-vf", f"fps=1/{a.every},scale=540:-2", "-q:v", "3",
                    str(a.out_dir / "frames" / "%03d.jpg")], check=True)

    cols = min(6, len(shots))
    rows = -(-len(shots) // cols)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-pattern_type", "glob",
                    "-i", str(a.out_dir / "shots" / "*.jpg"),
                    "-vf", f"scale=240:-2,tile={cols}x{rows}:padding=4", "-frames:v", "1",
                    str(a.out_dir / "sheet.jpg")], check=True)

    lengths = [s["length"] for s in shots]
    report = {
        "file": str(a.input),
        "duration": round(duration, 3),
        "resolution": f'{video["width"]}x{video["height"]}',
        "fps": video.get("r_frame_rate"),
        "has_audio": has_audio,
        "shot_count": len(shots),
        "avg_shot_length": round(sum(lengths) / len(lengths), 3),
        "min_shot_length": min(lengths),
        "max_shot_length": max(lengths),
        "cuts_per_minute": round(len(shots) / duration * 60, 1),
        "shots": shots,
    }
    (a.out_dir / "shots.json").write_text(json.dumps(report, indent=2))
    print(f"{len(shots)} shots, avg {report['avg_shot_length']}s, {report['cuts_per_minute']} cuts/min -> {a.out_dir}")


if __name__ == "__main__":
    main()
