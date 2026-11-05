"""Paper cutouts for collage videos: generate an object (SD-Turbo), cut it out (rembg), add a torn paper border.

  vs cutout gen   ASSETS.json OUT_DIR [--seeds 2]   # {"name": "prompt"}; skips names already in OUT_DIR and keys starting with _
                                                    # extra seeds land as NAME_v2.png ...: look at them and keep the best as NAME.png
  vs cutout tear  IN.png OUT.png [--cut]           # torn border around a user photo or cutout (--cut removes the background first)
  vs cutout paper OUT.png --shape sun|cloud --color "#f2c419" --size 600

Needs `vs setup --full` (torch, diffusers, rembg). Models: stabilityai/sd-turbo, rembg isnet-general-use.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

STYLE = (", paper craft miniature model made of cardboard and colored paper, handmade, whole object visible, centered, "
         "isolated on plain white background, soft studio light, high detail")
PAPER_RGB = (238, 231, 214)


def _noise(size: tuple[int, int], scale: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    w, h = size
    n = rng.random((h // scale + 2, w // scale + 2))
    return np.asarray(Image.fromarray((n * 255).astype("uint8")).resize((w, h), Image.BICUBIC), np.float32) / 255


def tear(img: Image.Image, border: int = 14, seed: int = 0) -> Image.Image:
    """Put an RGBA cutout on a rough-edged paper backing that is `border` px wider than the object."""
    img = img.convert("RGBA")
    pad = border * 3
    canvas = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, (pad, pad), img)
    alpha = canvas.getchannel("A").point(lambda a: 255 if a > 40 else 0)
    grown = alpha.filter(ImageFilter.MaxFilter(border * 2 + 1)).filter(ImageFilter.GaussianBlur(border * 0.6))
    rough = (_noise(canvas.size, 6, seed) * 0.7 + _noise(canvas.size, 2, seed + 1) * 0.3)
    edge = (np.asarray(grown, np.float32) / 255) + (rough - 0.5) * 0.55
    mask = Image.fromarray(((edge > 0.5) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(0.7))
    fibre = (np.asarray(Image.new("RGB", canvas.size, PAPER_RGB), np.float32)
             - (_noise(canvas.size, 3, seed + 2)[..., None] * 18))
    paper = Image.fromarray(np.clip(fibre, 0, 255).astype("uint8")).convert("RGBA")
    paper.putalpha(mask)
    paper.alpha_composite(canvas)
    return paper.crop(paper.getbbox())


def vintage(img: Image.Image, amount: float = 0.35) -> Image.Image:
    """Muted, warm print look like the collage references."""
    rgb = img.convert("RGB")
    grey = rgb.convert("L").convert("RGB")
    out = Image.blend(rgb, grey, amount)
    warm = Image.new("RGB", out.size, (255, 236, 205))
    out = ImageChops.multiply(out, warm)
    res = out.convert("RGBA")
    res.putalpha(img.getchannel("A"))
    return res


def paper_shape(shape: str, color: str, size: int, seed: int = 0) -> Image.Image:
    """Torn coloured paper: a sun disc or a cloud."""
    w, h = (size, size) if shape == "sun" else (size, int(size * 0.62))
    base = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(base)
    if shape == "sun":
        d.ellipse([w * 0.06, h * 0.06, w * 0.94, h * 0.94], fill=255)
    else:
        for cx, cy, r in [(0.28, 0.65, 0.22), (0.45, 0.42, 0.28), (0.65, 0.5, 0.24), (0.8, 0.68, 0.17), (0.5, 0.72, 0.22)]:
            d.ellipse([w * (cx - r * 0.9), h * (cy - r * 1.1), w * (cx + r * 0.9), h * (cy + r * 1.1)], fill=255)
        d.rectangle([w * 0.12, h * 0.68, w * 0.92, h * 0.92], fill=255)
    rough = _noise((w, h), 5, seed)
    edge = np.asarray(base.filter(ImageFilter.GaussianBlur(size * 0.012)), np.float32) / 255 + (rough - 0.5) * 0.5
    mask = Image.fromarray(((edge > 0.5) * 255).astype("uint8"))
    rgb = np.array(Image.new("RGB", (w, h), color), np.float32)
    rgb -= (_noise((w, h), 9, seed + 1)[..., None] - 0.5) * 34 + (_noise((w, h), 2, seed + 4)[..., None] - 0.5) * 12
    out = Image.fromarray(np.clip(rgb, 0, 255).astype("uint8")).convert("RGBA")
    out.putalpha(mask)
    return tear(out, border=max(6, size // 70), seed=seed + 3)


def generate(assets: dict, out_dir: Path, seeds: int = 1) -> None:
    import torch
    from diffusers import AutoPipelineForText2Image
    from rembg import new_session, remove

    torch.set_num_threads(4)
    pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sd-turbo", torch_dtype=torch.float32)
    session = new_session("isnet-general-use")
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, (name, prompt) in enumerate(assets.items()):
        if name.startswith("_") or (out_dir / f"{name}.png").exists():
            continue
        for k in range(seeds):
            stem = name if k == 0 else f"{name}_v{k + 1}"
            raw = pipe(prompt=prompt + STYLE, num_inference_steps=3, guidance_scale=0.0, width=512, height=512,
                       generator=torch.Generator().manual_seed(100 + i + 1000 * k)).images[0]
            raw.save(out_dir / f"{stem}.raw.png")
            tear(vintage(remove(raw, session=session)), seed=i + k).save(out_dir / f"{stem}.png")
            print(stem, flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("gen"); s.add_argument("assets", type=Path); s.add_argument("out_dir", type=Path)
    s.add_argument("--seeds", type=int, default=1)
    s = sub.add_parser("tear"); s.add_argument("input", type=Path); s.add_argument("output", type=Path)
    s.add_argument("--cut", action="store_true", help="remove the background with rembg first (needs setup --full)")
    s = sub.add_parser("paper"); s.add_argument("output", type=Path)
    s.add_argument("--shape", choices=["sun", "cloud"], default="sun"); s.add_argument("--color", default="#f2c419")
    s.add_argument("--size", type=int, default=600); s.add_argument("--seed", type=int, default=0)
    a = p.parse_args()
    if a.cmd == "gen":
        generate(json.loads(a.assets.read_text()), a.out_dir, a.seeds)
    elif a.cmd == "tear":
        img = Image.open(a.input)
        if a.cut:
            from rembg import new_session, remove
            img = remove(img, session=new_session("isnet-general-use"))
            img = img.crop(img.getbbox())
        tear(img).save(a.output)
    else:
        paper_shape(a.shape, a.color, a.size, a.seed).save(a.output)


if __name__ == "__main__":
    main()
