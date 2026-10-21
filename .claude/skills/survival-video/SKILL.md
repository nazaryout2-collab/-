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

**Disagreements and mistakes in this file: report, never fix silently.** If, after analysing
the reference video and transcripts (or at any later step), you disagree with a rule here,
or you find something inaccurate, outdated or contradictory in this file or in the
scripts, tell the user first: what the rule says, what you found, what you propose. Keep
following the current rule until the user decides; change the file only after the user
agrees.

## New session setup (fresh container)

- Python packages: `pip install requests pillow`; FFmpeg must be installed (`ffmpeg -version`).
- Keys are never stored in git. They come from the cloud environment's variables
  `VOICEGEN_API_KEY` and `ROYALTECHNO_API_KEY` (set once by the user in the environment
  settings, every new session gets them) or from the git-ignored `work/.env`. If neither is
  there, ask the user to add them in the environment settings; never repeat a key in chat.
- Sound files are not in git either: download what each video needs (see Sound design).

## Reference material

- `style/reference.mp4` — the competitor fragment the user supplied (picture, pacing, sound);
  the style reference collage is cut from it.
- `style/transcripts/` — both parts of the same competitor story ("Bunker Survival 1 Year",
  Part 1 and Part 2), with timestamps.
- `style/style.json` — the channel's fixed picture style: `style_block`, `shot_types`,
  `location_prompt`. Do not rewrite it; change it only when the user asks.
- `refs/hero.png` — the hero (M1), reused in every video. Scenes use `refs/hero_crop.png`, the
  same picture cropped tight so the figure fills it: with the small figure on a wide white canvas
  the model often redrew him as a bearded caveman or put a helmet on him (tested).
- `refs/thumbnail_style.jpg` — labelled collage of 6 competitor thumbnails (step 8).
- `refs/style_competitor.jpg` — style reference labelled "STYLE REFERENCE": a 3×2 collage of
  competitor frames from `style/reference.mp4` (their character graphically replaced by our
  hero) and our own approved frames; sources in `style/ref_sources/`. The STYLE rule says:
  drawing style only — no brightness, lighting or time of day from it, no objects.

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

## 2. Locations and recurring characters (every new video, right after the script is approved)

1. Go through the approved script and list:
   - places that recur (shelter, cave, camp, river crossing…);
   - characters and animals that recur (a T-rex, a wolf pack leader, a Neanderthal, a
     mammoth…), the hero excluded — he already has `refs/hero.png`.
   Anything that appears in **more than 2 scenes (3 or more)** gets its own reference;
   things in 1–2 scenes do not.
2. Show the user this list (name, what it looks like, which scenes) and wait for approval.
3. Generate candidates:
   - place: `python3 scripts/images.py --location <name> "<layout, rocks, walls, key objects
     that must stay the same>"` → `refs/candidates/loc_<name>_N.png`;
   - character / animal: `python3 scripts/images.py --character <name> "<species, body,
     colours, markings, distinctive details>"` → `refs/candidates/char_<name>_N.png`.
   Both use the fixed style and `refs/style_competitor.jpg`.
4. Show the candidates; the user picks; save as `refs/loc_<name>.png` / `refs/char_<name>.png`
   (they belong to one video and are git-ignored).
5. In `scenes.json` add them to `refs` with the role `location` or `character`, and attach
   them to every scene where that place or that creature is in the frame.
6. If the story changes a place later (a wall gets built, a fire goes out), describe the
   change in the scene prompt; do not make a new reference for it.

## 3. Scene table → `work/<slug>/scenes.json`

```json
{
  "title": "Topic Survival 1 Year",
  "voice": {"template_id": "chosen by the user"},
  "resolution": null,
  "setting": "rules for every frame only (no panels...); never a list of all places and seasons of the video",
  "refs": {"hero": "refs/hero_crop.png", "style": "refs/style_competitor.jpg",
           "<place>": "refs/loc_<place>.png", "<creature>": "refs/char_<creature>.png"},
  "ref_roles": {"hero": "hero", "style": "style", "<place>": "location", "<creature>": "character"},
  "ref_labels": {"hero": "CHARACTER 1", "<creature>": "T-REX", "<place>": "HILL"},
  "ref_notes": {"<creature>": "size only, e.g. Reference {<creature>} shows it next to CHARACTER 1: keep that size"},
  "scenes": [
    {"id": 1, "text": "narration", "type": "<shot type>",
     "prompt": "what is in the frame: action, emotion, framing, props",
     "in_frame": ["the hero, standing small at the left, frozen", "the T-rex on the hill, roaring"],
     "refs": ["hero", "<place>", "<creature>"], "text_in_image": "",
     "sfx": [{"file": "sfx/<pack>/<file>.mp3", "at": 0.0, "db": -8, "len": 4}]}
  ]
}
```

- One image per scene; words per scene = target seconds × narration words per second.

### Who is in the frame: continuity between scenes (most important rule for pictures)

The narration says what the scene is ABOUT; it does not say who is in the frame. Before
writing the prompts, go through the scenes in order and keep track of the moment: where
the hero is, what is around him, which creatures are present.
- While the moment continues in the same place, everyone who is there stays in the frame,
  even if the sentence talks only about one of them. Example: scene 10 — the hero walks up
  to a hill; scene 11 — a T-rex appears; scene 12 — the narration describes how terrifying
  the T-rex is. Scene 12 still shows the hero in that place (small in the foreground,
  frozen, looking at the T-rex) and the T-rex; the hero does not vanish just because the
  sentence is about the T-rex.
