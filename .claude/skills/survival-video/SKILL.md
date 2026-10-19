---
name: survival-video
description: Produce an animated "X Survival N Days/1 Year" YouTube video (prehistoric / dinosaur settings) in the style of the reference competitor — script, scene table, voiceover (VoiceGen), images (RoyalTechno, multi-reference), sound from downloaded libraries, and FFmpeg assembly. Use whenever the user gives a video topic for the survival channel or asks to make, test or fix any step of this pipeline.
---

# Survival video pipeline

The user supplies every topic. Nothing about ideas or script style is stored here: you
analyse the competitor's script yourself at the start of every session (step 0) and write
your findings down for that session only. The picture style is the opposite: it is fixed
in `style/style.json` and never changes between videos.

Limits matter (the user is on a $20 plan): never look at generated images unless the
user asks, never run the full generation unless the user asks for it — prepare
everything, run only the small test the user approves, and hand over the exact commands.

Talk to the user in Russian; the narration itself is in English.

## New session setup (fresh container)

- Python packages: `pip install requests pillow`; FFmpeg must be installed (`ffmpeg -version`).
- Keys: `work/.env` is not in git. If it is missing, ask the user for the VoiceGen and
  RoyalTechno keys and write them there as `VOICEGEN_API_KEY=...` and
  `ROYALTECHNO_API_KEY=...`; never repeat them in chat.
- Sound files are not in git either: download what each video needs (see Sound design).

## Reference material

- `style/reference.mp4` — the competitor fragment the user supplied (picture, pacing, sound);
  the style reference collage is cut from it.
- `style/transcripts/` — both parts of the same competitor story ("Bunker Survival 1 Year",
  Part 1 and Part 2), with timestamps.
- `style/style.json` — the channel's fixed picture style: `style_block`, `shot_types`,
  `location_prompt`. Do not rewrite it; change it only when the user asks.
- `refs/hero.png` — the hero (M1), reused in every video.
- `refs/style_competitor.jpg` — style reference labelled "STYLE REFERENCE": a 3×2 collage of
  competitor frames from `style/reference.mp4` and our own approved frames (sources in
  `style/ref_sources/`). The STYLE rule says: drawing style only — no brightness, colour
  intensity, lighting or time of day from it, no objects, and ignore every person in it;
  the only hero is `refs/hero.png`.

## 0. Session start: analyse the script (always, before writing anything)

1. `python3 scripts/analyze_reference.py` → pacing stats of `style/reference.mp4`
   (seconds per image). The picture style is not analysed: it is fixed.
2. Read both transcripts completely, as one story, not as separate texts.
3. Write `work/style_notes.md` (session-only, not committed) with your own findings:
   - **The script as a whole**: the arc from the first line to the last line of Part 2;
     what each part promises, delivers and leaves open; how tension rises across the
     whole video, not only inside scenes; recurring motifs and callbacks (objects, times,
     sounds that come back later); how practical survival detail and mystery alternate.
   - **The transition between parts**: how Part 1 ends (which question is left open, how
     close to the end the last twist lands) and how Part 2 opens (recap or not, how fast it
     returns to the open question, which time marker it starts from, which time span it
     covers). Use the same mechanics when the user asks for a multi-part video, and end
     every Part 1 on an open hook of the same kind.
   - **Narration**: person and tense, hook in the first 30 s, numbers and supplies, time
     markers and escalation rhythm, sentence length, words per minute.
   - **Pacing**: seconds per image → words per scene.
   - **On-screen text**: where the reference puts numbers, labels or warnings in the frame.

## 1. Script

Write the script for the user's topic from your own `work/style_notes.md` (length,
structure and part transitions taken from the transcripts). Show it to the user as text
and wait for approval.

User preferences that always apply:
- Narration in English.
- The hook is shorter than 40 s.
- Images change slightly faster than the reference: ≈ 85% of its measured average
  seconds per image.

## 2. Locations (every new video, right after the script is approved)

1. List the places that recur in the script (shelter, cave, camp, river crossing…). A place
   that appears in 3+ scenes gets its own location reference; one-off places do not.
2. For each one: `python3 scripts/images.py --location <name> "<what the place looks like:
   layout, rocks, walls, key objects that must stay the same>"` → 4 candidates in
   `refs/candidates/loc_<name>_N.png` (fixed style + `refs/style_competitor.jpg`).
3. Show the candidates to the user; the chosen one becomes `refs/loc_<name>.png`.
   Locations belong to one video (`refs/loc_*` is git-ignored).
4. If the story changes a place later (a wall gets built, a fire goes out), describe the
   change in the scene prompt; do not make a new location ref for it.

## 3. Scene table → `work/<slug>/scenes.json`

