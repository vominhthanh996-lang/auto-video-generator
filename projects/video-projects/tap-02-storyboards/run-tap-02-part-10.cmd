@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-02-part-10-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-02-storyboards\phan-10-roi-ga-xam\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-02-storyboards\phan-10-roi-ga-xam" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
