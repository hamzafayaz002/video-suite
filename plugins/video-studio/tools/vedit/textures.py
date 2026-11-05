"""Generate the studio's paper and ground textures from code.

  vs textures OUT_DIR   paper-light.jpg, paper.jpg, kraft.jpg, grain.png, halftone.png,
                        asphalt.jpg, soil.jpg, gravel.jpg, grass.jpg, wood.jpg, torn-black.png, torn-white.png
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
rng = np.random.default_rng(7)


def blur_noise(w: int, h: int, scale: int, sigma: float) -> np.ndarray:
    n = rng.random((h // scale + 2, w // scale + 2))
    im = Image.fromarray((n * 255).astype("uint8")).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(sigma))
    return np.asarray(im, np.float32) / 255


def save(arr: np.ndarray, path: Path) -> None:
    Image.fromarray(np.clip(arr, 0, 255).astype("uint8")).save(path, quality=90)


def paper(base: tuple, w: int, h: int, fibres: int = 900, vignette: float = 0.35) -> np.ndarray:
    blot, mid = blur_noise(w, h, 60, 40) - 0.5, blur_noise(w, h, 12, 6) - 0.5
    img = np.array(base, np.float32)[None, None, :] + blot[..., None] * 34 + mid[..., None] * 12 + rng.normal(0, 4, (h, w, 1))
    fib = Image.new("L", (w, h), 0); d = ImageDraw.Draw(fib)
    for _ in range(fibres):
        x, y, a, l = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(0, np.pi), rng.uniform(8, 40)
        d.line([(x, y), (x + np.cos(a) * l, y + np.sin(a) * l)], fill=int(rng.uniform(30, 90)), width=1)
    img -= np.asarray(fib.filter(ImageFilter.GaussianBlur(0.6)), np.float32)[..., None] * 0.15
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w * 0.75)) ** 2 + ((yy - h / 2) / (h * 0.75)) ** 2)
    return img * (1 - np.clip(r - 0.35, 0, 1) * vignette)[..., None]


def speckle(base: tuple, w: int, h: int, spread: float, dots: int, dot_colors: list, rmax: int) -> np.ndarray:
    img = np.array(base, np.float32)[None, None, :] + (blur_noise(w, h, 8, 3)[..., None] - 0.5) * spread + rng.normal(0, 10, (h, w, 1))
    im = Image.fromarray(np.clip(img, 0, 255).astype("uint8")); d = ImageDraw.Draw(im)
    for _ in range(dots):
        x, y, r = rng.uniform(0, w), rng.uniform(0, h), rng.uniform(1, rmax)
        c = dot_colors[rng.integers(len(dot_colors))]
        d.ellipse([x - r, y - r * rng.uniform(0.6, 1), x + r, y + r], fill=tuple(int(v + rng.uniform(-12, 12)) for v in c))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(0.4)), np.float32)


def torn(w: int, h: int, color: tuple, seed: int) -> Image.Image:
    r2 = np.random.default_rng(seed); im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pts = [(x, 6 + r2.uniform(0, 10)) for x in range(0, w + 1, 6)] + [(x, h - 6 - r2.uniform(0, 10)) for x in range(w, -1, -6)]
    d.polygon(pts, fill=color)
    return im


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("out_dir", type=Path)
    o = p.parse_args().out_dir
    o.mkdir(parents=True, exist_ok=True)
    save(paper((236, 230, 216), W, H, 700, 0.25), o / "paper-light.jpg")
    save(paper((217, 204, 176), W, H), o / "paper.jpg")
    save(paper((128, 96, 66), W, H, 300, 0.5), o / "kraft.jpg")
    Image.fromarray((128 + rng.normal(0, 38, (H // 2, W // 2))).clip(0, 255).astype("uint8")).resize((W, H), Image.NEAREST).save(o / "grain.png")
    ht = Image.new("LA", (W, H), (0, 0)); d = ImageDraw.Draw(ht); field = blur_noise(W, H, 30, 25)
    for y in range(0, H, 9):
        for x in range(0, W, 9):
            rad = 0.6 + field[y, x] * 2.6
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=(20, 255))
    ht.save(o / "halftone.png")
    tw, th = 1200, 900
    save(speckle((52, 52, 54), tw, th, 30, 9000, [(90, 90, 92), (25, 25, 27), (120, 118, 112)], 3), o / "asphalt.jpg")
    save(speckle((112, 82, 56), tw, th, 50, 3000, [(80, 58, 38), (140, 108, 78), (60, 44, 30)], 4), o / "soil.jpg")
    save(speckle((150, 146, 138), tw, th, 40, 7000, [(110, 106, 100), (185, 180, 170), (90, 88, 84), (200, 196, 186)], 9), o / "gravel.jpg")
    save(speckle((96, 140, 72), tw, th, 40, 6000, [(70, 116, 52), (122, 166, 88), (58, 96, 44)], 3), o / "grass.jpg")
    grain = blur_noise(tw, th, 40, 2)
    wood = np.array((160, 112, 66), np.float32)[None, None, :] + (np.sin(np.linspace(0, 60, th))[:, None] * 0.5 + grain - 0.5)[..., None] * 40
    save(wood, o / "wood.jpg")
    torn(900, 170, (22, 21, 19, 255), 1).save(o / "torn-black.png")
    torn(900, 170, (238, 231, 214, 255), 2).save(o / "torn-white.png")
    print(f"textures -> {o}")


if __name__ == "__main__":
    main()
