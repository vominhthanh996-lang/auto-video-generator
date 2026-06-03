param(
    [string]$TaskName = "",
    [string]$ConfigPath = "",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

function Get-ResolvedConfigPath {
    param([string]$Value)
    if (-not $Value) { return "" }
    try { return (Resolve-Path $Value).Path } catch { return $Value }
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

function Get-WorkerEntries {
    $workers = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "powershell.exe" -and $_.CommandLine -like "*story_task_worker.ps1*"
    }
    foreach ($worker in $workers) {
        $configPath = Get-ArgumentValueFromCommandLine -CommandLine $worker.CommandLine -ArgumentName "-ConfigPath"
        $taskName = ""
        if ($configPath -and (Test-Path $configPath)) {
            try {
                $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
                $taskName = [string]$cfg.TaskName
            }
            catch {}
        }
        $started = $null
        try { $started = (Get-Process -Id $worker.ProcessId -ErrorAction Stop).StartTime } catch {}
        [pscustomobject]@{
            ProcessId = [int]$worker.ProcessId
            TaskName = $taskName
            ConfigPath = $configPath
            Started = $started
        }
    }
}

$resolvedConfig = Get-ResolvedConfigPath $ConfigPath
$entries = @(Get-WorkerEntries)
if ($TaskName) {
    $entries = @($entries | Where-Object { $_.TaskName -eq $TaskName })
}
if ($resolvedConfig) {
    $entries = @($entries | Where-Object { $_.ConfigPath -eq $resolvedConfig })
}

$groups = @()
if ($resolvedConfig) {
    $groups = ,@($entries)
}
elseif ($TaskName) {
    $groups = ,@($entries)
}
else {
    $groups = @($entries | Group-Object -Property TaskName)
}

$stopped = @()
foreach ($group in $groups) {
    $items = if ($group -is [array]) { $group } else { @($group.Group) }
    $ordered = @($items | Sort-Object @{Expression={ if ($_.Started) { $_.Started } else { [datetime]::MinValue } }} -Descending)
    if ($ordered.Count -le 1) { continue }
    $dupes = $ordered | Select-Object -Skip 1
    foreach ($dupe in $dupes) {
        $stopped += $dupe.ProcessId
        if (-not $WhatIf) {
            Stop-Process -Id $dupe.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

[pscustomobject]@{
    task = $TaskName
    config = $resolvedConfig
    seen = @($entries).Count
    stopped = @($stopped)
    kept = @($entries | Sort-Object Started -Descending | Select-Object -First 1 ProcessId,TaskName,ConfigPath,Started)
} | ConvertTo-Json -Depth 4
