@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-08-part-05-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-08-storyboards\phan-05-tram-ghi-so-12\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-08-storyboards\phan-05-tram-ghi-so-12" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
