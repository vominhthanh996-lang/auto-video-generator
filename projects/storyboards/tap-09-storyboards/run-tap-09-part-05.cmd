@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-09-part-05-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\auto-video-generator\projects\storyboards\tap-09-storyboards\phan-05-toa-do-duoi-cau-gay\storyboard.json" -ProjectRoot "E:\ThanhMV\auto-video-generator\projects\storyboards\tap-09-storyboards\phan-05-toa-do-duoi-cau-gay" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
