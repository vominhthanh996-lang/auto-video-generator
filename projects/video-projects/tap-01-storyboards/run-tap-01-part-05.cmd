@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-01-part-05-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-01-storyboards\phan-05-vien-tinh-thach-trong-bun-den\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-01-storyboards\phan-05-vien-tinh-thach-trong-bun-den" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
