@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-04-part-02-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-04-storyboards\phan-02-ba-ngay-chuoc-mot-cai-ten-cu\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-04-storyboards\phan-02-ba-ngay-chuoc-mot-cai-ten-cu" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
