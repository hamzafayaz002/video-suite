"""Lay a music bed under a rendered video, ducked under its voice/SFX, and export for Reels.

Spec (JSON):
  {"segments": [{"file": "a.wav", "from": 0, "to": 30, "at": 0, "fade_in": 0.5, "fade_out": 1.0, "volume": 0.5}, ...],
   "bed_volume": 0.35}
Each segment takes [from, to) seconds of `file` and places it at `at` seconds in the video.

Usage: vs mix VIDEO SPEC.json OUT.mp4 [--no-encode]
An empty "segments" list means no music: the soundtrack is only loudness-normalised.
"""

import argparse
import json
import subprocess
from pathlib import Path


def build_filter(spec: dict, duration: float) -> tuple[list[str], str]:
    if not spec.get("segments"):  # no music: just bring the voice + effects to Reels loudness
        return [], "[0:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11[aout]"
    inputs, chains, labels = [], [], []
    for k, seg in enumerate(spec["segments"]):
        inputs += ["-i", seg["file"]]
        length = seg["to"] - seg["from"]
        fo = seg.get("fade_out", 0.5)
        chains.append(
            f'[{k + 1}:a]atrim={seg["from"]}:{seg["to"]},asetpts=PTS-STARTPTS,aresample=48000,'
            f'aformat=channel_layouts=stereo,afade=t=in:d={seg.get("fade_in", 0.3)},'
            f'afade=t=out:st={max(0, length - fo)}:d={fo},volume={seg.get("volume", 1.0)},'
            f'adelay={int(seg["at"] * 1000)}|{int(seg["at"] * 1000)}[m{k}]')
        labels.append(f"[m{k}]")
    n = len(labels)
    chains.append(f'{"".join(labels)}amix=inputs={n}:normalize=0,atrim=0:{duration},volume={spec.get("bed_volume", 0.35)}[bed]')
    chains.append("[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[vo][key]")
    chains.append("[bed][key]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=350:makeup=1[duck]")
    chains.append("[vo][duck]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]")
    return inputs, ";".join(chains)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("spec", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--no-encode", action="store_true", help="copy the video stream instead of re-encoding for Reels")
    a = p.parse_args()

    spec = json.loads(a.spec.read_text())
    for seg in spec["segments"]:  # paths in the spec are relative to the spec file
        seg["file"] = str((a.spec.parent / seg["file"]).resolve())
    duration = float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(a.video)]).decode())
    inputs, graph = build_filter(spec, duration)
    video = (["-c:v", "copy"] if a.no_encode else
             ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p", "-r", "30"])
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(a.video), *inputs,
                    "-filter_complex", graph, "-map", "0:v", "-map", "[aout]", *video,
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(a.output)], check=True)
    print(a.output)


if __name__ == "__main__":
    main()
