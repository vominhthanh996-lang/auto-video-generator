# Providers

This skill separates creative generation from rendering.

## Images

Use whichever image generation tool is available in the current Codex session. When using an API, keep provider-specific details out of `SKILL.md` and document them here.

Expected output:

- One image per scene
- PNG or JPG
- Same aspect ratio as the final video
- File paths written into `storyboard.json`

## Text-to-Speech

Use Edge TTS by default to turn each scene's narration into audio. This does not use OpenAI tokens and does not require an API key, but it does require internet access.

Expected output:

- One audio file per scene
- WAV, MP3, M4A, or AAC
- File paths written into `storyboard.json`

Use `scripts/generate_voice_edge.py` for normal work. Use `scripts/generate_voice_windows.ps1` only for offline fallback testing, because Windows' built-in voices are usually lower quality and may not include Vietnamese.

## Image Provider Fallback

Provider order:

1. OpenAI image generation via `scripts/generate_assets_openai.py`.
2. Replicate image generation via `scripts/generate_images_replicate.py`.
3. fal.ai image generation via `scripts/generate_images_fal.py`.
4. Stability AI image generation via `scripts/generate_images_stability.py`.
5. Pollinations AI image generation via `scripts/generate_images_pollinations.py`.
6. Runway image generation via `scripts/generate_runway.py --mode image`.
7. Manual/local image assets.

Use `scripts/generate_with_fallback.py --kind image` to automatically try this chain and stop at the first successful provider.

## Video Providers

Runway and Luma are the default online video providers:

Use `scripts/generate_with_fallback.py --kind video` to automatically try Runway first, then Luma, then local cinematic keyframe animation.

- Text-to-video and image-to-video: `scripts/generate_runway.py --mode video`
- Default model: `gen4.5`
- API version header: `2024-11-06`
- Env var: `RUNWAYML_API_SECRET`

Luma:

- Text-to-video: `scripts/generate_luma.py`
- Default model: `ray-flash-2`
- Env var: `LUMAAI_API_KEY`
- Image-to-video requires hosted image URLs, not local file paths.

Recommended environment variables for provider adapters:

- `VIDEO_IMAGE_PROVIDER`
- `VIDEO_TTS_PROVIDER`
- `OPENAI_API_KEY`
- `REPLICATE_API_TOKEN`
- `FAL_KEY`
- `STABILITY_API_KEY`
- `POLLINATIONS_API_KEY`
- `RUNWAYML_API_SECRET`
- `LUMAAI_API_KEY`
- `ELEVENLABS_API_KEY`

Do not print API keys. If no provider is configured, ask the user which provider to use.

## Rendering Requirements

The renderer requires `ffmpeg` and `ffprobe` on PATH. If they are missing, install or configure them before rendering.
