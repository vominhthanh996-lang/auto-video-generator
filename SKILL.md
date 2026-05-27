---
name: auto-video-generator
description: Generate videos automatically from a user script or brief with AI-generated images, AI text-to-speech narration, on-screen text, subtitles, music, and final MP4 rendering, including long-form 30-60 minute story videos split into chapters. Use when the user asks to create, assemble, or automate social videos, explainer clips, reels, shorts, narrated slideshows, long story videos, or prompt-to-video workflows.
metadata:
  short-description: Generate narrated videos from text
---

# Auto Video Generator

Use this skill to turn a user-provided idea, script, or text into a finished narrated video.

## Default Output

- Format: MP4
- Default aspect ratio: 9:16 vertical unless the user asks otherwise
- Default duration: 30-60 seconds for short videos; 30-60 minutes for story videos when requested
- Default language: match the user's input language
- Required elements: AI-generated images, AI-generated narration, on-screen text, and subtitles


## Output Presets

Use these names whenever the user asks for a target platform:

- `tiktok`: vertical `1080x1920`, aspect `9:16`, `30 FPS`, MP4. Also use for YouTube Shorts/Reels.
- `youtube`: landscape `1920x1080`, aspect `16:9`, `30 FPS`, MP4. Use for normal long-form YouTube videos.

Supported CLI usage:

```powershell
python scripts/create_longform_project.py --title "Story" --format tiktok
python scripts/create_longform_project.py --title "Story" --format youtube
python scripts/render_video.py --storyboard path\to\storyboard.json --output output.mp4 --format youtube
```

## One-Command Local Pipeline

For routine story videos, use the pipeline runner instead of manually calling each stage:

```powershell
python scripts/run_story_pipeline.py --source D:\ThanhMV\stories\chapter-01.txt --title "Chapter 01" --format youtube --batch-size 5 --start-comfy
python scripts/run_story_pipeline.py --source D:\ThanhMV\stories\chapter-01.txt --title "Chapter 01" --format tiktok --batch-size 5 --start-comfy
```

The runner:

- writes all project files under the detected work root, typically `D:\ThanhMV\video-projects` or `E:\ThanhMV\video-projects`
- builds a UTF-8 storyboard from the source text
- validates Vietnamese text before TTS
- runs local ComfyUI image batches and Edge TTS voice in parallel
- syncs scene duration to real audio duration
- validates text, images, and audio before rendering
- creates `contact-sheet.html`, `pipeline-summary.json`, and the final MP4

## Manual ChatGPT Hybrid Image Mode

Use this only when the user explicitly asks for `hybrid` or manual ChatGPT help. This mode does not automate ChatGPT app/browser usage and does not use the OpenAI API.

The pipeline splits scenes into:

- ComfyUI local scenes: generated automatically.
- Manual ChatGPT scenes: prompts are written for the user to paste into ChatGPT app.

Recommended command:

```powershell
python scripts/run_story_pipeline.py --source D:\ThanhMV\stories\chapter-01.txt --title "Chapter 01" --format youtube --image-mode hybrid-manual --manual-image-ratio 0.5 --wait-for-manual-images --start-comfy
```

Outputs for manual ChatGPT images:

- `chatgpt_image_prompts.md`: copy/paste prompts for ChatGPT app.
- `assets/manual-chatgpt/`: save ChatGPT images here.
- Expected filename pattern: `manual-scene-001.png`, `manual-scene-024.png`, etc.
- `manual-chatgpt-manifest.json`: machine-readable prompt/scene map.
- `manual-chatgpt-missing.json`: missing image list if render is waiting.

After the user saves the images, rerun:

```powershell
python scripts/run_story_pipeline.py --source D:\ThanhMV\stories\chapter-01.txt --title "Chapter 01" --format youtube --image-mode hybrid-manual --manual-image-ratio 0.5 --import-manual-images --skip-voice --skip-images
```

Use `--skip-images` only when the ComfyUI half is already generated. Otherwise omit it so ComfyUI fills its assigned scenes.

