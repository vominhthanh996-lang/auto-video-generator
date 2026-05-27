@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-09-part-02-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\auto-video-generator\projects\storyboards\tap-09-storyboards\phan-02-duong-khong-co-co\storyboard.json" -ProjectRoot "E:\ThanhMV\auto-video-generator\projects\storyboards\tap-09-storyboards\phan-02-duong-khong-co-co" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
