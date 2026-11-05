"""Report what video-studio needs and whether it is installed. Standard library only, so it runs before setup.

  vs doctor            human-readable checklist
  vs doctor --json     machine-readable, for the skills
Exit code 0 when the core studio works, 1 when something core is missing.
"""

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

VS_HOME = Path(os.environ.get("VS_HOME", Path.home() / ".video-studio"))
VENV_PY = VS_HOME / "venv" / "bin" / "python"


def version(cmd: list[str]) -> str | None:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (out.stdout or out.stderr).strip().splitlines()[0] if out.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def venv_has(*mods: str) -> bool:
    if not VENV_PY.exists():
        return False
    code = "import importlib.util,sys; sys.exit(0 if all(importlib.util.find_spec(m) for m in sys.argv[1:]) else 1)"
    return subprocess.run([str(VENV_PY), "-c", code, *mods], capture_output=True).returncode == 0


def checks() -> list[dict]:
    node = version(["node", "--version"])
    node_ok = bool(node) and int(node.lstrip("v").split(".")[0]) >= 18
    chrome = (VS_HOME / "chrome-path").read_text().strip() if (VS_HOME / "chrome-path").exists() else os.environ.get("PUPPETEER_EXECUTABLE_PATH")
    free_gb = shutil.disk_usage(VS_HOME if VS_HOME.exists() else Path.home()).free / 1e9
    kokoro = VS_HOME / "models" / "kokoro"
    out = [
        ("core", "ffmpeg", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), version(["ffmpeg", "-version"])),
        ("core", "node 18+ and npx", node_ok and bool(shutil.which("npx")), node),
        ("core", "python 3.10+", sys.version_info >= (3, 10), platform.python_version()),
        ("core", "studio python env", VENV_PY.exists(), str(VENV_PY)),
        ("core", "python libs (whisper, voice, images)", venv_has("faster_whisper", "kokoro_onnx", "soundfile", "PIL", "numpy"), None),
        ("core", "voice model (Kokoro)", (kokoro / "kokoro-v1.0.onnx").exists() and (kokoro / "voices-v1.0.bin").exists(), str(kokoro)),
        ("core", "renderer browser", bool(chrome) and Path(chrome).exists(), chrome),
        ("core", "GSAP animation library", (VS_HOME / "vendor" / "gsap.min.js").exists(), None),
        ("core", "sound effects + paper textures", (VS_HOME / "assets" / "sfx" / "pop.mp3").exists() and (VS_HOME / "assets" / "tex" / "paper-light.jpg").exists(), None),
        ("full", "AI image cutouts (SD-Turbo + rembg)", venv_has("torch", "diffusers", "rembg"), "vs setup --full"),
        ("full", "AI music (MusicGen, non-commercial licence)", venv_has("torch", "transformers"), "vs setup --full"),
        ("info", "free disk (GB)", free_gb >= 8, f"{free_gb:.0f}"),
    ]
    return [{"tier": t, "name": n, "ok": ok, "detail": d} for t, n, ok, d in out]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    rows = checks()
    core_ok = all(r["ok"] for r in rows if r["tier"] == "core")
    if a.json:
        print(json.dumps({"ready": core_ok, "vs_home": str(VS_HOME), "os": platform.system(), "checks": rows}, indent=1))
    else:
        print(f"video-studio doctor ({platform.system()} {platform.machine()}, home {VS_HOME})")
        for r in rows:
            mark = "OK " if r["ok"] else ("-- " if r["tier"] == "full" else "!! ")
            print(f"  {mark}[{r['tier']}] {r['name']}" + (f"  ({r['detail']})" if r["detail"] else ""))
        print("READY" if core_ok else "NOT READY: run `vs setup`")
    sys.exit(0 if core_ok else 1)


if __name__ == "__main__":
    main()
