# Auto Video Generator

Codex skill and scripts for generating short and long-form narrated videos.

## Features

- Storyboard-driven video generation
- Edge TTS voice generation for Vietnamese and English
- Image provider fallback:
  - OpenAI
  - Replicate
  - fal.ai
  - Stability AI
  - Pollinations AI
  - Runway
- Video provider fallback:
  - Runway
  - Luma
  - Local cinematic keyframe animation
- Long-form 30-60 minute project scaffolding with chapter-based rendering
- Local MP4 rendering with FFmpeg

## Required Tools

- Python 3.12+
- FFmpeg and FFprobe on PATH

## Environment Variables

Set only the providers you want to use:

```powershell
setx OPENAI_API_KEY "..."
setx REPLICATE_API_TOKEN "..."
setx FAL_KEY "..."
setx STABILITY_API_KEY "..."
setx POLLINATIONS_API_KEY "..."
setx RUNWAYML_API_SECRET "..."
setx LUMAAI_API_KEY "..."
```

Multiple keys per provider are supported:

```powershell
setx RUNWAYML_API_SECRET_1 "..."
setx RUNWAYML_API_SECRET_2 "..."
```

## Short Video Flow

```powershell
python auto-video-generator\scripts\generate_with_fallback.py --storyboard path\to\storyboard.json --kind image
python auto-video-generator\scripts\generate_voice_edge.py --storyboard path\to\storyboard.json --voice vi-female
python auto-video-generator\scripts\render_video.py --storyboard path\to\storyboard.json --output output.mp4
```

## Long-Form Flow

```powershell
python auto-video-generator\scripts\create_longform_project.py --title "Story Title" --minutes 30 --chapter-minutes 5 --scene-duration 12
python auto-video-generator\scripts\render_longform.py --manifest E:\ThanhMV\video-projects\story-title\manifest.json --chapter 1 --voice vi-female
python auto-video-generator\scripts\render_longform.py --manifest E:\ThanhMV\video-projects\story-title\manifest.json --voice vi-female
```

## Notes

- Do not commit API keys.
- Generated video projects can become large; keep outputs outside the repository.
- Provider availability, credit limits, and pricing can change.
