@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-08-part-08-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-08-storyboards\phan-08-ban-ghi-trong-may-chet\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-08-storyboards\phan-08-ban-ghi-trong-may-chet" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