- Somebody leaves the frame only when the story moves them (he runs away, the time skips,
  the place changes) or when the scene is deliberately a close-up, an object or a diagram.
- Write every visible character into `in_frame` with where he is and what he does, and
  attach the matching refs (`hero`, `char_*`, `loc_*`). `images.py` adds the line "IN THE
  FRAME (every one of them must be clearly visible): …" to the prompt.

- `refs`: `hero` whenever the hero is visible; a location ref whenever the scene is in a
  recurring place; none for isolated objects/diagrams. Decide per scene.
- `text_in_image`: only where the reference uses on-screen text.
- Never write words that make a picture pale into a scene prompt: "pale", "muted", "misty",
  "hazy", "foggy", "dusty", "faded", "washed", "grey sky", "soft light". For night, dusk, rain
  or snow describe the scene itself (dark blue night sky, orange fire light, falling snow);
  the colours stay clear.
- `type`: one of the fixed shot types in `style/style.json` (`hero_location`, `object`,
  `big_text`, `closeup`).
- The `style` ref is attached to every scene automatically by `images.py`, together with
  the rule "use it only to understand the drawing style, transfer no objects from it".
  If an object from the style collage still shows up, regenerate that scene.
- Never use a competitor frame as a reference image: its objects leak into the frames.

## 4. Choices to ask the user (every new video)

- Voice: the channel's voice is **"James – Calm, Clear and Informative"** (ElevenLabs library
  voice, read by the Cartesia engine), used for Jurassic Survival Part 1 and Part 2. Put it in
  `scenes.json` as
  `"voice": {"voice_id": "uh5qBlKfjqFl7XXhFnJi", "voice_source": "elevenlabs", "model_id": "sonic-3.6", "speed": 100}`
  (volume 100, the script default). Use it unless the user asks for another voice; then run
  `python3 scripts/voicegen.py --list` and let the user pick.
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
REFERENCE IMAGES: N reference images are attached, in this order:
Reference 1 shows our character CHARACTER 1 and has absolute priority for his identity and appearance. ...
Reference 2 shows our T-REX. Draw T-REX exactly as in Reference 2. <ref_note, if any>
Reference 3 shows the place HILL. Take the layout, rocks, trees and objects of this place from Reference 3.
Reference 4 is the STYLE reference. It controls only the rendering technique ...
<style_block from style/style.json>
SETTING: <setting of this video>
SHOT TYPE: <shot_types[type] from style/style.json>
SCENE: <scene prompt>
IN THE FRAME (every one of them must be clearly visible): <in_frame>
<quality rule>
<exact text rule | "No text, letters or numbers anywhere in the image.">
16:9 frame, no watermark, no borders.
```

Rules (tested on Jurassic Part 2; each one fixed a real failure):
- References go hero, characters, places, style; the prompt introduces each by its number and
  `ref_labels` name. Scene text then uses only that name (CHARACTER 1, T-REX, NOTEBOOK...).
- Never describe how the hero, an animal or a recurring object looks, in the scene text, the
  setting or the style block: the look comes only from its reference. Size relations go in
  `ref_notes` (best shown in the reference picture itself, e.g. the T-rex drawn next to the hero).
- Do not call the hero "HERO" (the model draws a heroic realistic man) and do not set him against
  the other people ("all other people are stick figures", "he must not match the stick-figure
  style"): both made him a realistic man.
- One source of style: the STYLE reference controls only the rendering technique and never
  changes the characters, animals, objects or places of the other references.
- No name banners drawn on the reference images: the model then ignored the references.
- No contradictions between parts: no white background in the style block for full scenes,
  no fixed camera angle in a shot type, no list of all places and seasons in the setting
  (it leaks into every scene), no "hazy" in a scene when the quality rule says never hazy.

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
- a character who is still in the scene has vanished (see "Who is in the frame");
- a recurring creature looks different from its `char_*` reference;
- faded, washed-out, greyish or low-contrast picture;
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

## 8. Thumbnails (after the finished video is sent)

Offer the user 10 thumbnail options in the competitor's thumbnail style:
1. Look at `refs/thumbnail_style.jpg` (6 competitor thumbnails, sources and the channel page
   in `style/thumbnails/`). Their pattern: the hero big and close, one story element behind
   him, a simple background, 1–2 huge bold words in a free corner ("1 YEAR", "PART 2",
   "HOUR 1"), sometimes two coloured words for a contrast ("BAD" / "GOOD").
2. Write `work/<slug>/thumbnails.json`: 10 different ideas `{"text": "...", "idea": "..."}`
   built from the strongest moments and the title of this video.
3. `python3 scripts/thumbnails.py work/<slug>/thumbnails.json` → `thumbnails/thumb_01..10.png`
   (hero + thumbnail reference attached to every one), send all 10, the user picks or asks
   for changes (`--only 3,7 --force` after editing those ideas).

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

- Keys are read from the environment variables `VOICEGEN_API_KEY`, `ROYALTECHNO_API_KEY`
  (cloud environment settings) or from the git-ignored `work/.env`. Never put keys in other
  files, commits or chat.
- RoyalTechno rules: poll images every 5 s with `If-None-Match`, ≤ 20 jobs in flight,
  one `Idempotency-Key` per job, stop on 400/401/402/403, retry only 429/503.
- VoiceGen results expire after 3 days: download immediately.
