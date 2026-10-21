"""Scenes drawn as the continuation of an earlier frame -> images/scene_###.png

Usage:
  python3 chain.py work/<slug>/scenes.json [--only 5,6] [--force] [--tag t2]

A scene with "after": <id> is drawn from the finished image of scene <id> instead of from the location
and creature references: only the hero reference and that frame are attached (plus "new_refs", the
characters that first appear in this scene). The model keeps everything of that frame - the same
creatures at the same size, the same place, colours and style - and changes only what the scene
describes. Scenes without "after" are made by images.py as usual; run images.py first.
Scenes are made one by one in id order, because each one needs the frame before it. --tag changes the
Idempotency-Key, so a retry of a failed or bad frame makes a new picture.
"""
import argparse
import sys

from common import load_project, scene_name
from images import REF_RULES, as_image_input, ref_label, run_jobs

CONTINUE = ("Reference 2 is the previous frame of this video. This picture is the next frame and continues it: "
            "keep everything from Reference 2 exactly as it is there - every character and animal with the same "
            "look and the same size next to {hero}, the same place, trees, hill and ground, the same colours and "
            "the same drawing style. Change only what the SCENE below describes: what happens, the poses, the "
            "camera framing, the weather and the time of day. This is a new shot, never a copy of Reference 2: "
            "the pose of every character and the camera framing follow the SCENE.")


def build_prompt(project, scene, tag=""):
    hero = ref_label(project, "hero")
    new = scene.get("new_refs", [])
    notes = project.get("ref_notes", {})
    parts = [f"REFERENCE IMAGES: {2 + len(new)} reference images are attached, in this order:",
             REF_RULES["hero"].format(n=1, name=hero), CONTINUE.format(hero=hero)]
    for i, k in enumerate(new):
        name = ref_label(project, k)
        nums = {key: n for n, key in enumerate(["hero", "_prev"] + new, 1)}
        note = notes.get(k, "").format_map(type("Nums", (dict,), {"__missing__": lambda self, key: "?"})(nums))
        parts.append(REF_RULES["character"].format(n=3 + i, name=name) + (f" {note}" if note else "")
                     + f" {name} appears for the first time in this frame.")
    if project.get("setting"):
        parts.append(f"SETTING: {project['setting']}")
    parts.append(f"SCENE: {scene['prompt']}")
    if scene.get("in_frame"):
        parts.append("IN THE FRAME (every one of them must be clearly visible): " + "; ".join(scene["in_frame"]))
    if scene.get("text_in_image"):
        parts.append(f'The only text in the image is exactly: "{scene["text_in_image"]}" '
                     "in bold black capital sans-serif letters, spelled exactly as written.")
    else:
        parts.append("No text, letters or numbers anywhere in the image.")
    parts.append("16:9 frame, no watermark, no borders.")
    return "\n".join(parts) + (f" ~{tag}" if tag else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--tag", default="")
    ap.add_argument("--model", default="nano-banana-pro")
    args = ap.parse_args()

    root, project = load_project(args.scenes)
    img_dir = root / "images"
    only = {s.strip() for s in args.only.split(",")} if args.only else None
    for s in sorted(project["scenes"], key=lambda s: s["id"]):
        if "after" not in s or (only and str(s["id"]) not in only):
            continue
        dest = img_dir / f"{scene_name(s['id'])}.png"
        if dest.exists() and not args.force:
            continue
        prev = img_dir / f"{scene_name(s['after'])}.png"
        if not prev.exists():
            sys.exit(f"scene {s['id']}: frame of scene {s['after']} is missing - make it first")
        refs = [project["refs"]["hero"], prev] + [project["refs"][k] for k in s.get("new_refs", [])]
        inp = {"prompt": build_prompt(project, s, args.tag), "aspect_ratio": "landscape",
               "reference_image_urls": [as_image_input(r) for r in refs]}
        if not run_jobs([(scene_name(s["id"]), inp, [dest])], args.model):
            sys.exit(f"scene {s['id']} failed - check it and rerun with --tag")


if __name__ == "__main__":
    main()
