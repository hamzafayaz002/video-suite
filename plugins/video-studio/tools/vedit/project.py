"""Start a video project folder.

  vs new NAME [--dir videos]     creates videos/NAME/ with the studio's sounds, textures and GSAP, a demo
                                 build.py + script.txt (3 scenes) and brief.md / assets.json to fill in

Layout:  brief.md  research.md  script.txt  build.py  assets.json  timing.json (from vs voice)
         refs/ (user references)  assets/{cut,ref,sfx,tex,vendor,vo,bgm}  compositions/  renders/  out/
"""

import argparse
import os
import re
import shutil
from pathlib import Path

from vedit.cutout import paper_shape

VS_HOME = Path(os.environ.get("VS_HOME", Path.home() / ".video-studio"))
TEMPLATE = Path(__file__).resolve().parents[2] / "templates" / "project"


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "video"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("name")
    p.add_argument("--dir", type=Path, default=Path("videos"))
    a = p.parse_args()
    root = a.dir / slug(a.name)
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"{root} already exists and is not empty")
    for d in ("refs", "out", "assets/cut", "assets/ref", "assets/vo", "assets/bgm"):
        (root / d).mkdir(parents=True, exist_ok=True)
    for f in ("script.txt", "build.py", "brief.md", "assets.json", "hyperframes.json", "bgm.json"):
        shutil.copy(TEMPLATE / f, root / f)
    shutil.copy(TEMPLATE / "gitignore.txt", root / ".gitignore")
    for sub in ("sfx", "tex", "vendor"):
        src = VS_HOME / "assets" / sub if sub != "vendor" else VS_HOME / "vendor"
        if not src.exists():
            raise SystemExit(f"missing {src}: run `vs setup` first")
        shutil.copytree(src, root / "assets" / sub, dirs_exist_ok=True)
    paper_shape("sun", "#f2c419", 600, 1).save(root / "assets" / "cut" / "sun.png")
    paper_shape("cloud", "#efe8d6", 600, 2).save(root / "assets" / "cut" / "cloud.png")
    paper_shape("cloud", "#8fb3cf", 600, 3).save(root / "assets" / "cut" / "cloud_blue.png")
    print(root)


if __name__ == "__main__":
    main()
