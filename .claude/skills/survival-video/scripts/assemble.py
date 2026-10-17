"""Image + per-scene audio (+ scene SFX from sfx/) -> final.mp4.
Each image lasts exactly as long as its scene audio.

Usage: python3 assemble.py work/<slug>/scenes.json [--music bed.mp3] [--music-db -22]
       [--fade 0.4] [--pad 0.15] [--fps 30] [--size 1920x1080]
"""
import argparse
import subprocess
from pathlib import Path

from common import SKILL_DIR, load_project, media_duration, scene_name


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
                      f"volume={fx.get('db', -8)}dB,adelay={at_ms}|{at_ms},aformat=channel_layouts=stereo[fx{k}]")
        labels.append(f"[fx{k}]")
    return args, chains, labels


def scene_clip(img, audio, dest, dur, fps, w, h, idx, sfx=None):
    frames = max(1, round(dur * fps))
    # Alternate slow zoom-in / zoom-out with a gentle drift so stills feel alive.
    if idx % 2 == 0:
        z = f"min(1.0+0.08*on/{frames},1.08)"
    else:
        z = f"max(1.08-0.08*on/{frames},1.0)"
    vf = (f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,crop={w * 2}:{h * 2},"
          f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps={fps},"
          f"format=yuv420p")
    fx_args, fx_chains, fx_labels = sfx_inputs(sfx, dur)
    voice = f"[1:a]aformat=channel_layouts=stereo,apad=whole_dur={dur:.3f}"
    if fx_labels:
        audio_graph = (f"{voice}[vo];" + ";".join(fx_chains) +
                       f";[vo]{''.join(fx_labels)}amix=inputs={1 + len(fx_labels)}:duration=first:normalize=0[a]")
    else:
        audio_graph = f"{voice}[a]"
    run(["ffmpeg", "-y", "-loop", "1", "-i", str(img), "-i", str(audio), *fx_args,
         "-filter_complex", f"[0:v]{vf}[v];{audio_graph}",
         "-map", "[v]", "-map", "[a]", "-t", f"{dur:.3f}",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(fps),
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", str(dest)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    ap.add_argument("--music")
    ap.add_argument("--music-db", type=float, default=-22)
    ap.add_argument("--fade", type=float, default=0.4, help="crossfade between scenes, s")
    ap.add_argument("--pad", type=float, default=0.15, help="silence after each scene, s")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--size", default="1920x1080")
    args = ap.parse_args()
    w, h = map(int, args.size.split("x"))

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
        # The crossfade eats --fade seconds from the end of the clip, so add it back.
        dur = media_duration(audio) + args.pad + (args.fade if i < len(project["scenes"]) - 1 else 0)
        dest = clips_dir / f"{name}.mp4"
        scene_clip(img, audio, dest, dur, args.fps, w, h, i, s.get("sfx"))
        clips.append(dest)
        durs.append(dur)
        print(f"{name}: {dur:.2f}s")

    body = root / "body.mp4"
    if len(clips) == 1 or args.fade <= 0:
        lst = root / "clips.txt"
        lst.write_text("".join(f"file '{c}'\n" for c in clips))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(body)])
    else:
        inputs, fv, fa = [], [], []
        for c in clips:
            inputs += ["-i", str(c)]
        prev_v, prev_a, offset = "0:v", "0:a", 0.0
        for k in range(1, len(clips)):
            offset += durs[k - 1] - args.fade
            fv.append(f"[{prev_v}][{k}:v]xfade=transition=fade:duration={args.fade}:offset={offset:.3f}[v{k}]")
            fa.append(f"[{prev_a}][{k}:a]acrossfade=d={args.fade}[a{k}]")
            prev_v, prev_a = f"v{k}", f"a{k}"
        run(["ffmpeg", "-y", *inputs, "-filter_complex", ";".join(fv + fa),
             "-map", f"[{prev_v}]", "-map", f"[{prev_a}]",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(body)])

    final = root / "final.mp4"
    if args.music:
        # Loop the music under the whole video and duck it under the narration.
        run(["ffmpeg", "-y", "-i", str(body), "-stream_loop", "-1", "-i", args.music,
             "-filter_complex",
             f"[1:a]volume={args.music_db}dB[m];[m][0:a]sidechaincompress=threshold=0.05:ratio=8:attack=20:release=400[md];"
             f"[0:a][md]amix=inputs=2:duration=first:normalize=0[a]",
             "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(final)])
    else:
        body.replace(final)
    print("final:", final, f"{media_duration(final):.1f}s")


if __name__ == "__main__":
    main()
