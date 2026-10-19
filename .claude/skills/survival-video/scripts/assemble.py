"""Image + per-scene narration -> final.mp4 (voice only).
Each image lasts exactly as long as its scene audio. Music, ambience and scene sound
effects are added afterwards by sound_design.py, never here (they would play twice).

Usage: python3 assemble.py work/<slug>/scenes.json

The look of every video is fixed by EFFECTS below (approved by the user on the 40 s
test). Do not change these values unless the user asks.
"""
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from common import SKILL_DIR, load_project, media_duration, scene_name

EFFECTS = {
    "size": (1920, 1080),
    "fps": 30,
    "zoom_max": 1.08,     # slow zoom between 1.00 and 1.08 over the whole scene
    "zoom_alternate": True,  # even scenes zoom in, odd scenes zoom out
    "fade": 0.4,          # crossfade between scenes, seconds
    "pad": 0.15,          # silence after each scene's narration, seconds
    "sfx_db": -8,         # default one-shot level in sound_design.py
    "crf": 20,
    "preset": "medium",
    # Speed only (no visual effect): parallel scene renders, crossfade in blocks.
    "workers": 4,
    "batch": 20,
}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def scene_clip(img, audio, dest, dur, idx):
    w, h = EFFECTS["size"]
    fps, zmax = EFFECTS["fps"], EFFECTS["zoom_max"]
    frames = max(1, round(dur * fps))
    span = zmax - 1.0
    if EFFECTS["zoom_alternate"] and idx % 2 == 1:
        z = f"({zmax}-{span}*in/{frames})"
    else:
        z = f"(1+{span}*in/{frames})"
    # zoompan snaps its crop to whole pixels, which makes a slow zoom shake. perspective
    # samples the source with sub-pixel cubic interpolation, so the zoom is smooth.
    m = f"(1-1/{z})"
    corners = {"x0": f"W/2*{m}", "y0": f"H/2*{m}", "x1": f"W-W/2*{m}", "y1": f"H/2*{m}",
               "x2": f"W/2*{m}", "y2": f"H-H/2*{m}", "x3": f"W-W/2*{m}", "y3": f"H-H/2*{m}"}
    vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},"
          + "perspective=" + ":".join(f"{k}='{v}'" for k, v in corners.items())
          + ":interpolation=cubic:eval=frame,format=yuv420p")
    audio_graph = f"[1:a]aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}[a]"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps), "-i", str(img), "-i", str(audio),
         "-filter_complex", f"[0:v]{vf}[v];{audio_graph}",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", EFFECTS["preset"], "-crf", str(EFFECTS["crf"]), "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest)])


def xfade_chain(clips, durs, dest, fade):
    inputs, fv, fa = [], [], []
    for c in clips:
        inputs += ["-i", str(c)]
    prev_v, prev_a, offset = "0:v", "0:a", 0.0
    for k in range(1, len(clips)):
        offset += durs[k - 1] - fade
        fv.append(f"[{prev_v}][{k}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}[v{k}]")
        fa.append(f"[{prev_a}][{k}:a]acrossfade=d={fade}[a{k}]")
        prev_v, prev_a = f"v{k}", f"a{k}"
    if len(clips) == 1:
        run(["ffmpeg", "-y", "-i", str(clips[0]), "-c", "copy", str(dest)])
        return
    run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fv + fa),
         "-map", f"[{prev_v}]", "-map", f"[{prev_a}]",
         "-c:v", "libx264", "-preset", EFFECTS["preset"], "-crf", str(EFFECTS["crf"]), "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(dest)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    args = ap.parse_args()
    fade, pad = EFFECTS["fade"], EFFECTS["pad"]

    root, project = load_project(args.scenes)
    clips_dir = root / "clips"
    clips_dir.mkdir(exist_ok=True)
    jobs = []
    for i, s in enumerate(project["scenes"]):
        name = scene_name(s["id"])
        img, audio = root / "images" / f"{name}.png", root / "audio" / f"{name}.mp3"
        missing = [p.name for p in (img, audio) if not p.exists()]
        if missing:
            raise SystemExit(f"{name}: missing {missing}")
        # The crossfade eats `fade` seconds from the end of the clip, so add it back.
        dur = media_duration(audio) + pad + (fade if i < len(project["scenes"]) - 1 else 0)
        jobs.append((img, audio, clips_dir / f"{name}.mp4", dur, i))
    with ThreadPoolExecutor(max_workers=EFFECTS["workers"]) as pool:
        list(pool.map(lambda j: scene_clip(*j), jobs))
    clips, durs = [j[2] for j in jobs], [j[3] for j in jobs]
    print(f"{len(clips)} scene clips rendered")

    body = root / "body.mp4"
    if len(clips) == 1 or fade <= 0:
        lst = root / "clips.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
    else:
        # Crossfade in blocks of `batch` clips (in parallel), then crossfade the blocks.
        # Every clip except the very last already carries `fade` extra seconds, so each
        # block except the last must keep its tail for the join with the next block.
        b = EFFECTS["batch"]
        groups = [(k, clips[k:k + b], durs[k:k + b]) for k in range(0, len(clips), b)]

        def block(g):
            k, cs, ds = g
            dest = root / f"block_{k // b:03d}.mp4"
            xfade_chain(cs, ds, dest, fade)
            return dest

        with ThreadPoolExecutor(max_workers=EFFECTS["workers"]) as pool:
            blocks = list(pool.map(block, groups))
        if len(blocks) == 1:
            blocks[0].replace(body)
        else:
            xfade_chain(blocks, [media_duration(p) for p in blocks], body, fade)

    final = root / "final.mp4"
    body.replace(final)
    print("final:", final, f"{media_duration(final):.1f}s")


if __name__ == "__main__":
    main()
