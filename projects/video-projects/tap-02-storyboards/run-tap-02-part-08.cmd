@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-02-part-08-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-02-storyboards\phan-08-thu-duoi-duong-ham\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-02-storyboards\phan-08-thu-duoi-duong-ham" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
