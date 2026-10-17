"""Image + per-scene audio (+ scene SFX from sfx/) -> final.mp4.
Each image lasts exactly as long as its scene audio.

Usage: python3 assemble.py work/<slug>/scenes.json [--music bed.mp3]

The look of every video is fixed by EFFECTS below (approved by the user on the 40 s
test). Do not change these values unless the user asks.
"""
import argparse
import subprocess
from pathlib import Path

from common import SKILL_DIR, load_project, media_duration, scene_name

EFFECTS = {
    "size": (1920, 1080),
    "fps": 30,
    "zoom_max": 1.08,     # slow zoom between 1.00 and 1.08 over the whole scene
    "zoom_alternate": True,  # even scenes zoom in, odd scenes zoom out
    "fade": 0.4,          # crossfade between scenes, seconds
    "pad": 0.15,          # silence after each scene's narration, seconds
    "music_db": -22,      # music bed level before ducking under the voice
    "sfx_db": -8,         # default sound-effect level
    "crf": 20,
    "preset": "medium",
}


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def sfx_inputs(sfx, dur):
    """Scene sound effects from the downloaded library: [{"file", "at", "db", "len"}]."""
    args, chains, labels = [], [], []
    for k, fx in enumerate(sfx or [], start=2):
        path = Path(fx["file"])
        if not path.is_absolute():
            path = SKILL_DIR / path
        args += ["-i", str(path)]
        at_ms = int(float(fx.get("at", 0)) * 1000)
        length = min(float(fx.get("len", dur)), dur)
        chains.append(f"[{k}:a]atrim=0:{length:.3f},afade=t=out:st={max(0, length - 0.3):.3f}:d=0.3,"
                      f"volume={fx.get('db', EFFECTS['sfx_db'])}dB,adelay={at_ms}|{at_ms},aformat=channel_layouts=stereo[fx{k}]")
        labels.append(f"[fx{k}]")
    return args, chains, labels


def scene_clip(img, audio, dest, dur, idx, sfx=None):
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
    fx_args, fx_chains, fx_labels = sfx_inputs(sfx, dur)
    voice = f"[1:a]aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}"
    if fx_labels:
        audio_graph = (f"{voice}[vo];" + ";".join(fx_chains) +
                       f";[vo]{''.join(fx_labels)}amix=inputs={1 + len(fx_labels)}:duration=first:normalize=0[a]")
    else:
        audio_graph = f"{voice}[a]"
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(fps), "-i", str(img), "-i", str(audio), *fx_args,
         "-filter_complex", f"[0:v]{vf}[v];{audio_graph}",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", EFFECTS["preset"], "-crf", str(EFFECTS["crf"]), "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    ap.add_argument("--music")
    args = ap.parse_args()
    fade, pad = EFFECTS["fade"], EFFECTS["pad"]

    root, project = load_project(args.scenes)
    clips_dir = root / "clips"
    clips_dir.mkdir(exist_ok=True)
    clips, durs = [], []
    for i, s in enumerate(project["scenes"]):
        name = scene_name(s["id"])
        img, audio = root / "images" / f"{name}.png", root / "audio" / f"{name}.mp3"
        missing = [p.name for p in (img, audio) if not p.exists()]
        if missing:
            raise SystemExit(f"{name}: missing {missing}")
        # The crossfade eats `fade` seconds from the end of the clip, so add it back.
        dur = media_duration(audio) + pad + (fade if i < len(project["scenes"]) - 1 else 0)
        dest = clips_dir / f"{name}.mp4"
        scene_clip(img, audio, dest, dur, i, s.get("sfx"))
        clips.append(dest)
        durs.append(dur)
        print(f"{name}: {dur:.2f}s")

    body = root / "body.mp4"
    if len(clips) == 1 or fade <= 0:
        lst = root / "clips.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
    else:
        inputs, fv, fa = [], [], []
        for c in clips:
            inputs += ["-i", str(c)]
        prev_v, prev_a, offset = "0:v", "0:a", 0.0
        for k in range(1, len(clips)):
            offset += durs[k - 1] - fade
            fv.append(f"[{prev_v}][{k}:v]xfade=transition=fade:duration={fade}:offset={offset:.3f}[v{k}]")
            fa.append(f"[{prev_a}][{k}:a]acrossfade=d={fade}[a{k}]")
            prev_v, prev_a = f"v{k}", f"a{k}"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fv + fa),
             "-map", f"[{prev_v}]", "-map", f"[{prev_a}]",
             "-c:v", "libx264", "-preset", EFFECTS["preset"], "-crf", str(EFFECTS["crf"]), "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(body)])

    final = root / "final.mp4"
    if args.music:
        # Loop the music under the whole video and duck it under the narration.
        run(["ffmpeg", "-y", "-i", str(body), "-stream_loop", "-1", "-i", args.music,
             "-filter_complex",
             f"[1:a]volume={EFFECTS['music_db']}dB[m];[m][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[md];"
             f"[0:a][md]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(final)])
    else:
        body.replace(final)
    print("final:", final, f"{media_duration(final):.1f}s")


if __name__ == "__main__":
    main()
