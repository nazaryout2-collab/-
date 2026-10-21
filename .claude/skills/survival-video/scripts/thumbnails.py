"""YouTube thumbnail candidates in the competitor's thumbnail style -> thumbnails/thumb_##.png

Usage: python3 thumbnails.py work/<slug>/thumbnails.json [--only 1,2] [--force]

thumbnails.json (written by you for each finished video, 10 ideas by default):
  [{"text": "1 YEAR", "idea": "...", "refs": {"T-REX": "work/<slug>/refs/rex.png"}}]
"idea" names the hero CHARACTER 1 and creatures by their "refs" names; never describe their look.
Every job gets refs/hero_crop.png, any "refs" of the item, and refs/thumbnail_style.jpg (last);
"own_layout": true leaves out the competitor layout (reference and rules) for a different look.
Same API rules as images.py.
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
    "is CHARACTER 1."
)


def build(item):
    names = list(item.get("refs", {}))
    own = item.get("own_layout")
    total = 1 + len(names) + (0 if own else 1)
    head = [f"REFERENCE IMAGES: {total} reference images are attached, in this order:",
            REF_RULES["hero"].format(n=1, name="CHARACTER 1")]
    head += [REF_RULES["character"].format(n=2 + i, name=name) for i, name in enumerate(names)]
    if not own:
        head.append(f"Reference {total} is the THUMBNAIL STYLE REFERENCE.")
    style = STYLE["style_block"].replace("{hero}", "CHARACTER 1")
    if own:
        style = style.replace(" rendered like the STYLE reference", "")
    parts = ["\n".join(head), style] + ([] if own else [THUMB_RULES]) + [
        "This is a YouTube thumbnail, readable at a very small size." if own else "",
        f"THUMBNAIL: {item['idea']}", STYLE["quality_rule"].replace(", like in the STYLE reference", "")]
    if item.get("texts"):
        parts.append("The only texts in the image are exactly these, each written once, spelled exactly as written: "
                     + ", ".join(f'"{x}"' for x in item["texts"]) + ".")
    elif item.get("text"):
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
    items = []
    for n, item in enumerate(ideas, 1):
        dest = out_dir / f"thumb_{n:02d}.png"
        if (only and n not in only) or (dest.exists() and not args.force):
            continue
        refs = ([as_image_input(SKILL_DIR / "refs" / "hero_crop.png")]
                + [as_image_input(SKILL_DIR / p) for p in item.get("refs", {}).values()]
                + ([] if item.get("own_layout") else [as_image_input(SKILL_DIR / THUMB_REF)]))
        inp = {"prompt": build(item), "aspect_ratio": "landscape", "reference_image_urls": refs}
        items.append((f"thumb_{n:02d}", inp, [dest]))
    print(f"{len(items)} thumbnails to generate")
    run_jobs(items, args.model)


if __name__ == "__main__":
    main()
