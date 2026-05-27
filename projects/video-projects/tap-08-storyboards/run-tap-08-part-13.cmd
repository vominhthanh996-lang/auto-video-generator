@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-08-part-13-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-08-storyboards\phan-13-nguoi-da-ky-quay-lai\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-08-storyboards\phan-13-nguoi-da-ky-quay-lai" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
