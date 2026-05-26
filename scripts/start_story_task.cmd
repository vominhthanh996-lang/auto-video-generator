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

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "E:\ThanhMV\auto-video-generator\scripts\start_story_task.ps1" -TaskName "%~1" -StorySource "%~2"
