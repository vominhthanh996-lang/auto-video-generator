@echo off
setlocal

if "%~1"=="" (
  echo Usage: start_story_task.cmd "TaskName" "StorySource"
  exit /b 1
)

if "%~2"=="" (
  echo Usage: start_story_task.cmd "TaskName" "StorySource"
  exit /b 1
)

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "REPO_ROOT=%%~fI"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%REPO_ROOT%\scripts\start_story_task.ps1" -RepoRoot "%REPO_ROOT%" -TaskName "%~1" -StorySource "%~2"
