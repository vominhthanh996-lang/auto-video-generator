param()

$ErrorActionPreference = "Stop"

$pythonExe = "C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$scriptPath = "E:\ThanhMV\auto-video-generator\scripts\task_ops_board.py"
$logPath = "E:\ThanhMV\temp\ops-board-server.log"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null
"& $pythonExe `"$scriptPath`" --host 127.0.0.1 --port 8765 *>> `"$logPath`"" | Invoke-Expression
