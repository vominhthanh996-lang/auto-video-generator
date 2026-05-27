@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-01-part-04-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-01-storyboards\phan-04-cho-hai-ham-tro-lai\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-01-storyboards\phan-04-cho-hai-ham-tro-lai" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
