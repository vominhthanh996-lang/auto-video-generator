param()

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot
$pythonExe = "python"
$scriptPath = Join-Path $scriptRoot "task_ops_board.py"
$logPath = Join-Path (Join-Path $workRoot "temp") "ops-board-server.log"
$errLogPath = Join-Path (Join-Path $workRoot "temp") "ops-board-server.err.log"

function Test-OpsBoardAlive {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/tasks" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Get-OpsBoardProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -match "python" -and $_.CommandLine -like "*task_ops_board.py*"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

if (Test-OpsBoardAlive) {
    exit 0
}

$alreadyRunning = @(Get-OpsBoardProcesses)
if ($alreadyRunning.Count -gt 0) {
    foreach ($proc in $alreadyRunning) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
        }
        catch {}
    }
    Start-Sleep -Seconds 2
}

$process = Start-Process -FilePath $pythonExe -ArgumentList @(
    $scriptPath,
    "--host", "127.0.0.1",
    "--port", "8765"
) -RedirectStandardOutput $logPath -RedirectStandardError $errLogPath -WindowStyle Hidden -PassThru

for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    if (Test-OpsBoardAlive) {
        exit 0
    }
    if ($process.HasExited) {
        break
    }
}

throw "Ops board did not start on http://127.0.0.1:8765"
