---
name: survival-video
description: Produce an animated "X Survival N Days/1 Year" YouTube video (prehistoric / dinosaur settings) in the style of the reference competitor — script, scene table, voiceover (VoiceGen), images (RoyalTechno, multi-reference), sound effects from a downloaded library, and FFmpeg assembly. Use whenever the user gives a video topic for the survival channel or asks to make, test or fix any step of this pipeline.
---

# Survival video pipeline

The user supplies every topic. Nothing about ideas is stored here: style, narration and
pacing are re-derived from the reference material at the start of each session.

Limits matter (the user is on a $20 plan): never look at generated images unless the
user asks, never run the full generation yourself — prepare everything, run only the
small test the user approves, and hand over the exact commands for the full run.

## 0. Session start: analyse the references (always, before writing anything)

1. `python3 scripts/analyze_reference.py` → frames of `style/reference.mp4` in
   `work/ref_frames/`, two contact sheets, pacing stats. Look at the contact sheets once.
2. Read both transcripts in `style/transcripts/`.
3. Write `work/style_notes.md` (session-only, not committed):
   - visual: line weight, palette, hero design, backgrounds, which shot types occur and
     how often, how on-screen text looks (font, colour, when it appears);
   - narration: person/tense, hook in the first 30 s, use of numbers and supplies,
     escalation rhythm (day markers), cliffhanger ending, words per minute;
   - pacing: seconds per image → words per scene.
   - `style_block` and `shot_types` for the master prompt (see below).

## 1. Script

Write the script for the user's topic following `work/style_notes.md` (length and
structure taken from the transcripts). Wait for the user's approval.

## 2. Scene table → `work/<slug>/scenes.json`

```json
{
  "title": "Ice Age Survival 1 Year",
  "voice": {"template_id": "chosen by the user"},
  "resolution": null,
  "style_block": "from step 0",
  "shot_types": {"hero_location": "...", "object": "...", "cutaway": "...", "big_text": "...", "closeup": "..."},
  "refs": {"hero": "refs/hero.png", "cave_main": "refs/cave_main.png"},
  "ref_roles": {"hero": "hero", "cave_main": "location"},
  "scenes": [
    {"id": 1, "text": "narration", "type": "hero_location",
     "prompt": "what is in the frame: action, emotion, framing, props",
     "refs": ["hero", "cave_main"], "text_in_image": "",
     "sfx": [{"file": "sfx/alarms/siren_01.mp3", "at": 0.0, "db": -8, "len": 4}]}
  ]
}
```

- One image per scene. Cut slightly faster than the reference: target ≈ 85% of its
  measured average seconds per image (words per scene = that time × narration words/s).
- The hook (before the first time-skip) is shorter than the reference's: ~20–25 s.
- Every character in a video (hero, other people, Neanderthals) is drawn in the same
  stick-figure style; only the hero carries his unique feature (`refs/hero.png`).
- `refs`: `hero` whenever the hero is visible; the location ref whenever the scene is in a
  recurring place; none for isolated objects/diagrams. Decide per scene.
- `text_in_image`: only where the reference uses on-screen text (numbers, labels, warnings).
- Style ref is `refs/style_neutral.png` (never a competitor frame: its objects leak into
  frames). For diagrams/icon scenes leave `refs` empty if an anchor object shows up.
- Known failure modes to check on contact sheets (only when the user asks for a check):
  hero drawn twice, eyes with whites/pupils, coloured face from "firelight", modern tools,
  objects copied from a reference, unrequested or misspelt text.
- `sfx`: pick files from `sfx/INDEX.md` where the reference would have a sound.

## 3. Choices to ask the user (every new video)

- Voice: run `python3 scripts/voicegen.py --list`, show the saved templates, the user picks.
- Image resolution: offer the model default (cheapest, $0.02) or `2k`/`4k` (2x/4x).
  Default to the cheapest unless the user chooses otherwise.

## 4. References (once per new hero / location)

`python3 scripts/images.py --refs-only "<prompt>" --out refs/candidates/<name> --count 4`
(add `--ref work/ref_frames/cut_0001.jpg` to anchor the style). The user picks; save as
`refs/<name>.png` and reuse in every later video.

## 5. Test, then hand over

Run only a 3–5 scene test (`--only 1,2,3`) of voice and images and assemble it, so the user
can check. The full run is done by the user's command:

```
python3 scripts/voicegen.py work/<slug>/scenes.json
python3 scripts/images.py work/<slug>/scenes.json [--resolution 2k]
python3 scripts/assemble.py work/<slug>/scenes.json [--music sfx/music/<bed>.mp3]
```

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
| SFX | per scene from `sfx/`, default −8 dB, 0.3 s fade-out |
| Music | optional bed at −22 dB, sidechain-ducked under the voice |

Output `work/<slug>/final.mp4`.

## Master prompt (built by `scripts/images.py::build_prompt`)

```
<style_block>
SHOT TYPE: <shot_types[type]>
SCENE: <prompt>
[hero ref rule] [location ref rule]
<exact text rule | "No text, letters or numbers anywhere in the image.">
16:9 frame, no watermark, no borders.
```

## Sound design (after the picture is assembled)

`python3 scripts/sound_design.py work/<slug>/scenes.json --video final.mp4` → `final_sd.mp4`.
No picture re-render (video stream is copied). It reads `"sound": {"ambience": [...],
"music": [...]}` (scene ranges, looped, faded) and per-scene one-shot `"sfx"`, places them
on the real scene timeline, ducks the bed under the narration, brings the voice to −16 LUFS
and the master to −14 LUFS (YouTube). Check bed vs voice per section with `volumedetect`:
speech sections ≈ 8–12 dB under the voice, storm/blizzard ≈ 5–7 dB under.
Wind is not a constant bed: only in outdoor scenes (soft in calm outdoor moments), none in
the cave, in close-ups, diagrams or quiet tense moments — there use fire crackle / cave room
tone or silence. Every growl or roar in one scene sequence is a different file.

## Sound library

Downloaded packs live in `sfx/<category>/` (not generated). `sfx/INDEX.md` lists each
file with a one-line description and length; keep it updated when packs are added.

## Keys and costs

- Keys only from env `VOICEGEN_API_KEY`, `ROYALTECHNO_API_KEY`. Never in files, commits, chat.
- RoyalTechno rules: poll images every 5 s with `If-None-Match`, ≤ 20 jobs in flight,
  one `Idempotency-Key` per job, stop on 400/401/402/403, retry only 429/503.
- VoiceGen results expire after 3 days: download immediately.
