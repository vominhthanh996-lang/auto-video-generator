@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-06-part-05-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-06-storyboards\phan-05-dem-cuop-nuoc-dau-tien\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-06-storyboards\phan-05-dem-cuop-nuoc-dau-tien" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
