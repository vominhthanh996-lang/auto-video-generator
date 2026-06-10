# Auto Video Repo Link

Project này được thiết lập để chạy bằng repo:

$repo

Project files vẫn nằm ngoài Git repo để tránh commit nhầm assets/output nặng.

## Files

- Storyboard: $project\storyboard.json
- Assets: $project\assets
- Output: $project\output
- Logs: $project\logs
- Config: $project\auto-video.config.json

## Commands

Validate text:

``powershell
python "E:\ThanhMV\auto-video-generator\scripts\validate_storyboard.py" --storyboard "E:\ThanhMV\video-projects\create-video-qa-2026-05-25\storyboard.json" --stage text
``

Generate voice:

``powershell
python "E:\ThanhMV\auto-video-generator\scripts\generate_voice_edge.py" --storyboard "E:\ThanhMV\video-projects\create-video-qa-2026-05-25\storyboard.json" --voice vi-female --overwrite
``

Generate images:

``powershell
python "E:\ThanhMV\auto-video-generator\scripts\generate_with_fallback.py" --storyboard "E:\ThanhMV\video-projects\create-video-qa-2026-05-25\storyboard.json" --kind image --overwrite
``

Render:

``powershell
python "E:\ThanhMV\auto-video-generator\scripts\render_video.py" --storyboard "E:\ThanhMV\video-projects\create-video-qa-2026-05-25\storyboard.json" --output "E:\ThanhMV\video-projects\create-video-qa-2026-05-25\output\create-video-qa-2026-05-25.mp4" --format tiktok
``
