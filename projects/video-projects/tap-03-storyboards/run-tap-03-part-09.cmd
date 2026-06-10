@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-03-part-09-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-03-storyboards\phan-09-bao-bui-do\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-03-storyboards\phan-09-bao-bui-do" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
