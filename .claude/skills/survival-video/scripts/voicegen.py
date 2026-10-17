"""One VoiceGen task per scene -> audio/scene_###.mp3 (+ .srt).

Usage: python3 voicegen.py work/<slug>/scenes.json [--only 1,2,3] [--force]
Key: env VOICEGEN_API_KEY.
"""
import argparse
import json
import os
import sys
import time
import uuid

import requests

from common import load_project, scene_name

BASE = "https://api.qw1voicegencore.pro"


def headers():
    key = os.environ.get("VOICEGEN_API_KEY")
    if not key:
        sys.exit("VOICEGEN_API_KEY is not set")
    return {"Authorization": "Bearer " + key}


def check_account():
    r = requests.get(BASE + "/api/v1/client/me", headers=headers(), timeout=30)
    r.raise_for_status()
    return r.json()


def create_task(scene, voice, state):
    sid = str(scene["id"])
    # Reuse the same client_task_id on retries so the server deduplicates.
    client_id = state.setdefault(sid, {}).setdefault("client_task_id", str(uuid.uuid4()))
    body = {
        "text": scene["text"],
        "voice_id": voice["voice_id"],
        "voice_engine": "cartesia",
        "model_id": voice.get("model_id", "sonic-3.6"),
        "voice_engine_settings": {"speed": voice.get("speed", 100), "volume": voice.get("volume", 100)},
        "filename": scene_name(scene["id"]) + ".mp3",
        "result_format": "single",
        "include_timestamps": True,
        "timestamps_granularity": "word",
        "client_task_id": client_id,
    }
    if voice.get("voice_source"):
        body["voice_source"] = voice["voice_source"]
    r = requests.post(BASE + "/api/v1/client/tasks", headers=headers(), json=body, timeout=60)
    if r.status_code in (400, 401, 403, 404, 422):
        sys.exit(f"scene {sid}: {r.status_code} {r.text[:300]}")
    r.raise_for_status()
    task = r.json()["task"]
    state[sid]["task_id"] = task["task_id"]
    return task["task_id"]


def download(url, dest):
    with requests.get(url, headers=headers(), timeout=180, allow_redirects=True, stream=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for block in r.iter_content(1 << 16):
                f.write(block)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scenes")
    ap.add_argument("--only", help="comma-separated scene ids")
    ap.add_argument("--force", action="store_true", help="regenerate existing audio")
    args = ap.parse_args()

    root, project = load_project(args.scenes)
    audio_dir = root / "audio"
    audio_dir.mkdir(exist_ok=True)
    state_path = root / "voice_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    todo = [s for s in project["scenes"]
            if (only is None or str(s["id"]) in only)
            and (args.force or not (audio_dir / (scene_name(s["id"]) + ".mp3")).exists())]
    if args.force:
        for s in todo:
            state.pop(str(s["id"]), None)

    me = check_account()
    print("account:", {k: me.get(k) for k in ("max_threads", "free_generation_remaining_chars", "has_active_subscription")})
    print("chars to synthesise:", sum(len(s["text"]) for s in todo))

    pending = {}
    for s in todo:
        pending[str(s["id"])] = state.get(str(s["id"]), {}).get("task_id") or create_task(s, project["voice"], state)
        state_path.write_text(json.dumps(state, indent=1))

    while pending:
        time.sleep(3)
        for sid, task_id in list(pending.items()):
            r = requests.get(f"{BASE}/api/v1/client/tasks/{task_id}", headers=headers(), timeout=30)
            r.raise_for_status()
            task = r.json()["task"]
            if task["status"] in ("queued", "running"):
                continue
            del pending[sid]
            if task["status"] != "done":
                print(f"scene {sid}: {task['status']} {task.get('error_message')}")
                continue
            name = scene_name(sid)
            download(f"{BASE}/api/v1/client/tasks/{task_id}/download", audio_dir / f"{name}.mp3")
            if task.get("timestamps_url"):
                download(task["timestamps_url"], audio_dir / f"{name}.srt")
            print("done", name)
    state_path.write_text(json.dumps(state, indent=1))


if __name__ == "__main__":
    main()
