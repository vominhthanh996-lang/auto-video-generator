param()

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot
$pythonExe = "python"
$scriptPath = Join-Path $scriptRoot "task_ops_board.py"
$logPath = Join-Path (Join-Path $workRoot "temp") "ops-board-server.log"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null
"& $pythonExe `"$scriptPath`" --host 127.0.0.1 --port 8765 *>> `"$logPath`"" | Invoke-Expression
