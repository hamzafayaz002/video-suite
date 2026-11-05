# Getting images

All scene images are PNGs with transparency in `assets/cut/`, referenced by name in `cut()`.

## User images (best)
- Product or store photo: `vs cutout tear refs/grill.jpg assets/cut/grill.png --cut` removes the background
  and adds a torn paper border. Check the result: if a hand, table or other object stuck to it, erase that region
  with PIL (set alpha to 0 in a rectangle or polygon) and tear() again.
- Whole picture as a print (a storefront, a screenshot, a flyer): `vs cutout tear refs/store.png assets/cut/store_print.png`.
- Logos: crop from the user's image with PIL; put them on a white or brand-colour tile rather than cutting them out.

## Drawn in code (reliable, fast)
- `vs cutout paper OUT.png --shape sun|cloud --color "#f2c419"` for suns and clouds.
- Props with PIL: draw shapes on a transparent canvas, add texture noise, then `vedit.cutout.tear(img)`:
  tables, fences, phones, food patties, piles of coal or gravel, signs, simple charts and arrows. Example:
  ```python
  from PIL import Image, ImageDraw
  from vedit.cutout import tear
  im = Image.new("RGBA", (520, 360)); d = ImageDraw.Draw(im)
  d.ellipse([10, 40, 510, 340], fill=(150, 60, 66, 255)); d.ellipse([10, 10, 510, 300], fill=(214, 112, 120, 255))
  tear(im, 10, 1).save("assets/cut/patty.png")
  ```
  Run it with `$VS_HOME/venv/bin/python` (default ~/.video-studio) and `PYTHONPATH` set to the plugin's tools
  folder, or put the code in a small script and run `vs` helpers around it.
- Pure CSS in build.py for panels, flyers, gauges, bars, speech bubbles, arrows (see the rig catalogue).

## Generated (needs `vs setup --full`)
- Write prompts in assets.json, then `vs cutout gen assets.json assets/cut --seeds 2`. Each picture takes
  30-60 s on a CPU. The style suffix (paper-craft miniature on white) is added automatically.
- People: "papercraft cardboard toy figure of a cheerful bearded man in a navy polo shirt and khaki pants,
  holding tongs, blocky low poly paper character, full body". Give every character fixed clothes and colours
  and reuse them in every pose prompt ("... with both hands on his head", "... giving a thumbs up").
- Works well: people (paper-craft prompt), houses, trees, cars, simple tools, food on a plate, appliances.
- Often fails: machines with many parts, fences, tables, phones, piles, flat textures, text and logos. Draw those.
- Always review: build a contact sheet (PIL thumbnails on magenta) and look at it. Pick the better seed,
  rename it to NAME.png, delete the rest. Regenerate or draw anything broken.
