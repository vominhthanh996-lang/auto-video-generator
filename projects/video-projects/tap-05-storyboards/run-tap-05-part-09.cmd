@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-05-part-09-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-05-storyboards\phan-09-tham-bach-dem-toi-mot-thanh-pho\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-05-storyboards\phan-09-tham-bach-dem-toi-mot-thanh-pho" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
