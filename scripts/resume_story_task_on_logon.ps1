param(
    [Parameter(Mandatory = $true)]
    [string]$ConfigPath
)

$ErrorActionPreference = "Stop"
$configPathResolved = (Resolve-Path $ConfigPath).Path
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$opsScript = Join-Path $repoRoot "scripts\start_ops_board.ps1"
$workerScript = Join-Path $repoRoot "scripts\story_task_worker.ps1"
$cleanupScript = Join-Path $repoRoot "scripts\cleanup_duplicate_story_tasks.ps1"

function Test-OpsBoardAlive {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/tasks" -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-OpsBoardAlive)) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $opsScript
    ) -WindowStyle Hidden
    Start-Sleep -Seconds 2
}

if (Test-Path $cleanupScript) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $cleanupScript,
        "-ConfigPath", $configPathResolved
    ) -WindowStyle Hidden -Wait
}

$alreadyRunning = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "powershell.exe" -and $_.CommandLine -like "*story_task_worker.ps1*" -and $_.CommandLine -like "*$configPathResolved*"
}
if ($alreadyRunning) {
    exit 0
}

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $workerScript,
    "-ConfigPath", $configPathResolved
) -WindowStyle Hidden