## Workflow

1. Capture the brief:
   - Topic or raw script
   - Target duration
   - Aspect ratio: 9:16, 1:1, or 16:9
   - Visual style
   - Voice style
   - Subtitle preference
   - Output folder
2. Create a storyboard with scenes. Each scene needs:
   - Narration text
   - Image prompt
   - On-screen text
   - Duration in seconds
3. Generate assets:
   - Save user script/source text as a UTF-8 file before building the storyboard. Do not pipe Vietnamese text through inline PowerShell/Python because it can turn accents into `?`.
   - Validate storyboard text before generating voice:
     `python scripts/validate_storyboard.py --storyboard path\to\storyboard.json --stage text`
   - Generate narration with Edge TTS by default using `scripts/generate_voice_edge.py`.
   - Validate generated audio before rendering:
     `python scripts/validate_storyboard.py --storyboard path\to\storyboard.json --stage assets`
   - Generate scene images with the configured online image provider.
   - Try image providers in this order unless the user asks otherwise: OpenAI, Replicate, fal.ai, Stability AI, Pollinations AI, Runway, then manual/local assets.
   - Keep every generated file in the project's output folder.
4. Render the video:
   - Write a `storyboard.json` file using the schema in `references/brief_schema.md`.
   - Run `scripts/render_video.py` with the storyboard path and output path.
   - `render_video.py` validates text, images, and audio before it writes the MP4.
5. Verify the video:
   - Confirm the MP4 exists.
   - Check duration, resolution, audio presence, and file size.
   - If possible, inspect a frame or preview before delivery.

## Long-Form Story Workflow

For 30-60 minute story videos, do not create one huge storyboard. Split into chapters and render resumably.

Recommended structure:

- 30 minutes: 6 chapters x 5 minutes
- 60 minutes: 12 chapters x 5 minutes
- Scene/image density for story videos: about 1 image per 30 narration words
- Example: 1800 words should become about 60 scenes/images
- Scene duration: 8-15 seconds, but do not let scenes get too sparse for the narration
- 30 minutes at 12 seconds per scene: about 150 scenes minimum
- 60 minutes at 12 seconds per scene: about 300 scenes minimum

Create a project scaffold:

```powershell
python scripts/create_longform_project.py --title "Story Title" --minutes 30 --chapter-minutes 5 --scene-duration 12 --format tiktok
python scripts/create_longform_project.py --title "Story Title" --minutes 30 --chapter-minutes 5 --scene-duration 12 --format youtube
python scripts/create_longform_project.py --title "Chapter 12" --minutes 12 --words 1800 --words-per-image 30 --format tiktok
```

This creates:

- `manifest.json`
- `chapter-01/storyboard.json`
- `chapter-02/storyboard.json`
- `chapter-XX/assets/`
- `chapter-XX/output/`
- `final/final.mp4`

Then replace placeholder narration and image prompts in each chapter storyboard with the real story content.

For local ComfyUI image generation on 2GB VRAM, generate small batches:

```powershell
python scripts/generate_images_comfy_batches.py --storyboard path\to\storyboard.json --batch-size 5 --aspect-ratio 16:9 --final-width 1920 --final-height 1080
```

While images are generating, generate/validate voice in a separate run when possible:

```powershell
python scripts/generate_voice_edge.py --storyboard path\to\storyboard.json --voice vi-female
python scripts/validate_storyboard.py --storyboard path\to\storyboard.json --stage assets
```

Render one chapter first:

```powershell
python scripts/render_longform.py --manifest path\to\manifest.json --chapter 1 --voice vi-female
```

Render all chapters and concat final:

```powershell
python scripts/render_longform.py --manifest path\to\manifest.json --voice vi-female
```

Resume behavior:

- Existing chapter MP4 files are skipped unless `--overwrite` is passed.
- Existing images are reused unless `--overwrite-images` is passed.
- Use `--skip-images` when images are already generated.
- Use `--skip-voice` when audio is already generated.

