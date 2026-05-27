@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-05-part-04-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-05-storyboards\phan-04-roi-thanh-khong-phai-tron-chay\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-05-storyboards\phan-04-roi-thanh-khong-phai-tron-chay" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
