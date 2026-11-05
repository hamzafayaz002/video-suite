# House rules

Lessons from real client reviews. Follow them unless the user asks otherwise.

## Length and pacing
- Ads and promos: 30-40 s. The first cut of one promo ran 82 s and was rejected as too long; the 35 s cut was
  approved. Explainers: 45-60 s. Never pad to fill time.
- First 2 seconds hook the viewer (a person, a problem, a surprising number), not a logo.
- One idea per scene, 2-6 s each. Lists of features: one short line and one visual per feature.
- Shortening: cut whole scenes and lines; never speed the voice past 1.15.

## Sound
- No bass "boom" or impact hits: reviewers called them annoying. The generated pack has none on purpose.
  Use pops, whooshes, typing, clicks, a sizzle or beep that fits the story, and a chime on the end card.
- Sound effects at 0.2-0.4 volume; the voice always wins. Music sits under the voice (mix ducks it).
- Never download famous or trending songs. The user adds those inside Instagram or TikTok.

## Facts and claims
- Check the audience before writing: a video about paving a home driveway was rejected for describing
  commercial road work (wrong base depth, wrong machines). Research the exact audience's version of the topic.
- Prices, discounts, specs and offers come only from the user or the brand's own pages. Show the old price
  struck through and the new price large when the user gives both.
- No exclusivity ("only at"), "best", "cheapest", guarantee or time-limit claims unless the user supplied them.
- Jokes and invented story details (a character, "12 friends") are fine; invented product facts are not.
- If the user's images and facts disagree (a gas-grill photo with charcoal-grill features), point it out at
  delivery.

## Look
- Default style: Vox-like paper collage. Torn-paper cutouts, paper textures, film grain, 2.5D parallax,
  typewriter labels, rubber stamps, bold captions with key words in yellow boxes and bad news in red.
- Characters: one consistent style per video. Paper-craft "blocky low poly paper character" figures match a
  paper world; photo cutouts look like a different video.
- Real products and stores: use the user's photos, cut out, not AI lookalikes. Keep logos and prices legible.
- Keep content between y=200 and y=1300 of the 1080x1920 frame. Captions sit at y=1420; the bottom ~350 px
  and top ~200 px are covered by the app UI.
- End card: product, price/offer, store or call to action, held at least 1 s after the last word.

## Voice
- Script phrase by phrase with per-line speed and pauses (`scene|speed|pause|text`): it sounds far more
  natural than one long take. Pause 0.5-0.8 s before a reveal or punchline.
- Run the humanizer skill on the script. Short sentences, concrete words, no "not X but Y" constructions.
- The local voice (Kokoro) is good but not human. Offer a human recording for important client work: drop
  the WAV in as assets/vo/voice.wav, keep script.txt matching it, and use `vs transcribe` for timings.

## Process
- Show the script before recording; show snapshots before the long render if the user is watching.
- Keep the no-music render next to the final: people add trending audio in the app.
- Write every decision and the user's feedback into brief.md so revisions start from it.
