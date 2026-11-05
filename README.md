# video-suite: an AI video studio for Claude Code

Type a topic, get a finished vertical video. The **video-studio** plugin gives Claude Code the whole pipeline:
research, story and hooks, script, voiceover, word-synced captions, Vox-style paper-cutout animation, sound
effects, music, rendering and a final quality check. It also cleans up your own footage (cuts black, frozen,
blurry and silent parts, "um"s and false starts) and captions it.

## Install (once per computer)

In Claude Code:

```
/plugin marketplace add hamzafayaz002/video-suite
/plugin install video-studio@video-suite
```

Then ask Claude: **"set up the video studio"** (or run `vs setup --test`). It installs everything into
`~/.video-studio`: ffmpeg, Node, Python 3.12, the voice and word-timing models, a headless browser for
rendering, the animation library, sound effects and textures, and renders a 10-second test video. Nothing
else to install by hand. Claude Code asks your permission before running the installer.

Optional AI extras (image generation and music, about 6 GB more): **"set up the video studio with the AI extras"**
(`vs setup --full`).

## Use

- "Make a 35-second promo for our Char-Broil grill, $100 now $89.99 at Busy Beaver. Here's the store photo."
- "Make a Vox-style explainer about the dot-com crash. Here's a reference reel I like."
- "Clean up these three clips into a 40-second reel with captions."

Claude asks a few questions if needed, shows you the script, then delivers `videos/<name>/out/<name>.mp4`.
Ask for changes in plain words ("make it shorter", "remove that sound", "change the price").

## Requirements

- Claude Code on macOS, Linux, or Windows through WSL.
- About 2 GB of disk (8 GB with the AI extras) and 8 GB of RAM (16 GB recommended).
- Internet access during setup. On locked-down networks allow: github.com, objects.githubusercontent.com,
  pypi.org, files.pythonhosted.org, registry.npmjs.org, nodejs.org, huggingface.co, *.hf.co,
  googlechromelabs.github.io, storage.googleapis.com (and download.pytorch.org for the extras).
- Speed on a typical laptop CPU: a 35-second video renders in about 5-10 minutes; each AI image takes
  30-60 seconds. Apple Silicon and machines with a GPU are faster.

## What's inside

| Path | What |
|---|---|
| `plugins/video-studio/skills/make-video` | the main skill: brief -> research -> script -> voice -> assets -> scenes -> render -> QA |
| `plugins/video-studio/skills/edit-footage` | footage cleanup, cutting, reframing, captions |
| `plugins/video-studio/skills/studio-setup` | installer (`scripts/setup.sh`) and troubleshooting |
| `plugins/video-studio/skills/humanizer` | makes scripts sound human (MIT, blader/humanizer) |
| `plugins/video-studio/skills/skill-creator` | build new skills for the suite (Apache-2.0, Anthropic) |
| `plugins/video-studio/bin/vs` | the `vs` command (on PATH while the plugin is enabled) |
| `plugins/video-studio/tools/vedit` | Python tools: rig (animation engine), voice, footage, qa, mix, music, cutout, analyze, sfx, textures |
| `plugins/video-studio/templates/project` | starting files for each new video |

`vs help` lists the commands. `vs doctor` shows what is installed.

## Licences of the models and libraries it downloads

- Kokoro voice (Apache-2.0), Whisper (MIT), HyperFrames renderer (Apache-2.0), GSAP (free standard licence),
  ffmpeg (GPL/LGPL builds): fine for client work.
- SD-Turbo image model (Stability AI Community License): free for organisations under US$1M annual revenue.
- MusicGen music model (CC-BY-NC 4.0): **non-commercial only**. For ads, use a licensed track or add music
  in the app.
- Never use the studio to download or reuse copyrighted music or footage you don't have rights to.

## Developing

- Test locally without installing: `claude --plugin-dir ./plugins/video-studio`.
- Validate: `claude plugin validate .` and `claude plugin validate ./plugins/video-studio`.
- Clean-install test: `VS_HOME=/tmp/vs-test plugins/video-studio/bin/vs setup --test`.
- New skills: use the bundled skill-creator skill; keep each skill's SKILL.md short and put detail in `references/`.
- Bump `version` in `plugins/video-studio/.claude-plugin/plugin.json` on every release so users get the update
  (`/plugin marketplace update video-suite`).
