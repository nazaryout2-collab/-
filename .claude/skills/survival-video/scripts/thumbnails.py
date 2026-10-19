"""YouTube thumbnail candidates in the competitor's thumbnail style -> thumbnails/thumb_##.png

Usage: python3 thumbnails.py work/<slug>/thumbnails.json [--only 1,2] [--force]

thumbnails.json (written by you for each finished video, 10 ideas by default):
  [{"text": "1 YEAR", "idea": "what is in the frame: the hero big, one key story element behind"}]
Every job gets refs/hero.png and refs/thumbnail_style.jpg. Same API rules as images.py.
"""
import argparse
import json
from pathlib import Path

from common import SKILL_DIR
from images import REF_RULES, STYLE, as_image_input, run_jobs

THUMB_REF = "refs/thumbnail_style.jpg"

THUMB_RULES = (
    "This is a YouTube thumbnail. Copy the thumbnail layout of the image labelled THUMBNAIL STYLE REFERENCE: "
    "the hero big and close (head and upper body fill about a third to a half of the frame), one clear story "
    "element behind or beside him, a simple uncluttered background, and the text in huge bold condensed "
    "sans-serif capital letters in a free corner, readable at a very small size. Use that reference ONLY for "
    "layout, text placement and composition: do not copy its objects, backgrounds, brightness or time of day, "
    "and ignore every person in it completely (never take a cap, hair, face or clothes from it); the only hero "
    "is the one in the HERO reference."
)


def build(item):
    parts = [STYLE["style_block"], THUMB_RULES, f"THUMBNAIL: {item['idea']}", REF_RULES["hero"]]
    if item.get("text"):
        parts.append(f'The only text in the image is exactly: "{item["text"]}", spelled exactly as written.')
    else:
        parts.append("No text, letters or numbers anywhere in the image.")
    parts.append("16:9 frame, no watermark, no borders, no YouTube interface.")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("thumbnails")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default="nano-banana-pro")
    args = ap.parse_args()

    path = Path(args.thumbnails).resolve()
    ideas = json.loads(path.read_text(encoding="utf-8"))
    out_dir = path.parent / "thumbnails"
    only = {int(x) for x in args.only.split(",")} if args.only else None
    refs = [as_image_input(SKILL_DIR / "refs" / "hero.png"), as_image_input(SKILL_DIR / THUMB_REF)]
    items = []
    for n, item in enumerate(ideas, 1):
        dest = out_dir / f"thumb_{n:02d}.png"
        if (only and n not in only) or (dest.exists() and not args.force):
            continue
        inp = {"prompt": build(item), "aspect_ratio": "landscape", "reference_image_urls": refs}
        items.append((f"thumb_{n:02d}", inp, [dest]))
    print(f"{len(items)} thumbnails to generate")
    run_jobs(items, args.model)


if __name__ == "__main__":
    main()
