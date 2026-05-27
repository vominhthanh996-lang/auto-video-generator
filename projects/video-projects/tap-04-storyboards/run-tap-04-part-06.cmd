@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-04-part-06-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-04-storyboards\phan-06-tham-bach-dua-ra-gia\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-04-storyboards\phan-06-tham-bach-dua-ra-gia" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
