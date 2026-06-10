@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-08-part-04-YouTube-WorkLocal" -StoryboardPath "E:\ThanhMV\video-projects\tap-08-storyboards\phan-04-mot-chu-ky-co-mui-thuoc-sat-trung\storyboard.json" -ProjectRoot "E:\ThanhMV\video-projects\tap-08-storyboards\phan-04-mot-chu-ky-co-mui-thuoc-sat-trung" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
