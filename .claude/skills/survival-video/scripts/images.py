"""RoyalTechno image jobs with multi-reference -> images/scene_###.png

Usage:
  python3 images.py work/<slug>/scenes.json [--only 1,2,3] [--force] [--model nano-banana-pro]
  python3 images.py --location cave "a narrow cave mouth high on a snowy hill, ..." [--count 4]
  python3 images.py --refs-only "prompt text" --out refs/candidates/hero --count 4 [--ref refs/x.png]
The picture style is fixed in style/style.json and is the same in every video.
Key: env ROYALTECHNO_API_KEY. Follows the API's client rules (poll 5 s with ETag,
<= 20 in flight, Idempotency-Key per job, stop on 4xx, retry only 429/503).
"""
import argparse
import base64
import json
import mimetypes
import os
import random
import sys
import time
import uuid
from pathlib import Path

import requests

from common import SKILL_DIR, load_project, scene_name

BASE = "https://api.royaltechno.cc"
MAX_IN_FLIGHT = 20
FATAL = {400, 401, 402, 403}

REF_RULES = {
    "hero": ("The hero is an exact copy of the HERO reference image. It is forbidden to change his appearance in any "
             "way: do not add, remove, simplify or redraw any part of his face, head, hair, headwear, clothing, colours, "
             "proportions or line style, in every pose, angle and emotion. Every feature visible on the reference stays "
             "visible. Draw the hero only ONCE in the frame."),
    "location": "The setting must match the LOCATION reference image: same layout, rock shapes, walls and objects.",
    "style": ("The STYLE reference image is given ONLY to understand the drawing style: line weight, colouring and "
              "shading. Do NOT transfer anything from it into this picture: no objects, machines, tanks, pipes, shelves, "
              "buildings, labels, text or layout. Draw only what the SCENE describes."),
}


STYLE = json.loads((SKILL_DIR / "style" / "style.json").read_text())
STYLE_REF = "refs/style_competitor.jpg"


def build_prompt(project, scene):
    """Master prompt: fixed style + setting + shot type + scene + reference rules + text rule."""
    parts = [STYLE["style_block"]]
    if project.get("setting"):
        parts.append(f"SETTING: {project['setting']}")
    if scene.get("type"):
        parts.append(f"SHOT TYPE: {STYLE['shot_types'].get(scene['type'], scene['type'])}")
    parts.append(f"SCENE: {scene['prompt']}")
    roles = {project.get("ref_roles", {}).get(r, r) for r in scene.get("refs", [])}
    parts += [REF_RULES[r] for r in ("hero", "location", "style") if r in roles]
    if scene.get("text_in_image"):
        parts.append(f'The only text in the image is exactly: "{scene["text_in_image"]}" '
                     "in bold black capital sans-serif letters, spelled exactly as written.")
    else:
        parts.append("No text, letters or numbers anywhere in the image.")
    parts.append("16:9 frame, no watermark, no borders.")
    return "\n".join(parts)


def headers():
    key = os.environ.get("ROYALTECHNO_API_KEY")
    if not key:
        sys.exit("ROYALTECHNO_API_KEY is not set")
    return {"Authorization": "Bearer " + key}


def as_image_input(ref):
    """URLs pass through; local files become data URIs (5 MiB limit)."""
    if str(ref).startswith("https://"):
        return str(ref)
    path = Path(ref)
    if not path.is_absolute():
        path = SKILL_DIR / path
    data = path.read_bytes()
    if len(data) > 5 * 1024 * 1024:
        sys.exit(f"reference too large (>5 MiB): {path}")
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def submit(body, idem_key):
    for attempt in range(6):
        r = requests.post(BASE + "/v1/jobs", headers={**headers(), "Idempotency-Key": idem_key},
                          json=body, timeout=90)
        if r.status_code in FATAL:
            sys.exit(f"submit refused {r.status_code}: {r.text[:400]}")
        if r.status_code == 429:
            if "queue_full" in r.text:
                return None
            wait = max(float(r.headers.get("Retry-After", 5)), min(60, 2 ** attempt) * random.uniform(0.8, 1.2))
            time.sleep(wait)
            continue
        if r.status_code == 503:
            time.sleep(min(60, 2 ** attempt) * random.uniform(0.8, 1.2))
            continue
        r.raise_for_status()
        return r.json()
    sys.exit("submit: giving up after 6 attempts")


def job_id(job):
    return job.get("external_id") or job.get("id")


