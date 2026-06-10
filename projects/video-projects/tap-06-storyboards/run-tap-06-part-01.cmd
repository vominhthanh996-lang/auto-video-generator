@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-06-part-01-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-06-storyboards\phan-01-ba-ngay-dau-khong-duoc-chet\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-06-storyboards\phan-01-ba-ngay-dau-khong-duoc-chet" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
