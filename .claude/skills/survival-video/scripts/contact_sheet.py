"""Tile images into numbered contact sheets so many frames can be reviewed at once.

Usage: python3 contact_sheet.py <dir_or_glob> [--out work/sheet] [--cols 4] [--rows 3]
"""
import argparse
import glob
from pathlib import Path

from PIL import Image, ImageDraw


def build_sheets(paths, out_prefix, labels=None, cols=4, rows=3, tile_w=480):
    paths = [Path(p) for p in paths]
    tile_h = tile_w * 9 // 16
    per = cols * rows
    sheets = []
    for start in range(0, len(paths), per):
        sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + 22)), "white")
        draw = ImageDraw.Draw(sheet)
        for i, p in enumerate(paths[start:start + per]):
            im = Image.open(p).convert("RGB")
            im.thumbnail((tile_w, tile_h))
            x, y = (i % cols) * tile_w, (i // cols) * (tile_h + 22)
            sheet.paste(im, (x, y + 22))
            label = labels[start + i] if labels and start + i < len(labels) else ""
            draw.text((x + 4, y + 4), f"{start + i + 1}. {p.stem} {label}", fill="black")
        dest = Path(f"{out_prefix}_{start // per + 1:02d}.jpg")
        dest.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dest, quality=85)
        sheets.append(dest)
    return sheets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default="work/sheet")
    ap.add_argument("--cols", type=int, default=4)
    ap.add_argument("--rows", type=int, default=3)
    args = ap.parse_args()
    src = Path(args.src)
    paths = sorted(src.glob("*.png")) + sorted(src.glob("*.jpg")) if src.is_dir() else sorted(glob.glob(args.src))
    for s in build_sheets(paths, args.out, cols=args.cols, rows=args.rows):
        print(s)


if __name__ == "__main__":
    main()
