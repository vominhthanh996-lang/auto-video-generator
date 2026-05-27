@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-07-part-06-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-07-storyboards\phan-06-thue-nuoc-dau-tien\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-07-storyboards\phan-06-thue-nuoc-dau-tien" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
