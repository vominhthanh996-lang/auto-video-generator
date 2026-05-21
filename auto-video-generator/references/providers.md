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

1. Local SD 1.5 through ComfyUI via `scripts/generate_images_comfy_local.py`.
2. OpenAI image generation via `scripts/generate_assets_openai.py`.
3. Replicate image generation via `scripts/generate_images_replicate.py`.
4. fal.ai image generation via `scripts/generate_images_fal.py`.
5. Stability AI image generation via `scripts/generate_images_stability.py`.
6. Pollinations AI image generation via `scripts/generate_images_pollinations.py`.
7. Runway image generation via `scripts/generate_runway.py --mode image`.
8. Manual/local image assets.

Use `scripts/generate_with_fallback.py --kind image` to automatically try this chain and stop at the first successful provider.

### Local SD 1.5 Low-VRAM

The local provider is tuned for the user's 2GB VRAM GPU. It uses SD 1.5 realistic/cinematic checkpoints by default, keeps batch size at 1, generates small, then upscales.

```powershell
python scripts/generate_images_comfy_local.py --inspect-only
python scripts/generate_images_comfy_local.py --storyboard path\to\storyboard.json --preset balanced --overwrite
```

Requirements:

- ComfyUI running at `http://127.0.0.1:8188` or `COMFYUI_URL`.
- SD 1.5 realistic/cinematic checkpoint in ComfyUI `models/checkpoints`.
- SD 1.5 VAE in ComfyUI `models/vae`, recommended `vae-ft-mse-840000-ema-pruned.safetensors`.
- Optional LoRAs in ComfyUI `models/loras`.
- Optional upscale model in ComfyUI `models/upscale_models`.

Useful environment variables:

- `COMFYUI_URL`
- `SD15_CHECKPOINT`
- `SD15_VAE`
- `SD_UPSCALE_MODEL`

Model selection:

- `--checkpoint auto` scans ComfyUI and prefers SD 1.5 realistic/cinematic checkpoints.
- `--vae auto` prefers `vae-ft-mse-840000-ema-pruned` if available, otherwise uses the checkpoint VAE.
- `--upscale-model auto` prefers 4x-UltraSharp, Remacri, then RealESRGAN if available.
- `--lora name.safetensors:0.45` is optional. Missing LoRAs are skipped instead of crashing the whole batch.

Presets:

- `--preset safe`: 512x704, fewer steps, lighter hires pass.
- `--preset balanced`: 512x768, stable default for 2GB VRAM.
- `--preset quality`: 576x832, better detail if the current ComfyUI setup can hold it.

Default 2GB VRAM settings:

- Resolution: `512x768`
- Batch size: `1`
- Steps: `24`
- CFG: `6.5`
- Sampler: `dpmpp_2m`
- Scheduler: `karras`
- Hires scale: `1.5`
- Hires denoise: `0.34`
- Tiled VAE: enabled
- VAE tile size: `384`
- Final scale: `1080x1920`

Recommended checkpoints to test first:

- Realistic Vision v6 / v5.1
- CyberRealistic v4.x
- epiCRealism
- Photon
- DreamShaper 8 for more stylized cinematic scenes

Recommended upscalers:

- 4x-UltraSharp
- 4x_foolhardy_Remacri
- RealESRGAN_x2plus

Optional experimental mode: SDXL Turbo or FLUX can be tested only if a quantized/low-VRAM ComfyUI setup is already stable. They are not the default for 2GB VRAM.

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
