#!/usr/bin/env bash
# video-studio installer. Safe to re-run: every step is skipped when already done.
#   vs setup            core studio: ffmpeg, Node, Python env, voice + whisper models, renderer, GSAP, sounds, textures
#   vs setup --full     + AI image cutouts (SD-Turbo, rembg) and AI music (MusicGen); ~6 GB more
#   vs setup --test     + render a 10-second demo video to prove everything works
# Everything goes in $VS_HOME (default ~/.video-studio). System packages are used when they exist;
# otherwise ffmpeg and Node are downloaded into $VS_HOME/bin (no admin password needed).
set -euo pipefail

FULL=0; TEST=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --test) TEST=1 ;;
    *) echo "unknown option $arg" >&2; exit 2 ;;
  esac
done

PLUGIN_ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../.." && pwd)"
VS_HOME="${VS_HOME:-$HOME/.video-studio}"
mkdir -p "$VS_HOME/bin" "$VS_HOME/models" "$VS_HOME/vendor" "$VS_HOME/assets"
export PATH="$VS_HOME/bin:$VS_HOME/node/bin:$PATH"
OS="$(uname -s)"; ARCH="$(uname -m)"
NODE_VERSION="22.22.0"; GSAP_VERSION="3.15.1"; HF="hyperframes@0.8.200"

step() { printf '\n==> %s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }
fetch() { curl -fL --retry 3 --progress-bar "$1" -o "$2"; }

case "$OS" in
  Linux|Darwin) ;;
  MINGW*|MSYS*|CYGWIN*) echo "On Windows, install WSL (wsl --install), open Ubuntu, and run Claude Code there." >&2; exit 1 ;;
  *) echo "Unsupported system: $OS" >&2; exit 1 ;;
esac
have curl || { echo "curl is required. Install it with your package manager and re-run." >&2; exit 1; }

# ------------------------------------------------------------------ ffmpeg
step "ffmpeg"
if have ffmpeg && have ffprobe; then
  echo "found $(ffmpeg -version | head -1)"
elif [ "$OS" = Darwin ] && have brew; then
  brew install ffmpeg
elif [ "$OS" = Linux ] && have apt-get && [ "$(id -u)" = 0 ]; then
  apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq ffmpeg
elif [ "$OS" = Linux ]; then
  case "$ARCH" in x86_64) FA=linux64 ;; aarch64|arm64) FA=linuxarm64 ;; *) echo "no static ffmpeg for $ARCH" >&2; exit 1 ;; esac
  tmp="$(mktemp -d)"  # static GPL build from github.com/BtbN/FFmpeg-Builds
  fetch "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-$FA-gpl.tar.xz" "$tmp/ff.tar.xz"
  tar -xJf "$tmp/ff.tar.xz" -C "$tmp"
  cp "$tmp"/ffmpeg-*/bin/ffmpeg "$tmp"/ffmpeg-*/bin/ffprobe "$VS_HOME/bin/"
  rm -rf "$tmp"; echo "installed static ffmpeg into $VS_HOME/bin"
else
  echo "Install Homebrew (https://brew.sh), then re-run. ffmpeg comes from: brew install ffmpeg" >&2; exit 1
fi

# ------------------------------------------------------------------ Node 18+
step "Node.js"
node_ok() { have node && have npx && [ "$(node -p 'process.versions.node.split(".")[0]')" -ge 18 ]; }
if node_ok; then
  echo "found node $(node --version)"
else
  case "$OS-$ARCH" in
    Linux-x86_64) NP=linux-x64 ;; Linux-aarch64|Linux-arm64) NP=linux-arm64 ;;
    Darwin-arm64) NP=darwin-arm64 ;; Darwin-x86_64) NP=darwin-x64 ;; *) echo "no Node build for $OS $ARCH" >&2; exit 1 ;;
  esac
  tmp="$(mktemp -d)"
  fetch "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-$NP.tar.gz" "$tmp/node.tgz"
  rm -rf "$VS_HOME/node"; mkdir -p "$VS_HOME/node"
  tar -xzf "$tmp/node.tgz" -C "$VS_HOME/node" --strip-components 1
  rm -rf "$tmp"; echo "installed node $(node --version) into $VS_HOME/node"
fi

# ------------------------------------------------------------------ Python env (uv brings its own Python 3.12)
step "Python environment"
if ! have uv; then
  case "$OS-$ARCH" in
    Linux-x86_64) UT=x86_64-unknown-linux-gnu ;; Linux-aarch64|Linux-arm64) UT=aarch64-unknown-linux-gnu ;;
    Darwin-arm64) UT=aarch64-apple-darwin ;; Darwin-x86_64) UT=x86_64-apple-darwin ;; *) echo "no uv build for $OS $ARCH" >&2; exit 1 ;;
  esac
  tmp="$(mktemp -d)"
  fetch "https://github.com/astral-sh/uv/releases/latest/download/uv-$UT.tar.gz" "$tmp/uv.tgz"
  tar -xzf "$tmp/uv.tgz" -C "$tmp" && cp "$tmp/uv-$UT/uv" "$VS_HOME/bin/"
  rm -rf "$tmp"; echo "installed uv into $VS_HOME/bin"
fi
if [ ! -x "$VS_HOME/venv/bin/python" ]; then
  uv venv --python 3.12 "$VS_HOME/venv"
fi
PY="$VS_HOME/venv/bin/python"
uv pip install --python "$PY" -q -r "$PLUGIN_ROOT/tools/requirements.txt"
echo "python env ready: $("$PY" --version)"
export PYTHONPATH="$PLUGIN_ROOT/tools" HF_HOME="$VS_HOME/models/hf" U2NET_HOME="$VS_HOME/models/rembg"

