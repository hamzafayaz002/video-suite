---
name: make-video
description: Make a finished short vertical video (Instagram Reel, TikTok, YouTube Short; 1080x1920) from a topic or brief, optionally with reference videos, images, product facts or brand assets. Handles research, story and hooks, script, voiceover, word-synced captions, Vox-style paper-cutout animation, sound effects, music, rendering and a final quality check. Use when the user asks to make, create, generate or produce a video, reel, explainer, promo or ad, or to revise one made earlier.
argument-hint: "[topic or brief]"
allowed-tools: Bash(vs *), Bash(${CLAUDE_PLUGIN_ROOT}/bin/vs *)
---

# Make a video

The user gives a topic (and maybe references). Deliver a rendered MP4 in `videos/<slug>/out/`, made with the
`vs` command from this plugin (`${CLAUDE_PLUGIN_ROOT}/bin/vs` if `vs` is not on PATH). Read
`${CLAUDE_SKILL_DIR}/references/house-rules.md` first: it holds what reviewers already rejected.

Work in this order. Keep the user posted with one short line per stage; show them the script before recording
and the finished video at the end.

## 1. Check the studio

Run `vs doctor`. NOT READY: follow the studio-setup skill, then continue. Note whether the `full` rows are OK
(AI image cutouts available) because it decides how assets get made in step 7.

## 2. Brief

Fill the gaps with at most one AskUserQuestion round, only for what changes the video and cannot be found:
goal (sell, explain, announce), audience, length, must-have facts (product names, prices, features, offer,
store, call to action), references, voice, music. Defaults when the user does not care: Instagram Reel 1080x1920,
30-40 s for ads and promos, 45-60 s for explainers, Vox-style paper collage, voice `af_heart`, no music for
commercial work (they add a trending track in the app) or generated music for non-commercial work.

`vs new "<short title>"` creates `videos/<slug>/` (or `--dir` elsewhere). Copy the user's references into
`refs/`. Write the answers into `brief.md`.

## 3. Research

Skip for pure fiction. Otherwise search the web, open the pages you use (a search snippet is not a source) and
write `research.md`: a table of facts with source links, plus who the audience is. Check the facts fit the
audience (a residential driveway is not a commercial road). Product facts, prices and offers come only from the
user or the brand's own pages, never invented. Note anything you could not confirm and say so at delivery.

## 4. Study the references

- Video: `vs analyze refs/<file> refs/<name>-analysis`, then look at `sheet.jpg` and a few `frames/`. Write
  down pacing (cuts per minute, shot length), framing, palette, text style, how it hooks in the first 2 s.
- Images: look at each. A product or store picture the user gives is a real asset: cut it out with
  `vs cutout tear refs/x.png assets/cut/x.png --cut` (or without `--cut` to keep the whole picture as a
  torn print) and use it, rather than generating a lookalike.
- Put style notes in `brief.md` and follow them where they do not clash with the house rules.

## 5. Story and script

Follow `${CLAUDE_SKILL_DIR}/references/storytelling.md`. In `brief.md`: three hook options and the beat list
(one beat = one scene, 2-6 s each). Then write `script.txt` (format in its header; lines are numbered 1, 2, 3...
in order and build.py refers to them by number). Word budget: seconds x 2.6. Run the humanizer skill over the
lines. Show the user the script with the estimated length and get a yes before recording, unless they said to
go ahead without review.

## 6. Voice

`vs voice videos/<slug>` records each line and writes `timing.json`. Compare `total` with the target: more than
10 % off, cut or add words (not speed) and re-record. Spot-check the word list it prints: a misheard word is
fine (timing only), a mispronounced brand needs respelling in script.txt (e.g. "Char-Broil" -> "Char Broil").

## 7. Assets

List every image each scene needs. Get them in this order of preference:
1. the user's own images (cut out as in step 4);
2. drawn in code: CSS shapes in build.py, or PIL + `vedit.cutout.tear` for props (tables, fences, phones,
   food, piles, signs, charts) and `vs cutout paper` for suns and clouds;
3. generated: put prompts in `assets.json` and run `vs cutout gen videos/<slug>/assets.json videos/<slug>/assets/cut --seeds 2`
   (needs `vs setup --full`; ~30-60 s per picture on a CPU). People: "papercraft cardboard toy figure of ...,
   blocky low poly paper character, full body" keeps characters consistent.
Look at every generated image (make a contact sheet with PIL) and replace failures. Details:
`${CLAUDE_SKILL_DIR}/references/assets.md`.

## 8. Scenes

Write `build.py` from the template's pattern using `${CLAUDE_SKILL_DIR}/references/rig.md`: one builder per
scene, everything hidden at t=0 and brought in on the word it illustrates, labels on the beat, one stamp or
reveal per scene. Then:
- `vs build videos/<slug>` (fix MISSING images and DUPLICATE ids it reports)
- `vs check videos/<slug>` (fix errors; warnings about repeated images are fine)
- `vs snapshot videos/<slug> --at <a time late in each scene, comma separated> --no-end -o renders/snap`, then
  look at `renders/snap/contact-sheet*.jpg`. Fix anything off-screen, overlapping, unreadable or empty, and
  re-snapshot just those times.

## 9. Render, music, check

- `vs render videos/<slug> -o out/<slug>-no-music.mp4` (path relative to the project). A CPU renders about
  2-4 frames a second, so a 35 s video takes 5-10 minutes: run it in the background and wait.
- Music: none -> keep `bgm.json` empty; user's licensed track -> copy it to `assets/bgm/` and list it in
  `bgm.json`; generated (non-commercial only) -> `vs music videos/<slug> --seconds <length> --prompt "<mood, instruments, bpm, no vocals>"`.
- `vs mix videos/<slug>/out/<slug>-no-music.mp4 videos/<slug>/bgm.json videos/<slug>/out/<slug>.mp4`
  (ducks music under the voice, normalises to -14 LUFS).
- `vs qa videos/<slug>/out/<slug>.mp4 --min <low> --max <high>`; look at the `.qa.jpg` sheet. Fix any FAIL.

## 10. Deliver

Give the path, length, the story in 3-5 lines, and anything the user must check (unconfirmed facts, licences
for client work, mismatches between their images and their facts). Keep the no-music render too: people often
add a trending song in Instagram. Record decisions in `brief.md` so the next revision starts from them.

## Revisions

Change only what was asked. Text and timing changes: edit script.txt, `vs voice`, `vs build`, snapshot, render.
Adding or removing a script line shifts the line numbers that `ph()` and `at()` use in build.py: update them
(every number after the change moves by the same amount). Shortening a video: cut whole scenes and lines rather
than speeding the voice up.
