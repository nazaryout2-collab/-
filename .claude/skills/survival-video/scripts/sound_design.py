"""Lay the sound design over an assembled video without re-rendering the picture.

Usage: python3 sound_design.py work/<slug>/scenes.json [--video body.mp4] [--out final_sd.mp4]

scenes.json:
  "sound": {
    "ambience": [[first_scene, last_scene, "sfx/mixkit/x.mp3", db], ...],   # looped beds
    "music":    [[first_scene, last_scene, "sfx/music/y.mp3", db], ...]      # looped, 2 s fades
  }
  scene "sfx": [{"file", "at" (s from scene start), "db", "len"}]           # one-shots
Scene start times follow assemble.py exactly (narration + pad, crossfade overlap).
The bed (ambience + music + one-shots) is gently ducked under the narration.
"""
import argparse
import subprocess
from pathlib import Path

from assemble import EFFECTS
from common import SKILL_DIR, load_project, media_duration, scene_name

BED_FADE = 1.5     # fade in/out of ambience beds, s
MUSIC_FADE = 2.5   # fade in/out of music sections, s
VOICE_LUFS = -16   # narration level before the bed is added
FINAL_LUFS = -14   # YouTube loudness target


def integrated_lufs(path):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path), "-map", "0:a", "-af", "ebur128",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(err.rsplit("I:", 1)[1].split("LUFS")[0])


def scene_times(root, scenes):
    fade, pad = EFFECTS["fade"], EFFECTS["pad"]
    starts, ends, t = {}, {}, 0.0
    for i, s in enumerate(scenes):
        dur = media_duration(root / "audio" / f"{scene_name(s['id'])}.mp3") + pad
        starts[s["id"]] = t
        ends[s["id"]] = t + dur
        t += dur + (fade if i < len(scenes) - 1 else 0) - fade
    return starts, ends


def src(path):
    p = Path(path)
    return p if p.is_absolute() else SKILL_DIR / p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    ap.add_argument("--video", default="body.mp4")
    ap.add_argument("--out", default="final_sd.mp4")
    args = ap.parse_args()

    root, project = load_project(args.scenes)
    scenes = project["scenes"]
    starts, ends = scene_times(root, scenes)
    video = root / args.video
    total = media_duration(video)

    inputs, chains, labels = ["-i", str(video)], [], []

    def add(path, start, length, db, loop, fade_in, fade_out):
        k = len(labels) + 1  # input 0 is the video
        inputs.extend((["-stream_loop", "-1"] if loop else []) + ["-i", str(src(path))])
        length = max(0.1, min(length, total - start))
        ms = int(start * 1000)
        chains.append(
            f"[{k}:a]aformat=sample_rates=48000:channel_layouts=stereo,atrim=0:{length:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, length - fade_out):.3f}:d={fade_out},"
            f"volume={db}dB,adelay={ms}|{ms}[s{k}]")
        labels.append(f"[s{k}]")

    snd = project.get("sound", {})
    for first, last, path, db in snd.get("ambience", []):
        add(path, starts[first], ends[last] - starts[first], db, True, BED_FADE, BED_FADE)
    for first, last, path, db in snd.get("music", []):
        add(path, starts[first], ends[last] - starts[first], db, True, MUSIC_FADE, MUSIC_FADE)
    for s in scenes:
        for fx in s.get("sfx", []):
            t0 = starts[s["id"]] + float(fx.get("at", 0))
            length = float(fx.get("len", media_duration(src(fx["file"]))))
            add(fx["file"], t0, length, fx.get("db", EFFECTS["sfx_db"]), False, 0.05, min(0.4, length / 3))

    # Bring the narration to VOICE_LUFS first, so every bed level is relative to the voice.
    vgain = VOICE_LUFS - integrated_lufs(video)
    graph = ";".join(chains)
    graph += f";{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[bed]"
    graph += f";[0:a]volume={vgain:.2f}dB,asplit=2[voice][key]"
    graph += ";[bed][key]sidechaincompress=threshold=0.04:ratio=3:attack=30:release=600[bedd]"
    graph += (";[voice][bedd]amix=inputs=2:duration=first:normalize=0,"
              f"loudnorm=I={FINAL_LUFS}:TP=-1.5:LRA=11,aresample=48000[a]")

    script = root / "sound_graph.txt"
    script.write_text(graph)
    out = root / args.out
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex_script", str(script),
                    "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{total:.3f}", str(out)], check=True)
    print(f"{out}: {media_duration(out):.1f}s, {len(labels)} sound layers")


if __name__ == "__main__":
    main()