# ------------------------------------------------------------------ models
step "Voice model (Kokoro, ~330 MB) and word-timing model (Whisper base)"
K="$VS_HOME/models/kokoro"; mkdir -p "$K"
KR="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
[ -s "$K/kokoro-v1.0.onnx" ] || fetch "$KR/kokoro-v1.0.onnx" "$K/kokoro-v1.0.onnx"
[ -s "$K/voices-v1.0.bin" ] || fetch "$KR/voices-v1.0.bin" "$K/voices-v1.0.bin"
"$PY" -c "
from faster_whisper import WhisperModel
WhisperModel('base', device='cpu', compute_type='int8', download_root='$VS_HOME/models/whisper')
print('whisper base ready')"

# ------------------------------------------------------------------ GSAP + renderer browser + HyperFrames
step "Animation library (GSAP $GSAP_VERSION)"
if [ ! -s "$VS_HOME/vendor/gsap.min.js" ]; then
  tmp="$(mktemp -d)"
  if (cd "$tmp" && npm pack --silent "gsap@$GSAP_VERSION" >/dev/null 2>&1); then
    tar -xzf "$tmp"/gsap-*.tgz -C "$tmp" && cp "$tmp/package/dist/gsap.min.js" "$VS_HOME/vendor/"
  else
    fetch "https://cdn.jsdelivr.net/npm/gsap@$GSAP_VERSION/dist/gsap.min.js" "$VS_HOME/vendor/gsap.min.js"
  fi
  rm -rf "$tmp"
fi
echo "gsap ready"

step "Renderer browser"
chrome=""
if [ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ] && [ -x "$PUPPETEER_EXECUTABLE_PATH" ]; then
  chrome="$PUPPETEER_EXECUTABLE_PATH"
elif [ -f "$VS_HOME/chrome-path" ] && [ -x "$(cat "$VS_HOME/chrome-path")" ]; then
  chrome="$(cat "$VS_HOME/chrome-path")"
else
  out="$(npx --yes @puppeteer/browsers install chrome-headless-shell@stable --path "$VS_HOME/browsers" </dev/null 2>&1 | tail -1)" || true
  chrome="$(echo "$out" | awk '{print $NF}')"
  if [ ! -x "$chrome" ]; then  # offline or blocked: fall back to any headless shell already on the machine
    chrome="$(ls -d /opt/pw-browsers/chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell 2>/dev/null | head -1 || true)"
  fi
fi
if [ -n "$chrome" ] && [ -x "$chrome" ]; then
  echo "$chrome" > "$VS_HOME/chrome-path"; echo "browser: $chrome"
else
  echo "WARNING: no headless browser installed ($out)" >&2
fi
npx --yes "$HF" --version </dev/null >/dev/null 2>&1 && echo "hyperframes cached" || echo "WARNING: could not fetch $HF from npm" >&2

# ------------------------------------------------------------------ sounds + textures (generated, licence-free)
step "Sound effects and paper textures"
[ -s "$VS_HOME/assets/sfx/pop.mp3" ] || "$PY" -m vedit.sfx "$VS_HOME/assets/sfx"
[ -s "$VS_HOME/assets/tex/paper-light.jpg" ] || "$PY" -m vedit.textures "$VS_HOME/assets/tex"

# ------------------------------------------------------------------ optional AI generation
if [ "$FULL" = 1 ]; then
  step "AI image + music generation (torch, SD-Turbo, rembg, MusicGen; several GB)"
  if [ "$OS" = Linux ] && ! have nvidia-smi; then
    uv pip install --python "$PY" -q torch --index-url https://download.pytorch.org/whl/cpu
  else
    uv pip install --python "$PY" -q torch
  fi
  uv pip install --python "$PY" -q -r "$PLUGIN_ROOT/tools/requirements-full.txt"
  "$PY" -c "
from diffusers import AutoPipelineForText2Image
AutoPipelineForText2Image.from_pretrained('stabilityai/sd-turbo')
from transformers import AutoProcessor, MusicgenForConditionalGeneration
AutoProcessor.from_pretrained('facebook/musicgen-small'); MusicgenForConditionalGeneration.from_pretrained('facebook/musicgen-small')
from rembg import new_session; new_session('isnet-general-use')
print('image + music models ready')"
fi

# ------------------------------------------------------------------ check
step "Doctor"
"$PY" -m vedit.doctor || true

if [ "$TEST" = 1 ]; then
  step "Test render (about 1-3 minutes)"
  t="$(mktemp -d)"
  "$PY" -m vedit.project setup-test --dir "$t" >/dev/null
  "$PY" -m vedit.voice "$t/setup-test"
  "$PY" "$t/setup-test/build.py"
  [ -f "$VS_HOME/chrome-path" ] && export PUPPETEER_EXECUTABLE_PATH="$(cat "$VS_HOME/chrome-path")"
  (cd "$t/setup-test" && npx --yes "$HF" render -o "$t/setup-test/out/raw.mp4" </dev/null >"$t/render.log" 2>&1) \
    || { tail -20 "$t/render.log" >&2; echo "TEST RENDER FAILED (log: $t/render.log)" >&2; exit 1; }
  mkdir -p "$VS_HOME/test"
  "$PY" -m vedit.mix "$t/setup-test/out/raw.mp4" "$t/setup-test/bgm.json" "$VS_HOME/test/test.mp4" >/dev/null
  "$PY" -m vedit.qa "$VS_HOME/test/test.mp4" --min 8 --max 20 || { echo "TEST VIDEO FAILED QA" >&2; exit 1; }
  echo "test video: $VS_HOME/test/test.mp4"
fi
echo
echo "video-studio setup finished. Home: $VS_HOME"
