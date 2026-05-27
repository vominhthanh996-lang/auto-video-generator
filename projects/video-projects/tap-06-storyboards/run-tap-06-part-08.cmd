@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-06-part-08-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-06-storyboards\phan-08-mot-bat-nuoc-bi-danh-cap\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-06-storyboards\phan-08-mot-bat-nuoc-bi-danh-cap" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
