"""Download a video with yt-dlp.

Usage: python -m vedit.download URL [-o media/input]
"""

import argparse
from pathlib import Path

import yt_dlp


def download(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "outtmpl": str(out_dir / "%(id)s.%(ext)s"),
        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
        "merge_output_format": "mp4",
        "noplaylist": True,
        # YouTube needs a JS runtime for its challenges; Node is already required by the studios
        "js_runtimes": {"node": {}},
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return Path(ydl.prepare_filename(info)).with_suffix(".mp4")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("-o", "--out-dir", type=Path, default=Path("media/input"))
    args = parser.parse_args()
    print(download(args.url, args.out_dir))


if __name__ == "__main__":
    main()
