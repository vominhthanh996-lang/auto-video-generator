# Create Video QA 2026-05-25

Repo-local video project for asking, drafting, storyboarding, and rendering with this repository's scripts.

## Default

- Format: 9:16 / tiktok
- Voice: vi-female
- Status: waiting for brief

## Run From Repo Root

``powershell
python scripts\validate_storyboard.py --storyboard projects\create-video-qa-2026-05-25\storyboard.json --stage text
python scripts\generate_voice_edge.py --storyboard projects\create-video-qa-2026-05-25\storyboard.json --voice vi-female --voice-style wasteland-dark --overwrite
python scripts\generate_with_fallback.py --storyboard projects\create-video-qa-2026-05-25\storyboard.json --kind image --overwrite
python scripts\render_video.py --storyboard projects\create-video-qa-2026-05-25\storyboard.json --output projects\create-video-qa-2026-05-25\output\create-video-qa-2026-05-25.mp4 --format tiktok
``

Generated assets, logs, and output stay local and are ignored by Git.
