"""Extract frames from style/reference.mp4, build contact sheets and print pacing stats.

Usage: python3 analyze_reference.py [--video style/reference.mp4] [--fps 4] [--diff 18]
Samples the video at --fps, marks an image change when the mean pixel difference from
the last kept frame exceeds --diff (works for hard cuts and crossfades, ignores slow zooms
better than per-frame scene scores). Outputs work/ref_frames/cut_####.jpg and sheet_##.jpg.
"""
import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from common import SKILL_DIR, WORK_DIR, media_duration
from contact_sheet import build_sheets


def diff(a, b):
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=str(SKILL_DIR / "style" / "reference.mp4"))
    ap.add_argument("--fps", type=float, default=4)
    ap.add_argument("--diff", type=float, default=18)
    args = ap.parse_args()

    out = WORK_DIR / "ref_frames"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()

    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["ffmpeg", "-v", "error", "-i", args.video, "-vf", f"fps={args.fps},scale=640:-2",
                        "-q:v", "3", f"{tmp}/f_%05d.jpg"], check=True)
        frames = sorted(Path(tmp).glob("f_*.jpg"))
        kept, times, last, pending = [], [], None, None
        for i, f in enumerate(frames):
            im = Image.open(f).convert("RGB").resize((160, 90))
            if last is None:
                kept.append(f), times.append(0.0)
                last = im
                continue
            if diff(im, last) <= args.diff:
                pending = None  # still the same image (zoom/pan drift)
                continue
            # Different from the current image: accept once two samples in a row agree,
            # so the middle of a crossfade is never taken as a new image.
            if pending and diff(im, pending[2]) <= args.diff / 2:
                kept.append(pending[1]), times.append(pending[0] / args.fps)
                last, pending = pending[2], None
            else:
                pending = (i, f, im)
        if pending:
            kept.append(pending[1]), times.append(pending[0] / args.fps)
        paths = []
        for n, f in enumerate(kept, 1):
            dest = out / f"cut_{n:04d}.jpg"
            dest.write_bytes(f.read_bytes())
            paths.append(dest)

    total = media_duration(args.video)
    gaps = [b - a for a, b in zip(times, times[1:] + [total])]
    print(f"duration {total:.1f}s, images {len(times)}")
    gs = sorted(gaps)
    print(f"seconds per image: avg {sum(gaps) / len(gaps):.2f}, median {gs[len(gs) // 2]:.2f}, "
          f"min {gs[0]:.2f}, max {gs[-1]:.2f}")
    sheets = build_sheets(paths, out / "sheet", labels=[f"{t:.1f}s" for t in times])
    print("contact sheets:", *sheets, sep="\n  ")


if __name__ == "__main__":
    main()
