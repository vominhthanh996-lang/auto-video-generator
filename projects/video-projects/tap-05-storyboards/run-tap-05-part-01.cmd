@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-05-part-01-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-05-storyboards\phan-01-khi-thanh-bat-dau-khoa-cua\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-05-storyboards\phan-01-khi-thanh-bat-dau-khoa-cua" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
