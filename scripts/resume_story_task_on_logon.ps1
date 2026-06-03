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

function Quote-Arg {
    param([string]$Value)
    '"' + ($Value -replace '"', '\"') + '"'
}

function Join-PSArguments {
    param([string[]]$Values)
    ($Values | ForEach-Object { Quote-Arg $_ }) -join " "
}

function Get-ArgumentValueFromCommandLine {
    param(
        [string]$CommandLine,
        [string]$ArgumentName
    )
    if (-not $CommandLine -or -not $ArgumentName) {
        return ""
    }
    $escaped = [Regex]::Escape($ArgumentName)
    $patterns = @(
        ('"{0}"\s+"([^"]+)"' -f $escaped),
        ('{0}\s+"([^"]+)"' -f $escaped),
        ('"{0}"\s+([^\s]+)' -f $escaped),
        ('{0}\s+([^\s]+)' -f $escaped)
    )
    foreach ($pattern in $patterns) {
        if ($CommandLine -match $pattern) {
            return $matches[1]
        }
    }
    return ""
}

function Test-OpsBoardAlive {
    try {
        Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/tasks" -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Ensure-OpsBoard {
    if (Test-OpsBoardAlive) {
        return
    }
    $opsArgs = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $opsScript
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $opsArgs -WorkingDirectory $repoRoot -WindowStyle Hidden
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-OpsBoardAlive) {
            return
        }
    }
}

function Get-WorkerEntries {
    $workers = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "powershell.exe" -and $_.CommandLine -like "*story_task_worker.ps1*"
    }
    foreach ($worker in $workers) {
        $configPath = Get-ArgumentValueFromCommandLine -CommandLine $worker.CommandLine -ArgumentName "-ConfigPath"
        if ($configPath -ne $configPathResolved) {
            continue
        }
        $started = $null
        try { $started = (Get-Process -Id $worker.ProcessId -ErrorAction Stop).StartTime } catch {}
        [pscustomobject]@{
            ProcessId = [int]$worker.ProcessId
            ConfigPath = $configPath
            Started = $started
            CommandLine = $worker.CommandLine
        }
    }
}

function Get-StatusContext {
    try {
        $cfg = Get-Content $configPathResolved -Raw -Encoding UTF8 | ConvertFrom-Json
        $taskName = [string]$cfg.TaskName
        $slug = $taskName.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
        $slug = $slug.Trim("-")
        if (-not $slug) {
            $slug = "story-task"
        }
        $tempRoot = Join-Path (Split-Path -Parent $repoRoot) "temp"
        $statusPath = Join-Path (Join-Path $tempRoot "story-task-status") ($slug + ".json")
        $lockPath = Join-Path (Join-Path $tempRoot "story-task-locks") ($slug + ".lock")
        return [pscustomobject]@{
            TaskName = $taskName
            StatusPath = $statusPath
            LockPath = $lockPath
        }
    }
    catch {
        return $null
    }
}

function Test-PidAlive {
    param([int]$ProcessId)
    try {
        Get-Process -Id $ProcessId -ErrorAction Stop | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Test-WorkerLockActive {
    param($Context)
    if ($null -eq $Context -or -not $Context.LockPath -or -not (Test-Path $Context.LockPath)) {
        return $false
    }
    try {
        $lock = Get-Content $Context.LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $pid = [int]$lock.pid
        if ($pid -and (Test-PidAlive -ProcessId $pid)) {
            return $true
        }
    }
    catch {}
    return $false
}

function Get-TaskState {
    param([string]$StatusPath)
    if (-not (Test-Path $StatusPath)) {
        return $null
    }
    try {
        return Get-Content $StatusPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Get-ProgressKey {
    param($State)
    if ($null -eq $State) {
        return ""
    }
    $images = 0
    $audio = 0
    $updated = ""
    $node = ""
    try { $images = [int]$State.counts.images } catch {}
    try { $audio = [int]$State.counts.audio } catch {}
    try { $updated = [string]$State.updated_at } catch {}
    try { $node = [string]$State.current_node } catch {}
    return "{0}|{1}|{2}|{3}" -f $images, $audio, $node, $updated
}

function Start-Worker {
    if (Test-Path $cleanupScript) {
        $cleanupArgs = Join-PSArguments @(
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", $cleanupScript,
            "-ConfigPath", $configPathResolved
        )
        Start-Process -FilePath "powershell.exe" -ArgumentList $cleanupArgs -WorkingDirectory $repoRoot -WindowStyle Hidden -Wait
    }
    $workerArgs = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $workerScript,
        "-ConfigPath", $configPathResolved
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $workerArgs -WorkingDirectory $repoRoot -WindowStyle Hidden | Out-Null
}

$statusContext = Get-StatusContext
$lastProgress = ""
$crashLoops = 0
$maxCrashLoops = 12

Ensure-OpsBoard

while ($true) {
    $state = if ($statusContext) { Get-TaskState -StatusPath $statusContext.StatusPath } else { $null }
    if ($state -and @("paused", "terminated") -contains [string]$state.overall) {
        exit 0
    }
    if ($state -and @("success", "warning") -contains [string]$state.overall) {
        exit 0
    }

    $progressKey = Get-ProgressKey -State $state
    if ($progressKey -and $progressKey -ne $lastProgress) {
        $lastProgress = $progressKey
        $crashLoops = 0
    }

    $workers = @(Get-WorkerEntries)
    if ($workers.Count -eq 0) {
        if (Test-WorkerLockActive -Context $statusContext) {
            Start-Sleep -Seconds 10
            continue
        }
        Start-Worker
        Start-Sleep -Seconds 5
        $workers = @(Get-WorkerEntries)
        if ($workers.Count -eq 0) {
            $crashLoops++
            if ($statusContext -and (Test-Path $statusContext.StatusPath)) {
                try {
                    $current = Get-TaskState -StatusPath $statusContext.StatusPath
                    if ($current) {
                        $current.current_node = "supervisor"
                        if ($crashLoops -ge $maxCrashLoops) {
                            $current.overall = "failed"
                            $current.message = "Worker exited too quickly too many times; supervisor stopped retrying."
                        }
                        else {
                            $current.overall = "running"
                            $current.message = "Worker restart in progress ($crashLoops/$maxCrashLoops)."
                        }
                        $current.updated_at = (Get-Date).ToString("s")
                        $current | ConvertTo-Json -Depth 8 | Set-Content -Path $statusContext.StatusPath -Encoding UTF8
                    }
                }
                catch {}
            }
            if ($crashLoops -ge $maxCrashLoops) {
                exit 1
            }
            Start-Sleep -Seconds 10
            continue
        }
    }
    elseif ($statusContext -and (Test-Path $statusContext.StatusPath)) {
        try {
            $current = Get-TaskState -StatusPath $statusContext.StatusPath
            if ($current -and @("failed", "queued") -contains [string]$current.overall -and @("supervisor", "startup") -contains [string]$current.current_node) {
                $current.overall = "running"
                $current.message = "Worker restarted and task is continuing."
                $current.updated_at = (Get-Date).ToString("s")
                $current | ConvertTo-Json -Depth 8 | Set-Content -Path $statusContext.StatusPath -Encoding UTF8
            }
        }
        catch {}
    }

    Start-Sleep -Seconds 15
}
