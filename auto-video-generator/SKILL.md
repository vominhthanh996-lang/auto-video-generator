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
   - Generate narration with Edge TTS by default using `scripts/generate_voice_edge.py`.
   - Generate scene images with the configured image provider.
   - Try image providers in this order unless the user asks otherwise: local SD 1.5 ComfyUI, OpenAI, Replicate, fal.ai, Stability AI, Pollinations AI, Runway, then manual/local assets.
   - Keep every generated file in the project's output folder.
4. Render the video:
   - Write a `storyboard.json` file using the schema in `references/brief_schema.md`.
   - Run `scripts/render_video.py` with the storyboard path and output path.
5. Verify the video:
   - Confirm the MP4 exists.
   - Check duration, resolution, audio presence, and file size.
   - If possible, inspect a frame or preview before delivery.

## Long-Form Story Workflow

For 30-60 minute story videos, do not create one huge storyboard. Split into chapters and render resumably.

Recommended structure:

- 30 minutes: 6 chapters x 5 minutes
- 60 minutes: 12 chapters x 5 minutes
- Scene duration: 8-15 seconds
- 30 minutes at 12 seconds per scene: about 150 scenes
- 60 minutes at 12 seconds per scene: about 300 scenes

Create a project scaffold:

```powershell
python scripts/create_longform_project.py --title "Story Title" --minutes 30 --chapter-minutes 5 --scene-duration 12
```

This creates:

- `manifest.json`
- `chapter-01/storyboard.json`
- `chapter-02/storyboard.json`
- `chapter-XX/assets/`
- `chapter-XX/output/`
- `final/final.mp4`

Then replace placeholder narration and image prompts in each chapter storyboard with the real story content.

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

1. `scripts/generate_images_comfy_local.py` if local ComfyUI is running.
2. `scripts/generate_assets_openai.py` if `OPENAI_API_KEY` is available and billing is healthy.
3. `scripts/generate_images_replicate.py` if `REPLICATE_API_TOKEN` is available.
4. `scripts/generate_images_fal.py` if `FAL_KEY` is available.
5. `scripts/generate_images_stability.py` if `STABILITY_API_KEY` is available.
6. `scripts/generate_images_pollinations.py` if `POLLINATIONS_API_KEY` is available.
7. `scripts/generate_runway.py --mode image` if `RUNWAYML_API_SECRET` is available.
8. Ask the user for another provider, uploaded images, or manual assets.

Local image defaults target low VRAM machines: SD 1.5 realistic/cinematic checkpoint, batch size 1, 512x768 generation, DPM++ 2M Karras, CFG around 6.5, tiled VAE, light hires pass, and final upscale to 1080x1920. Do not use FLUX as the default on 2GB VRAM.

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
