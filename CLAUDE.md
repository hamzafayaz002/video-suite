# CLAUDE.md (developing this repo)

This repo is a Claude Code marketplace (`.claude-plugin/marketplace.json`) with one plugin,
`plugins/video-studio`. Users install it with `/plugin marketplace add hamzafayaz002/video-suite`.

- Runtime state lives in `$VS_HOME` (default `~/.video-studio`), never in the plugin folder: venv, models,
  vendor/gsap.min.js, assets/{sfx,tex}, chrome-path, test/.
- `bin/vs` is the only entry point skills should call. Python tools are `tools/vedit/*.py`, run as `vs <tool>`.
- `vedit.doctor` must stay standard-library only (it runs before setup).
- Skills reference bundled files with `${CLAUDE_SKILL_DIR}` / `${CLAUDE_PLUGIN_ROOT}` in their Markdown; those
  variables are not exported to shell commands.
- Pin versions: requirements*.txt, `hyperframes@0.8.200` in bin/vs and setup.sh, GSAP and Node in setup.sh.
- Before pushing: `claude plugin validate .`, `claude plugin validate ./plugins/video-studio`, and for installer
  changes a clean `VS_HOME=/tmp/x plugins/video-studio/bin/vs setup --test`.
- Never commit media, models or renders. Bump plugin.json `version` for each release.
- House rules for the videos themselves live in `plugins/video-studio/skills/make-video/references/house-rules.md`.