## Provider Selection

Read `references/providers.md` only when choosing or configuring image providers. Voice defaults to Edge TTS, which does not use OpenAI tokens but requires internet access.

## Voice

Use Edge TTS by default:

```powershell
python scripts/generate_voice_edge.py --storyboard path\to\storyboard.json --voice vi-female --overwrite
```

Voice presets:

- `vi-female`: Vietnamese female, `vi-VN-HoaiMyNeural`
- `vi-male`: Vietnamese male, `vi-VN-NamMinhNeural`
- `en-female`: English female, `en-US-JennyNeural`
- `en-male`: English male, `en-US-GuyNeural`

Use a matching voice for the narration language. For mixed-language videos, split scenes by language or run the voice generator separately per storyboard.

## Image Fallback

Prefer the fallback router:

```powershell
python scripts/generate_with_fallback.py --storyboard path\to\storyboard.json --kind image
```

It tries provider scripts in order and stops at the first success:

1. `scripts/generate_assets_openai.py` if `OPENAI_API_KEY` is available and billing is healthy.
2. `scripts/generate_images_replicate.py` if `REPLICATE_API_TOKEN` is available.
3. `scripts/generate_images_fal.py` if `FAL_KEY` is available.
4. `scripts/generate_images_stability.py` if `STABILITY_API_KEY` is available.
5. `scripts/generate_images_pollinations.py` if `POLLINATIONS_API_KEY` is available.
6. `scripts/generate_runway.py --mode image` if `RUNWAYML_API_SECRET` is available.
7. Ask the user for another provider, uploaded images, or manual assets.

## Video Generation

Use Runway or Luma for AI-generated video clips, with local cinematic keyframe animation as the final fallback:

```powershell
python scripts/generate_with_fallback.py --storyboard path\to\storyboard.json --kind video
python scripts/generate_runway.py --storyboard path\to\storyboard.json --mode video --duration 5
python scripts/generate_luma.py --storyboard path\to\storyboard.json --duration 5s
python scripts/generate_video_local.py --storyboard path\to\storyboard.json
```

Use the fallback router first unless the user explicitly picks a provider.

Multiple API keys per provider are supported by naming environment variables with suffixes:

- `RUNWAYML_API_SECRET`, `RUNWAYML_API_SECRET_1`, `RUNWAYML_API_SECRET_2`
- `STABILITY_API_KEY`, `STABILITY_API_KEY_1`, `STABILITY_API_KEY_2`
- `FAL_KEY`, `FAL_KEY_1`, `FAL_KEY_2`
- `POLLINATIONS_API_KEY`, `POLLINATIONS_API_KEY_1`, `POLLINATIONS_API_KEY_2`

The router tries all keys for a provider before moving to the next provider. You can also set comma-separated lists such as `RUNWAYML_API_SECRET_LIST`.

Runway defaults:

- Image generation model: `gen4_image_turbo`
- Video generation model: `gen4.5`
- Portrait output ratio: `720:1280`
- Key env var: `RUNWAYML_API_SECRET`

Runway charges credits per generation and per video second. Do a one-scene test before running a batch.

Luma defaults:

- Video generation model: `ray-flash-2`
- Resolution: `720p`
- Duration: `5s`
- Key env var: `LUMAAI_API_KEY`

Luma image-to-video requires an externally reachable image URL, so this skill defaults to text-to-video for Luma unless a scene provides hosted keyframe URLs.

## Rendering

Use the bundled renderer when image and audio assets already exist:

```powershell
python scripts/render_video.py --storyboard path\to\storyboard.json --output path\to\video.mp4
```

The renderer expects local image and audio paths in the storyboard. It creates subtitles and burns simple on-screen text into the video.

## Quality Rules

- Keep scene text short enough to read on mobile.
- Avoid putting important text near the frame edges.
- Use one coherent visual style across all scene image prompts.
- Match narration pacing to scene duration.
- Verify generated assets exist before rendering.
- Never overwrite a user's source assets unless explicitly requested.
