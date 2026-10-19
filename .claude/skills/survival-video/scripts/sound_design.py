"""Lay the sound design over an assembled video without re-rendering the picture.

Usage: python3 sound_design.py work/<slug>/scenes.json --video final.mp4 [--parts sfx,music,ambience] [--out final_sd.mp4]
--parts picks the layers the user asked for (default: all three).

scenes.json:
  "sound": {
    "ambience": [[first_scene, last_scene, "sfx/mixkit/x.mp3", db], ...],   # looped beds
    "music":    [[first_scene, last_scene, "sfx/music/y.mp3", db], ...]      # looped, 2 s fades
  }
  scene "sfx": [{"file", "at" (s from scene start), "db", "len"}]           # one-shots
Scene start times follow assemble.py exactly (narration + pad, crossfade overlap).
No ducking; the master gets a static gain to FINAL_LUFS and a peak limiter.
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
    ap.add_argument("--parts", default="sfx,music,ambience",
                    help="comma list of layers to add: sfx (one-shots), music, ambience (wind, fire, room tone)")
    ap.add_argument("--bed-only", action="store_true", help="write the bed without the voice to sound_bed.wav, for level checks")
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

    parts = {p.strip() for p in args.parts.split(",") if p.strip()}
    snd = project.get("sound", {})
    for first, last, path, db in (snd.get("ambience", []) if "ambience" in parts else []):
        add(path, starts[first], ends[last] - starts[first], db, True, BED_FADE, BED_FADE)
    for first, last, path, db in (snd.get("music", []) if "music" in parts else []):
        add(path, starts[first], ends[last] - starts[first], db, True, MUSIC_FADE, MUSIC_FADE)
    for s in scenes:
        for fx in (s.get("sfx", []) if "sfx" in parts else []):
            t0 = starts[s["id"]] + float(fx.get("at", 0))
            length = float(fx.get("len", media_duration(src(fx["file"]))))
            add(fx["file"], t0, length, fx.get("db", EFFECTS["sfx_db"]), False, 0.05, min(0.4, length / 3))

    # Bring the narration to VOICE_LUFS first, so every bed level is relative to the voice.
    vgain = VOICE_LUFS - integrated_lufs(video)
    if not labels:  # nothing chosen: a silent bed keeps the graph the same
        inputs += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=48000:cl=stereo"]
        chains.append(f"[{len(labels) + 1}:a]anull[s1]")
        labels.append("[s1]")
    graph = ";".join(chains)
    graph += f";{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[bed]"
    # No ducking: pumping the bed between phrases made the wind swell every few seconds
    # and sound like a short loop. Bed levels are set relative to the voice instead.
    graph += f";[0:a]volume={0 if args.bed_only else f'{vgain:.2f}dB'}[voice]"
    graph += ";[voice][bed]amix=inputs=2:duration=first:normalize=0,aresample=48000[a]"

    script = root / "sound_graph.txt"
    script.write_text(graph)
    premix = root / "sound_premix.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex_script", str(script),
                    "-map", "[a]", "-t", f"{total:.3f}", "-c:a", "pcm_s24le", str(premix)], check=True)
    if args.bed_only:
        premix.replace(root / "sound_bed.wav")
        print(root / "sound_bed.wav")
        return
    # Static gain to FINAL_LUFS plus a peak limiter. Single-pass loudnorm is dynamic: it lifts
    # the pauses between phrases, so any cut to the wind or music was partly undone.
    gain = FINAL_LUFS - integrated_lufs(premix)
    out = root / args.out
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(video), "-i", str(premix),
                    "-map", "0:v", "-map", "1:a", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{total:.3f}", str(out)], check=True)
    premix.unlink()
    print(f"{out}: {media_duration(out):.1f}s, {len(labels)} sound layers")


if __name__ == "__main__":
    main()
