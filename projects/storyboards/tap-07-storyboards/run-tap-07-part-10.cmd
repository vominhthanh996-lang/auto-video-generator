@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-07-part-10-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-07-storyboards\phan-10-mot-la-co-khong-sach\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-07-storyboards\phan-10-mot-la-co-khong-sach" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