def output_urls(job):
    out = job.get("output") or {}
    if isinstance(out, list):
        return [o.get("url") for o in out if o.get("url")]
    if out.get("url"):
        return [out["url"]]
    return [o.get("url") for o in out.get("images", []) if o.get("url")]


def run_jobs(items, model, poll=5):
    """items: list of (name, body_input, dest_paths). Sliding window, single poll loop."""
    queue = list(items)
    inflight = {}
    etags = {}
    done = {}
    while queue or inflight:
        while queue and len(inflight) < MAX_IN_FLIGHT:
            name, inp, dests = queue[0]
            idem = str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps([model, name, inp], sort_keys=True)))
            job = submit({"model": model, "input": inp}, idem)
            if job is None:  # queue_full: wait for a slot
                break
            queue.pop(0)
            inflight[job_id(job)] = (name, dests)
        time.sleep(poll)
        for jid, (name, dests) in list(inflight.items()):
            h = headers()
            if jid in etags:
                h["If-None-Match"] = etags[jid]
            r = requests.get(f"{BASE}/v1/jobs/{jid}", headers=h, timeout=30)
            if r.status_code == 304:
                continue
            if r.status_code in (429, 503):
                time.sleep(float(r.headers.get("Retry-After", poll)))
                continue
            r.raise_for_status()
            etags[jid] = r.headers.get("ETag", "")
            job = r.json()
            status = job.get("status")
            if status in ("queued", "processing", "running"):
                continue
            del inflight[jid]
            if status != "succeeded":
                print(f"{name}: {status} {job.get('error')}")
                continue
            urls = output_urls(job)
            for url, dest in zip(urls, dests):
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(requests.get(url, timeout=120).content)
            done[name] = urls
            print("done", name, urls[:1], job.get("notice") or "")
    return done


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes", nargs="?")
    ap.add_argument("--only")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--model", default="nano-banana-pro")
    ap.add_argument("--resolution", help="omit for the model default (cheapest); e.g. 2k, 4k")
    ap.add_argument("--refs-only", metavar="PROMPT")
    ap.add_argument("--out", default="refs/candidates/ref")
    ap.add_argument("--count", type=int, default=4)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--location", nargs=2, metavar=("NAME", "DESCRIPTION"),
                    help="location reference candidates -> refs/candidates/loc_<NAME>_N.png")
    args = ap.parse_args()

    base_inp = {"aspect_ratio": "landscape"}
    if args.resolution:
        base_inp["resolution"] = args.resolution

    if args.location:
        name, desc = args.location
        args.refs_only = (STYLE["style_block"] + "\n" + STYLE["location_prompt"].format(description=desc)
                          + "\n" + REF_RULES["style"])
        args.out = f"refs/candidates/loc_{name}"
        args.ref = args.ref or [STYLE_REF]

    if args.refs_only:
        inp = {"prompt": args.refs_only, **base_inp}
        if args.ref:
            inp["reference_image_urls"] = [as_image_input(r) for r in args.ref]
        else:
            inp["count"] = args.count
        n = 1 if args.ref else args.count
        out = SKILL_DIR / args.out
        dests = [out.parent / f"{out.name}_{i + 1}.png" for i in range(n)]
        items = [("refs", inp, dests)] if not args.ref else \
            [(f"refs{i}", dict(inp), [dests[0].parent / f"{out.name}_{i + 1}.png"]) for i in range(args.count)]
        run_jobs(items, args.model)
        return

    root, project = load_project(args.scenes)
    img_dir = root / "images"
    only = {s.strip() for s in args.only.split(",")} if args.only else None
    items = []
    for s in project["scenes"]:
        name = scene_name(s["id"])
        dest = img_dir / f"{name}.png"
        if (only and str(s["id"]) not in only) or (dest.exists() and not args.force):
            continue
        # The style reference (and its "style only, copy nothing" rule) goes with every scene.
        if "style" in project.get("refs", {}) and "style" not in s.get("refs", []):
            s = {**s, "refs": s.get("refs", []) + ["style"]}
        prompt = build_prompt(project, s)
        inp = {"prompt": prompt, **base_inp}
        refs = [project["refs"][k] for k in s.get("refs", [])]
        if refs:
            inp["reference_image_urls"] = [as_image_input(r) for r in refs]
        items.append((name, inp, [dest]))
    print(f"{len(items)} images to generate with {args.model}")
    done = run_jobs(items, args.model)
    log = root / "images_log.json"
    prev = json.loads(log.read_text()) if log.exists() else {}
    prev.update(done)
    log.write_text(json.dumps(prev, indent=1))


if __name__ == "__main__":
    main()
