@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..\..\..") do set "REPO_ROOT=%%~fI"
set "PROJECT_ROOT=%SCRIPT_DIR%phan-10-mot-la-co-khong-sach"
set "STORYBOARD=%PROJECT_ROOT%\storyboard.json"
powershell -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\start_story_task.ps1" -TaskName "AutoVideo-tap-07-part-10-YouTube-WorkLocal" -RepoRoot "%REPO_ROOT%" -StoryboardPath "%STORYBOARD%" -ProjectRoot "%PROJECT_ROOT%" -Format youtube -RunMode work -ImageMode comfy -UseExistingStoryboard
endlocal
