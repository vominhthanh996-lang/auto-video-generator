@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-04-part-08-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-04-storyboards\phan-08-hac-nha-chua-chet-het\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-04-storyboards\phan-08-hac-nha-chua-chet-het" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
