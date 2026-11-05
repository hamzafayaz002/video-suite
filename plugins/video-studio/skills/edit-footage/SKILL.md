---
name: edit-footage
description: Turn the user's own raw clips into a clean vertical video - finds and cuts black, frozen, blurry and silent stretches, "um/uh" fillers and false starts, joins clips, reframes to 1080x1920, adds bold word-by-word captions, music and a final quality check. Use when the user gives video files and asks to edit, clean up, cut, trim, shorten, caption, reframe or turn them into a reel/short. For animated videos from a topic use make-video instead; for mixing their clips into an animated video use both.
argument-hint: "[clip files] [what to make]"
allowed-tools: Bash(vs *), Bash(${CLAUDE_PLUGIN_ROOT}/bin/vs *)
---

# Edit footage

Use the `vs` command from this plugin (`${CLAUDE_PLUGIN_ROOT}/bin/vs` if not on PATH). Run `vs doctor` first;
if NOT READY follow the studio-setup skill.

1. **Project.** `vs new "<title>"` and copy the clips into `videos/<slug>/refs/` (keep the originals untouched).
   Ask at most one round of questions: target length, platform, framing (crop to fill / fit on a blurred
   background), captions yes/no, music, anything that must stay or go.
2. **Look.** `vs analyze refs/<clip> refs/<clip>-analysis` for each clip and view `sheet.jpg`, so you know
   what is in it. `vs ffmpeg probe <clip>` for size, rotation and fps.
3. **Find the bad parts.** From the project folder:
   - `vs footage scan refs/*.mp4 -o scan.json` (black, frozen, blurry, silent stretches and scene cuts)
   - `vs footage words refs/*.mp4 -o words.json` for clips with speech (word timings, used to cut fillers and
     restarted sentences)
   - `vs footage plan scan.json --words words.json -o edl.json` builds the keep-list. Read edl.json and the
     transcript: reorder segments for the story, drop weak takes, keep the best version of repeated lines,
     respect the target length. Edit edl.json directly (it is a plain list of file/start/end).
   Blurry detection is relative to each clip: a clip that is soft all over is not flagged; judge it yourself.
4. **Cut.** `vs footage cut edl.json out/cut.mp4 --frame crop` (`blur` keeps the whole frame on a blurred
   background, good for landscape footage with people at the edges; `keep` pads with bars).
5. **Captions** (default on for speech): `vs footage captions out/cut.mp4 out/captioned.mp4` (3 words per line,
   the spoken word turns yellow).
6. **Music and loudness.** Same as make-video: empty `bgm.json` = no music, a licensed track, or `vs music`
   (non-commercial only). `vs mix out/captioned.mp4 bgm.json out/<slug>.mp4`.
7. **Check.** `vs qa out/<slug>.mp4 --min <low> --max <high>`, look at the `.qa.jpg` contact sheet and spot-check
   a few cut points (`vs ffmpeg cut` a 3 s piece around each, or grab frames) for jump cuts mid-word.
8. **Deliver** the path, the length before and after, and a short list of what was removed and why.

To combine footage with animation, render the animated part with make-video and join the pieces with
`vs ffmpeg concat OUT a.mp4 b.mp4` (both 1080x1920 30 fps; re-encode with `vs ffmpeg reel` first if not).
