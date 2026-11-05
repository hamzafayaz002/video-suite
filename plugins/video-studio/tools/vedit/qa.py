"""Final check of a rendered video before it goes to the user.

  vs qa OUT.mp4 [--min 30 --max 40]

Checks: 1080x1920, ~30 fps, H.264 + AAC, duration in range, loudness near -14 LUFS, true peak under -1 dB,
no black or frozen stretches over 1 s, no silent stretches over 1.5 s (except the last 2.5 s), and writes OUT.qa.jpg (a contact sheet of
12 frames) to look at. Exit code 1 when a check fails.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(args: list[str]) -> str:
    return subprocess.run(args, capture_output=True, text=True).stderr


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--min", type=float, default=0)
    p.add_argument("--max", type=float, default=1e9)
    a = p.parse_args()
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(a.video)],
                                     capture_output=True, text=True, check=True).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur = float(info["format"]["duration"])
    num, den = (int(x) for x in v["r_frame_rate"].split("/"))
    fps = num / den
    loud = run(["ffmpeg", "-hide_banner", "-i", str(a.video), "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs = float(re.findall(r"I:\s+(-?[\d.]+) LUFS", loud)[-1]) if au else None
    peak = float(re.findall(r"Peak:\s+(-?[\d.]+) dBFS", loud)[-1]) if au else None
    vlog = run(["ffmpeg", "-hide_banner", "-i", str(a.video), "-vf", "blackdetect=d=1.0:pix_th=0.08,freezedetect=n=-60dB:d=1.0", "-an", "-f", "null", "-"])
    slog = run(["ffmpeg", "-hide_banner", "-i", str(a.video), "-af", "silencedetect=n=-45dB:d=1.5", "-vn", "-f", "null", "-"]) if au else ""
    gaps = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", slog) if float(x) < dur - 2.5]
    checks = [
        ("size 1080x1920", v["width"] == 1080 and v["height"] == 1920, f'{v["width"]}x{v["height"]}'),
        ("frame rate ~30", abs(fps - 30) < 0.5, f"{fps:.2f}"),
        ("codecs h264 + aac", v["codec_name"] == "h264" and au is not None and au["codec_name"] == "aac", f'{v["codec_name"]}/{au["codec_name"] if au else "none"}'),
        (f"duration {a.min:g}-{a.max:g}s", a.min <= dur <= a.max, f"{dur:.1f}s"),
        ("loudness -16..-13 LUFS", lufs is not None and -16 <= lufs <= -13, f"{lufs} LUFS"),
        ("true peak <= -1 dB", peak is not None and peak <= -0.9, f"{peak} dBFS"),
        ("no black stretch > 1s", "black_start" not in vlog, ",".join(re.findall(r"black_start:([\d.]+)", vlog)) or "none"),
        ("no frozen stretch > 1s", "freeze_start" not in vlog, ",".join(re.findall(r"freeze_start: ([\d.]+)", vlog)) or "none"),
        ("no silence > 1.5s (end card excepted)", not gaps, ",".join(f"{g:.1f}s" for g in gaps) or "none"),
    ]
    sheet = a.video.with_suffix(".qa.jpg")
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a.video), "-vf",
                    f"fps=12/{max(dur, 1):.3f},scale=270:-2,tile=6x2:padding=6", "-frames:v", "1", str(sheet)])
    ok = all(c[1] for c in checks)
    for name, good, detail in checks:
        print(f"  {'OK ' if good else '!! '}{name}  ({detail})")
    print(f"contact sheet: {sheet}")
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