```json
{
  "title": "Topic Survival 1 Year",
  "voice": {"template_id": "chosen by the user"},
  "resolution": null,
  "setting": "one line: era, landscape and its colours for this video (the style itself is fixed)",
  "refs": {"hero": "refs/hero.png", "style": "refs/style_competitor.jpg", "<place>": "refs/loc_<place>.png"},
  "ref_roles": {"hero": "hero", "style": "style", "<place>": "location"},
  "scenes": [
    {"id": 1, "text": "narration", "type": "<shot type>",
     "prompt": "what is in the frame: action, emotion, framing, props",
     "refs": ["hero", "<place>"], "text_in_image": "",
     "sfx": [{"file": "sfx/<pack>/<file>.mp3", "at": 0.0, "db": -8, "len": 4}]}
  ]
}
```

- One image per scene; words per scene = target seconds × narration words per second.
- `refs`: `hero` whenever the hero is visible; a location ref whenever the scene is in a
  recurring place; none for isolated objects/diagrams. Decide per scene.
- `text_in_image`: only where the reference uses on-screen text.
- `type`: one of the fixed shot types in `style/style.json` (`hero_location`, `object`,
  `big_text`, `closeup`).
- The `style` ref is attached to every scene automatically by `images.py`, together with
  the rule "use it only to understand the drawing style, transfer no objects from it".
  If an object from the style collage still shows up, regenerate that scene.
- Never use a competitor frame as a reference image: its objects leak into the frames.

## 4. Choices to ask the user (every new video)

- Voice: run `python3 scripts/voicegen.py --list`, show the saved templates, the user picks
  (last time: "Ниша финансы 1.2", template `2d0c42ad-885b-4833-91cf-e8f697c2b4d7`).
- Image resolution: offer the model default (cheapest, $0.02) or `2k`/`4k` (2x/4x).
  Default to the cheapest unless the user chooses otherwise.

## 5. New hero (only when the user asks for one)

`python3 scripts/images.py --refs-only "<prompt>" --out refs/candidates/<name> --count 4
--ref refs/style_competitor.jpg`. Show the candidates, the user picks; save as
`refs/hero.png`. The hero has one unique feature; everyone else is a plain stick figure.

## 6. Images: how one image request is built

`scripts/images.py` sends one job per scene to RoyalTechno (`nano-banana-pro`) with:
- `prompt` = the master prompt below;
- `reference_image_urls` = the files listed in the scene's `refs` (up to 10);
- `aspect_ratio: landscape`, plus `resolution` only if the user chose 2k/4k.

Master prompt (`build_prompt`):

```
<style_block from style/style.json>
SETTING: <setting of this video>
SHOT TYPE: <shot_types[type] from style/style.json>
SCENE: <scene prompt>
<one rule per reference role used in the scene: hero / location / style>
<exact text rule | "No text, letters or numbers anywhere in the image.">
16:9 frame, no watermark, no borders.
```

The reference rules are in `REF_RULES` in `scripts/images.py`: the hero must match the
HERO image exactly, with a strict ban on changing any part of his appearance (his
features are not described in words, the reference image is the only source), drawn only once, a location must keep the
layout of its LOCATION image, the STYLE image is used only for line weight and colouring.

### Known failure modes

Check for these on contact sheets only when the user asks for a check, and fix by
regenerating the scene with `--only <ids> --force` after tightening its prompt or refs:
- hero drawn twice in one frame;
- the hero's appearance differs from `hero.png` (missing mouth, eyes with whites or pupils,
  other hair or clothes);
- coloured or orange face from "firelight" or "glow" in the prompt;
- modern tools or objects in a prehistoric setting;
- objects copied from a reference image (style or location) into an unrelated scene;
- unrequested, extra or misspelt text;
- for diagram / icon scenes: an anchor object from the style ref appears — leave `refs` empty.

## 7. Test, then hand over

Run only a 3–5 scene test (`--only 1,2,3`) of voice and images and assemble it, so the user
can check. The full run is done by the user's command:

```
python3 scripts/voicegen.py work/<slug>/scenes.json
python3 scripts/images.py work/<slug>/scenes.json [--resolution 2k]
python3 scripts/assemble.py work/<slug>/scenes.json
python3 scripts/sound_design.py work/<slug>/scenes.json --video final.mp4 --parts <what the user chose>
```

When the user asks you to produce the whole video yourself, render it in parts and send
part 1 first so the user can check it before you continue.

### Sending videos to the user

Files above ~100 MB do not download on the user's phone. Send:
- the full video re-encoded to 720p (`scale=1280:720`, CRF 25), usually 60–75 MB;
- if 1080p is needed, the 1080p file cut into ~3.5-minute parts with
  `-c copy -f segment -segment_time 205` (each 55–70 MB);
