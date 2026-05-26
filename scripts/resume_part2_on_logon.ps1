param()

$ErrorActionPreference = "Stop"

$repoRoot = "E:\ThanhMV\auto-video-generator"
$workerScript = Join-Path $repoRoot "scripts\story_task_worker.ps1"
$boardScript = Join-Path $repoRoot "scripts\start_ops_board.ps1"
$configPath = "E:\ThanhMV\temp\autovideo-phan02-youtube-worklocal.json"
$pythonExe = "C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"

if (-not (Test-Path $configPath)) {
    Write-Output "Missing config: $configPath"
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
    $statusUrl = "http://127.0.0.1:8765/api/tasks"
    Invoke-WebRequest -Uri $statusUrl -UseBasicParsing -TimeoutSec 3 | Out-Null
}
catch {
}

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $workerScript,
    "-ConfigPath", $configPath
) -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
