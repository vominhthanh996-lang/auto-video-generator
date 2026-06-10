@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-03-part-06-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-03-storyboards\phan-06-dau-hac-nha\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-03-storyboards\phan-06-dau-hac-nha" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
