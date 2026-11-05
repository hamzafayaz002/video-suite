---
name: studio-setup
description: Install and check everything video-studio needs (ffmpeg, Node, a Python env, voice and word-timing models, the headless renderer, GSAP, sound effects, textures, and optionally AI image and music models). Use when the user asks to set up, install, repair or update the video studio, when `vs doctor` reports NOT READY, or before the first video on a new machine.
allowed-tools: Bash(vs doctor*), Bash(vs setup*), Bash(${CLAUDE_PLUGIN_ROOT}/bin/vs *)
---

# Studio setup

Everything installs into `~/.video-studio` (override with `VS_HOME`). The `vs` command ships in this plugin's
`bin/`, which Claude Code puts on PATH; if `vs` is not found, call it as `${CLAUDE_PLUGIN_ROOT}/bin/vs`.

## Steps

1. Run `vs doctor`. If it prints READY and the user did not ask for the AI extras, say so and stop.
2. Tell the user in two lines what will be installed and roughly how long it takes, then run setup. It downloads
   about 1.5 GB, so give the Bash call a long timeout (20 minutes) or run it in the background and wait:
   - core: `vs setup --test` (ffmpeg, Node, Python 3.12 env via uv, Kokoro voice, Whisper, headless Chrome,
     GSAP, generated sound effects and paper textures, then a 10-second test render)
   - with AI image cutouts and AI music: `vs setup --full --test` (about 6 GB more; image generation on a CPU
     takes 20-60 s per picture)
3. Read the doctor table at the end. Any `!!` row on a core item: fix it with the table below and re-run
   `vs setup` (each step is skipped when already done).
4. If `--test` ran, look at the contact sheet next to `~/.video-studio/test/test.mp4` (qa prints its path) and
   tell the user setup worked and how to start: "Make a 35-second video about ..." (the make-video skill) or
   "Clean up this clip" (the edit-footage skill).

## When something fails

| Symptom | Fix |
|---|---|
| Windows (Git Bash, MSYS, CYGWIN) | The studio runs in WSL: `wsl --install`, open Ubuntu, install Claude Code there, run setup again |
| macOS without Homebrew and no ffmpeg | Ask the user to install Homebrew from https://brew.sh (it needs their password), then re-run |
| `curl` or downloads fail, 403, timeouts | A firewall or proxy. The hosts needed are github.com, objects.githubusercontent.com (ffmpeg, uv, Python and model downloads), pypi.org, files.pythonhosted.org, registry.npmjs.org, nodejs.org, huggingface.co, *.hf.co, googlechromelabs.github.io and storage.googleapis.com (Chrome), download.pytorch.org (--full) |
| renderer browser `!!` on Linux, or render fails with missing `.so` libraries | Chrome needs system libraries: `sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 libasound2` (ask first: it needs the user's password) |
| Low disk (doctor's free disk row) | Core needs ~2 GB free, `--full` ~8 GB |
| Python libs fail to build | Delete `~/.video-studio/venv` and re-run `vs setup`; uv downloads its own Python 3.12 |

Never disable TLS verification or pipe unknown scripts into a shell to get around a failure; report it instead.

## Licences to mention when relevant

- Kokoro voice (Apache-2.0), Whisper (MIT), HyperFrames (Apache-2.0), GSAP (free standard licence): fine for client work.
- SD-Turbo image model: Stability AI Community License; free for businesses under US$1M annual revenue.
- MusicGen music model: CC-BY-NC 4.0, non-commercial only. For ads, use a licensed track or add music in the app.
