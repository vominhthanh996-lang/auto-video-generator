param(
    [string]$ConfigPath = ""
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot
$boardScript = Join-Path $repoRoot "scripts\start_ops_board.ps1"
$resumeScript = Join-Path $repoRoot "scripts\resume_story_task_on_logon.ps1"

if (-not $ConfigPath) {
    $ConfigPath = Join-Path $workRoot "temp\autovideo-tap-01-part-02-youtube-worklocal.json"
}

if (-not (Test-Path $ConfigPath)) {
    Write-Output "Missing config: $ConfigPath"
    exit 0
}

try {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $boardScript
    ) -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
}
catch {
}

Start-Sleep -Seconds 2

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/tasks" -UseBasicParsing -TimeoutSec 3 | Out-Null
}
catch {
}

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $resumeScript,
    "-ConfigPath", $ConfigPath
) -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
