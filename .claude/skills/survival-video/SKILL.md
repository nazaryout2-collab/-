---
name: survival-video
description: Produce an animated "X Survival N Days/1 Year" YouTube video (prehistoric / dinosaur settings) in the style of the reference competitor — script, scene table, voiceover (VoiceGen), images (RoyalTechno, multi-reference), and FFmpeg assembly. Use whenever the user gives a video topic for the survival channel or asks to make, test or fix any step of this pipeline.
---

# Survival video pipeline

The user supplies the topic. Nothing about ideas is stored here: every decision about
style, narration and pacing comes from analysing the reference material at the start
of each session.

## 0. Session start: analyse the references (always, before writing anything)

1. `python3 scripts/analyze_reference.py` — extracts frames from `style/reference.mp4`
   into `work/ref_frames/`, builds contact sheets and prints pacing stats
   (average seconds per image, cut count). Look at every contact sheet.
2. Read both transcripts in `style/transcripts/`.
3. Write `work/style_notes.md` for this session:
   - visual: line weight, palette, character proportions, backgrounds, shot types,
     on-screen text, what changes between consecutive frames;
   - narration: person/tense, hook in the first 30 s, how numbers and supplies are
     used, escalation rhythm (day markers), cliffhanger ending, words per minute;
   - pacing: seconds per image, words per scene.
   Derive the style block for image prompts from this analysis (template below).

## 1. Script

Write the script for the user's topic following `work/style_notes.md`.
Target length and structure come from the transcripts (≈1 900–2 100 words for ~11–12 min).
Show the script to the user and wait for approval before spending credits.

## 2. Scene table → `work/<slug>/scenes.json`

Split the approved script into scenes, one image per scene, sized to the measured
pacing (words per scene). Schema:

```json
{
  "title": "Ice Age Survival 1 Year",
  "voice": {"voice_id": "...", "model_id": "sonic-3.6", "speed": 100},
  "style_block": "…derived in step 0…",
  "refs": {"hero": "refs/hero.png", "cave_inside": "refs/cave_inside.png"},
  "scenes": [
    {"id": 1, "text": "narration for this scene",
     "prompt": "what is in the frame: action, emotion, shot, props",
     "refs": ["hero", "cave_inside"]}
  ]
}
```

`refs` per scene: include `hero` whenever the hero is visible, plus the location
reference whenever the scene is in a recurring place. Decide this yourself per scene.

## 3. References (once per new hero / location)

Generate candidates with `scripts/images.py --refs-only`, show them, let the user pick,
save the chosen ones under `refs/`. Reuse them for every later video.

## 4. Generate

- Voice: `python3 scripts/voicegen.py work/<slug>/scenes.json` → `audio/scene_###.mp3`
  (one task per scene, so every scene has its own exact duration).
- Images: `python3 scripts/images.py work/<slug>/scenes.json` → `images/scene_###.png`.
  Always test on 3–5 scenes first and show the user before the full batch.
- Review every image (contact sheets: `scripts/contact_sheet.py`). Regenerate the ones
  that break the style, the hero design or the location; note why in `review.md`.

## 5. Assemble

`python3 scripts/assemble.py work/<slug>/scenes.json` — each image stays on screen exactly
as long as its scene audio, with a slow zoom/pan, short crossfades and optional music
(`--music file.mp3`, ducked under the voice). Output: `work/<slug>/final.mp4` (1080p30).

## Prompt template for images

```
<style_block from step 0>
SCENE: <scene.prompt>
Keep the hero identical to the hero reference image. Keep the location identical to
the location reference image. 16:9, no text, no watermark, no captions.
```

## Keys and costs

- Keys come only from environment variables `VOICEGEN_API_KEY` and `ROYALTECHNO_API_KEY`.
  Never write a key to a file, a commit or the chat.
- Images: `nano-banana-pro` (≈$0.02/image, up to 10 reference images). Voice: billed per
  character by VoiceGen. Ask before any batch larger than the 3–5 scene test.
- RoyalTechno client rules are enforced: poll images every 5 s with `If-None-Match`,
  ≤ 20 jobs in flight, one `Idempotency-Key` per job, stop on 400/401/402/403,
  retry only 429 (after `Retry-After`) and 503.
- VoiceGen results expire after 3 days: download immediately.
