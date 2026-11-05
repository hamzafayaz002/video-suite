"""FFmpeg helpers for Reels.

  python -m vedit.ffmpeg probe  IN
  python -m vedit.ffmpeg cut    IN OUT --start 5 --end 20
  python -m vedit.ffmpeg reel   IN OUT [--blur]        # 1080x1920, 30fps, H.264/AAC
  python -m vedit.ffmpeg concat OUT IN1 IN2 ...         # inputs must share codec/size (run `reel` first)
  python -m vedit.ffmpeg subs   IN SRT OUT              # burn in subtitles
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

W, H, FPS = 1080, 1920, 30
ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]


def run(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def probe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(out)


def cut(src: Path, dst: Path, start: float, end: float) -> None:
    run(["-ss", str(start), "-to", str(end), "-i", str(src), *ENCODE, str(dst)])


def reel(src: Path, dst: Path, blur: bool = False) -> None:
    """Convert to vertical 9:16. Default crops the centre; --blur fits the whole frame over a blurred fill."""
    if blur:
        vf = (f"split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},boxblur=20[bg];"
              f"[b]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,fps={FPS}")
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}"
    run(["-i", str(src), "-filter_complex", vf, *ENCODE, str(dst)])


def concat(dst: Path, srcs: list[Path]) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.writelines(f"file '{p.resolve()}'\n" for p in srcs)
    run(["-f", "concat", "-safe", "0", "-i", f.name, "-c", "copy", str(dst)])


def subs(src: Path, srt: Path, dst: Path) -> None:
    style = "FontName=Arial,FontSize=14,Bold=1,Outline=2,Alignment=2,MarginV=60"
    run(["-i", str(src), "-vf", f"subtitles={srt}:force_style='{style}'", *ENCODE, str(dst)])


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("probe"); s.add_argument("input", type=Path)
    s = sub.add_parser("cut"); s.add_argument("input", type=Path); s.add_argument("output", type=Path)
    s.add_argument("--start", type=float, required=True); s.add_argument("--end", type=float, required=True)
    s = sub.add_parser("reel"); s.add_argument("input", type=Path); s.add_argument("output", type=Path)
    s.add_argument("--blur", action="store_true")
    s = sub.add_parser("concat"); s.add_argument("output", type=Path); s.add_argument("inputs", type=Path, nargs="+")
    s = sub.add_parser("subs"); s.add_argument("input", type=Path); s.add_argument("srt", type=Path)
    s.add_argument("output", type=Path)

    a = p.parse_args()
    if a.cmd == "probe":
        print(json.dumps(probe(a.input), indent=2))
    elif a.cmd == "cut":
        cut(a.input, a.output, a.start, a.end)
    elif a.cmd == "reel":
        reel(a.input, a.output, a.blur)
    elif a.cmd == "concat":
        concat(a.output, a.inputs)
    elif a.cmd == "subs":
        subs(a.input, a.srt, a.output)


if __name__ == "__main__":
    main()
