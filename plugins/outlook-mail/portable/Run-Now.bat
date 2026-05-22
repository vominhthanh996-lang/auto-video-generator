@echo off
powershell.exe -ExecutionPolicy Bypass -File "%~dp0OutlookMailReporter.ps1" -SinceHours 24 -Limit 300 -PreviewChars 1200 -OutputDir "%~dp0reports" -OpenReport
pause
