@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-02-part-04-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-02-storyboards\phan-04-duong-ham-so-4\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-02-storyboards\phan-04-duong-ham-so-4" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
