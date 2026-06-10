param()

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
$scriptPath = Join-Path $scriptRoot "task_ops_board.py"
$logPath = Join-Path (Join-Path $workRoot "temp") "ops-board-server.log"
$errLogPath = Join-Path (Join-Path $workRoot "temp") "ops-board-server.err.log"

function Quote-Arg {
    param([string]$Value)
    '"' + ($Value -replace '"', '\"') + '"'
}

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

function Get-OpsBoardListenerProcessId {
    try {
        $listener = Get-NetTCPConnection -LocalAddress "127.0.0.1" -LocalPort 8765 -State Listen -ErrorAction Stop | Select-Object -First 1
        if ($listener) {
            return [int]$listener.OwningProcess
        }
    }
    catch {}
    return $null
}

function Test-OpsBoardHealthy {
    $processes = @(Get-OpsBoardProcesses)
    if ($processes.Count -ne 1) {
        return $false
    }
    $listenerPid = Get-OpsBoardListenerProcessId
    if (-not $listenerPid -or $listenerPid -ne [int]$processes[0].ProcessId) {
        return $false
    }
    if (Test-Path -LiteralPath $venvPython) {
        $expected = (Resolve-Path $venvPython).Path.ToLowerInvariant()
        $procPath = ""
        try { $procPath = (Get-Process -Id $listenerPid -ErrorAction Stop).Path } catch {}
        if (-not $procPath -or $procPath.ToLowerInvariant() -ne $expected) {
            return $false
        }
    }
    return Test-OpsBoardAlive
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

if (Test-OpsBoardHealthy) {
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

$pythonArgs = @(
    "-u",
    $scriptPath,
    "--host", "127.0.0.1",
    "--port", "8765"
) | ForEach-Object { Quote-Arg $_ }

$process = Start-Process -FilePath $pythonExe -ArgumentList ($pythonArgs -join " ") -WorkingDirectory $repoRoot -RedirectStandardOutput $logPath -RedirectStandardError $errLogPath -WindowStyle Hidden -PassThru

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