- for a sound or picture fix, also a short fragment (20–90 s) of the changed place.

## Effects (fixed — approved on the 40 s test, identical in every video)

All values live in `EFFECTS` at the top of `scripts/assemble.py`; never change them
unless the user asks, and never pass ad-hoc overrides.

| Setting | Value |
|---|---|
| Output | 1920×1080, 30 fps, H.264 CRF 20 (preset medium), AAC 192k 48 kHz stereo |
| Image duration | exactly the scene's narration length + 0.15 s pad |
| Motion | slow zoom 1.00 → 1.08 over the scene; even scenes zoom in, odd scenes zoom out; centred |
| Zoom renderer | `perspective` filter, cubic sub-pixel interpolation (no `zoompan`: it shakes) |
| Transition | 0.4 s crossfade (`xfade=fade` + `acrossfade`) |

Output `work/<slug>/final.mp4`.

## Sound design (after the picture is assembled)

Only when the user asks for it. After `final.mp4` is ready, send it and ask: no sound
design, effects only, or effects with music and ambience — and whether wind is wanted.
Then run with the chosen layers: `--parts sfx`, `--parts sfx,music`, `--parts sfx,music,ambience`
(for "no wind" leave the wind rows out of `sound.ambience`, keep fire / room tone).

Sound files are not kept in the repository. For every video download what it needs from
Mixkit (Sound Effects / Stock Music Free License, commercial use on YouTube allowed) or
CC0 sources into `sfx/<pack>/` (git-ignored) and list them in `sfx/INDEX.md`.
Mixkit file URLs: `https://assets.mixkit.co/active_storage/sfx/<id>/<id>-preview.mp3`
(effects), `https://assets.mixkit.co/music/<id>/<id>.mp3` (music). On category pages
the preview URL comes before the title of its card.

`python3 scripts/sound_design.py work/<slug>/scenes.json --video final.mp4` → `final_sd.mp4`.
No picture re-render (video stream is copied). It reads `"sound": {"ambience": [...],
"music": [...]}` (`[first_scene, last_scene, file, db]`, looped, faded) and per-scene
one-shot `"sfx"`, places them on the real scene timeline, brings the voice to −16 LUFS (no
ducking) and the master to −14 LUFS (YouTube) with a static gain + peak limiter. Never
use single-pass `loudnorm` on the master: it is dynamic and lifts the pauses, undoing any
cut to wind or music.

- Wind is not a constant bed: only in outdoor scenes (soft in calm outdoor moments), none
  indoors, in close-ups, diagrams or quiet tense moments — there use room tone, fire or
  silence.
- Every growl or roar in one scene sequence is a different file.
- Tense moments get slightly louder one-shots than calm ones; the ending is quieter.
- Beds must be long files (30 s and more) or layered: a short loop is heard as a repeat.
- A key creature sound (a mammoth call, a roar) lasts about its scene, not a short blip.
- Footsteps only where the narration is about walking, and never several in a row.
- When the user asks for "N% quieter/louder", that is amplitude: dB = 20·log10(1 ± N/100)
  (−25% ≈ −2.5 dB). Apply it to the current level, then measure the result (bed level in
  the pauses between phrases, per section) and show the numbers. If the user says nothing
  changed, also send a short before/after clip (same 15 s, old then new).
- Music: cinematic documentary / mystery / suspense. No meditation, zen or fairy-tale tracks.

Levels are set by hand from measured loudness, never by a compressor (source files differ
by up to 10 dB, so equal dB settings do not sound equal):
- Music: `db = target − track LUFS`, target ≈ −45.5 LUFS (predator / ending ≈ −48).
- Continuous bed (music + ambience) per section ≈ −43 LUFS, calm −45..−47, storm ≈ −37.
  Check with `sound_design.py <scenes> --video final.mp4 --bed-only` on a copy of
  scenes.json without one-shots, then `ebur128` per section.
- One-shots by max momentary loudness (file M-max + db): big roars/attacks ≈ −14,
  tense hits and heartbeats ≈ −17, actions ≈ −21, small details (steps, twigs) ≈ −25.

## Keys and costs

- Keys are read from `work/.env` (`VOICEGEN_API_KEY`, `ROYALTECHNO_API_KEY`); `work/` is
  git-ignored. Never put keys in other files, commits or chat.
- RoyalTechno rules: poll images every 5 s with `If-None-Match`, ≤ 20 jobs in flight,
  one `Idempotency-Key` per job, stop on 400/401/402/403, retry only 429/503.
- VoiceGen results expire after 3 days: download immediately.
