@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-01-part-08-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-01-storyboards\phan-08-lon-giap-bun-va-muong-dau-dau-tien\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-01-storyboards\phan-08-lon-giap-bun-va-muong-dau-dau-tien" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
