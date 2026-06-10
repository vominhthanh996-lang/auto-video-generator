# Machine Handoff

This file records the important working agreements, quality targets, and technical decisions for the project so another machine can pull the repo and continue without relying on chat history.

## Working location

- Main repo: `E:\ThanhMV\auto-video-generator`
- Project outputs and temporary work should stay under `E:\ThanhMV`
- Avoid using `C:` for story inputs, outputs, generated assets, or temp files unless a third-party app forces it

## Current branch

- Active branch used for these changes: `codex-auto-video-generator`

## Main workflow goals

- Generate Vietnamese story videos with:
  - local or hybrid image generation
  - Edge TTS based narration
  - consistent characters across scenes
  - image prompts that match the story beat, not generic wallpaper
- Support both:
  - `youtube` -> `16:9`
  - `tiktok` -> `9:16`

## Image direction

- Preferred visual target is based on Thanh's approved reference image:
  - dirty but beautiful young female scavenger on the left
  - injured righteous male survivor on the right
  - warm lantern between them
  - torn tarp shelter
  - ruined wasteland depth behind
  - cinematic warm/cool contrast
- LÃ¢m Tá»‹ch should look like a beautiful youthful maiden, but still weak, dirty, hungry, and believable in the wasteland
- Táº§n DÃ£ should look principled and protective, not villainous, not faceless
- Images should stay story-accurate and maintain scene-to-scene continuity

## Important local image-generation reality

- Current weaker machine only has one local checkpoint in ComfyUI:
  - `dreamshaper_8.safetensors`
- There is no stronger realistic checkpoint yet on this machine
- There is no dedicated local upscaler model in ComfyUI yet
- Because of that, pure text-to-image local output is limited
- The best current local path is:
  - ComfyUI local generation
  - strong face/composition prompt control
  - optional `--reference-image` img2img mode
  - low `--reference-denoise` to preserve composition

## Current local image improvements already implemented

- stronger face-control prompt at the front of local prompts
- stronger negative prompt for:
  - melted face
  - warped face
  - bad eyes
  - cropped face
  - solo portrait drift
  - missing second character
- reference-image local mode added to ComfyUI generator
- batch runner and story pipeline can now pass:
  - `--reference-image`
  - `--reference-denoise`

## Recommended local command pattern

```powershell
python E:\ThanhMV\auto-video-generator\scripts\run_story_pipeline.py `
  --source "E:\ThanhMV\Content truyen\...\story.md" `
  --format youtube `
  --image-mode comfy `
  --image-reference "C:\Users\thanh\Downloads\fb8d05e9-8752-4bc9-912c-85580d64d714.png" `
  --image-reference-denoise 0.28 `
  --run-mode work
```

## Voice direction

- narration should not be too slow
- pauses at `,` and `.` should be short and natural
- character voices should differ from narration voice
- character delivery should adapt to emotion and scene tone
- part 1 assets should not be overwritten unless explicitly requested

## Auto learning

- GitHub Actions based learning runner exists and should keep running independently
- It is for learning/research only, not for rendering videos

## Important user preferences

- Do not overwrite approved or existing deliverables unless explicitly requested
- Keep image style grounded, cinematic, and close to viral wasteland story videos
- Avoid generic AI beauty, oversaturation, or random wallpaper shots
- Prefer resumable workflows
- Keep everything portable so another machine can continue after a normal git pull

## Limitation of git vs chat history

- Git can store code, config, logs, notes, prompts, and workflow decisions
- Git does not automatically store the full Codex/ChatGPT conversation thread
- This file exists to preserve the useful technical context from the collaboration
