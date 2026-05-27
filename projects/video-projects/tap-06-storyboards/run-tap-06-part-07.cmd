@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-06-part-07-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-06-storyboards\phan-07-ai-duoc-goi-la-nguoi-tram\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-06-storyboards\phan-07-ai-duoc-goi-la-nguoi-tram" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
