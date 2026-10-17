import json
import os
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
WORK_DIR = SKILL_DIR / "work"

# Keys may live in the git-ignored work/.env; real environment variables win.
_env = WORK_DIR / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        if "=" in _line and not _line.lstrip().startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def load_project(scenes_path):
    path = Path(scenes_path).resolve()
    project = json.loads(path.read_text(encoding="utf-8"))
    return path.parent, project


def scene_name(scene_id):
    return f"scene_{int(scene_id):03d}"


def media_duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out.strip())
