param(
  [string]$InstallDir = "$PSScriptRoot",
  [string]$TaskPrefix = "Outlook Mail Report",
  [string]$ReportTimes = "08:10,11:45,15:45"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $InstallDir "OutlookMailReporter.ps1"
if (-not (Test-Path $scriptPath)) {
  throw "Cannot find $scriptPath"
}

$outputDir = Join-Path $InstallDir "reports"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

foreach ($timeText in $ReportTimes.Split(",")) {
  $timeText = $timeText.Trim()
  $taskName = "$TaskPrefix $timeText"
  $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$scriptPath`" -SinceHours 24 -Limit 300 -PreviewChars 1200 -OutputDir `"$outputDir`""
  $trigger = New-ScheduledTaskTrigger -Daily -At $timeText
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

  Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  Write-Host "Installed scheduled task: $taskName"
}

Write-Host "Done. Reports will be saved in: $outputDir"
