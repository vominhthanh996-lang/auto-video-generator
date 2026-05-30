param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName,

    [string]$StorySource = "",
    [string]$StoryboardPath = "",

    [string]$RepoRoot = "",
    [string]$ProjectsRoot = "",
    [string]$ProjectRoot = "",
    [string]$Format = "youtube",
    [string]$RunMode = "work",
    [string]$ImageMode = "comfy",
    [string]$ImageReference = "",
    [double]$ImageReferenceDenoise = 0.28,
    [string]$Voice = "vi-female",
    [string]$VoiceStyle = "wasteland-dark",
    [switch]$SkipVoice,
    [switch]$UseExistingStoryboard
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$defaultRepoRoot = Split-Path -Parent $scriptRoot
$defaultWorkRoot = Split-Path -Parent $defaultRepoRoot
$opsBoardUrl = "http://127.0.0.1:8765"

function Test-OpsBoardAlive {
    try {
        $response = Invoke-WebRequest -Uri "$opsBoardUrl/api/tasks" -UseBasicParsing -TimeoutSec 2
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Ensure-OpsBoard {
    param([string]$RepoRootPath)
    if (Test-OpsBoardAlive) {
        return
    }
    $boardScript = Join-Path $RepoRootPath "scripts\start_ops_board.ps1"
    if (-not (Test-Path $boardScript)) {
        return
    }
    $boardArgs = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $boardScript
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $boardArgs -WorkingDirectory $RepoRootPath -WindowStyle Hidden
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        if (Test-OpsBoardAlive) {
            return
        }
    }
}

function Quote-Arg {
    param([string]$Value)
    '"' + ($Value -replace '"', '\"') + '"'
}

function Join-PSArguments {
    param([string[]]$Values)
    ($Values | ForEach-Object { Quote-Arg $_ }) -join " "
}

function Get-Slug {
    param([string]$Value)
    $slug = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $slug = $slug.Trim("-")
    if (-not $slug) {
        return "story-task"
    }
    return $slug
}

function Get-WorkerEntries {
    param(
        [string]$TaskFilter = "",
        [string]$ConfigFilter = ""
    )
    $resolvedConfig = ""
    if ($ConfigFilter) {
        try { $resolvedConfig = (Resolve-Path $ConfigFilter).Path } catch { $resolvedConfig = $ConfigFilter }
    }
    $workers = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "powershell.exe" -and $_.CommandLine -like "*story_task_worker.ps1*"
    }
    $entries = foreach ($worker in $workers) {
        $configPath = ""
        if ($worker.CommandLine -match '-ConfigPath\s+"([^"]+)"') {
            $configPath = $matches[1]
        }
        elseif ($worker.CommandLine -match '-ConfigPath\s+([^\s]+)') {
            $configPath = $matches[1]
        }
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
            CommandLine = $worker.CommandLine
        }
    }
    if ($TaskFilter) {
        $entries = $entries | Where-Object { $_.TaskName -eq $TaskFilter }
    }
    if ($resolvedConfig) {
        $entries = $entries | Where-Object { $_.ConfigPath -eq $resolvedConfig }
    }
    @($entries)
}

function Get-SupervisorEntries {
    param([string]$ConfigFilter = "")
    $resolvedConfig = ""
    if ($ConfigFilter) {
        try { $resolvedConfig = (Resolve-Path $ConfigFilter).Path } catch { $resolvedConfig = $ConfigFilter }
    }
    $supervisors = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "powershell.exe" -and $_.CommandLine -like "*resume_story_task_on_logon.ps1*"
    }
    $entries = foreach ($supervisor in $supervisors) {
        $configPath = ""
        if ($supervisor.CommandLine -match '-ConfigPath\s+"([^"]+)"') {
            $configPath = $matches[1]
        }
        elseif ($supervisor.CommandLine -match '-ConfigPath\s+([^\s]+)') {
            $configPath = $matches[1]
        }
        $started = $null
        try { $started = (Get-Process -Id $supervisor.ProcessId -ErrorAction Stop).StartTime } catch {}
        [pscustomobject]@{
            ProcessId = [int]$supervisor.ProcessId
            ConfigPath = $configPath
            Started = $started
            CommandLine = $supervisor.CommandLine
        }
    }
    if ($resolvedConfig) {
        $entries = $entries | Where-Object { $_.ConfigPath -eq $resolvedConfig }
    }
    @($entries)
}

function Get-LauncherEntries {
    param([string]$TaskFilter = "")
    $launchers = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq "powershell.exe" -and
        $_.ProcessId -ne $PID -and
        $_.CommandLine -like "*start_story_task.ps1*"
    }
    $entries = foreach ($launcher in $launchers) {
        $taskName = ""
        if ($launcher.CommandLine -match '-TaskName\s+"([^"]+)"') {
            $taskName = $matches[1]
        }
        elseif ($launcher.CommandLine -match '-TaskName\s+([^\s]+)') {
            $taskName = $matches[1]
        }
        [pscustomobject]@{
            ProcessId = [int]$launcher.ProcessId
            TaskName = $taskName
            CommandLine = $launcher.CommandLine
        }
    }
    if ($TaskFilter) {
        $entries = $entries | Where-Object { $_.TaskName -eq $TaskFilter }
    }
    @($entries)
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

function Acquire-LaunchLock {
    param(
        [string]$LockPath,
        [string]$TaskValue
    )
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LockPath) | Out-Null
    if (Test-Path $LockPath) {
        try {
            $existing = Get-Content $LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $existingPid = [int]($existing.pid)
            if ($existingPid -and $existingPid -ne $PID -and (Test-PidAlive -ProcessId $existingPid)) {
                return $false
            }
        }
        catch {}
    }
    try {
        $stream = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $writer = New-Object System.IO.StreamWriter($stream, [System.Text.Encoding]::UTF8)
        $writer.Write(([pscustomobject]@{
            pid = $PID
            task = $TaskValue
            acquired_at = (Get-Date).ToString("s")
        } | ConvertTo-Json -Depth 4))
        $writer.Flush()
        $writer.Dispose()
        $stream.Dispose()
        return $true
    }
    catch {
        return $false
    }
}

function Release-LaunchLock {
    param([string]$LockPath)
    if (-not (Test-Path $LockPath)) {
        return
    }
    try {
        $existing = Get-Content $LockPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([int]($existing.pid) -eq $PID) {
            Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Remove-Item -LiteralPath $LockPath -Force -ErrorAction SilentlyContinue
    }
}

function Start-SupervisorProcess {
    param(
        [string]$ResumeScriptPath,
        [string]$WorkerConfigPath
    )
    $args = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $ResumeScriptPath,
        "-ConfigPath", $WorkerConfigPath
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory (Split-Path -Parent $ResumeScriptPath) -WindowStyle Hidden | Out-Null

    for ($i = 0; $i -lt 8; $i++) {
        Start-Sleep -Seconds 1
        $running = @(Get-SupervisorEntries -ConfigFilter $WorkerConfigPath)
        if ($running.Count -gt 0) {
            return $running
        }
    }

    return @()
}

function Start-WorkerProcess {
    param(
        [string]$WorkerScriptPath,
        [string]$WorkerConfigPath
    )
    $args = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $WorkerScriptPath,
        "-ConfigPath", $WorkerConfigPath
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $args -WorkingDirectory (Split-Path -Parent $WorkerScriptPath) -WindowStyle Hidden | Out-Null

    for ($i = 0; $i -lt 8; $i++) {
        Start-Sleep -Seconds 1
        $running = @(Get-WorkerEntries -ConfigFilter $WorkerConfigPath)
        if ($running.Count -gt 0) {
            return $running
        }
    }

    return @()
}

$taskNameClean = $TaskName.Trim()
if (-not $taskNameClean) {
    throw "TaskName cannot be empty."
}
if (-not $StorySource -and -not $StoryboardPath) {
    throw "StorySource or StoryboardPath is required."
}

$existingLaunchers = @(Get-LauncherEntries -TaskFilter $taskNameClean)
if ($existingLaunchers.Count -gt 0) {
    Write-Output ("Ops board: {0}" -f $opsBoardUrl)
    [pscustomobject]@{
        task = $taskNameClean
        already_starting = $true
        existing_launcher_count = $existingLaunchers.Count
        launcher_pids = @($existingLaunchers | Select-Object -ExpandProperty ProcessId)
        ops_board_url = $opsBoardUrl
    } | ConvertTo-Json -Compress
    exit 0
}

if (-not $RepoRoot) {
    $RepoRoot = $defaultRepoRoot
}
if (-not $ProjectsRoot) {
    $ProjectsRoot = Join-Path $defaultWorkRoot "video-projects"
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$workRootResolved = Split-Path -Parent $repoRootResolved
$storySourceResolved = if ($StorySource) { (Resolve-Path $StorySource).Path } else { "" }
$storyboardPathResolved = if ($StoryboardPath) { (Resolve-Path $StoryboardPath).Path } else { "" }
$workerPath = Join-Path $repoRootResolved "scripts\story_task_worker.ps1"
$tempRoot = Join-Path $workRootResolved "temp"
$launchLockPath = Join-Path (Join-Path $tempRoot "story-task-launch-locks") ((Get-Slug $taskNameClean) + ".lock")
$configPath = Join-Path $tempRoot ((Get-Slug $taskNameClean) + ".json")
$statusPath = Join-Path (Join-Path $tempRoot "story-task-status") ((Get-Slug $taskNameClean) + ".json")
$logPath = Join-Path $tempRoot ((Get-Slug $taskNameClean) + ".log")
$resumeScript = Join-Path $repoRootResolved "scripts\resume_story_task_on_logon.ps1"
$cleanupScript = Join-Path $repoRootResolved "scripts\cleanup_duplicate_story_tasks.ps1"
$startupFolder = [Environment]::GetFolderPath("Startup")
$startupLauncher = Join-Path $startupFolder ((Get-Slug $taskNameClean) + ".cmd")
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $statusPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null
$venvPython = Join-Path $repoRootResolved ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }

if (-not (Acquire-LaunchLock -LockPath $launchLockPath -TaskValue $taskNameClean)) {
    Write-Output ("Ops board: {0}" -f $opsBoardUrl)
    [pscustomobject]@{
        task = $taskNameClean
        already_starting = $true
        lock_path = $launchLockPath
        ops_board_url = $opsBoardUrl
    } | ConvertTo-Json -Compress
    exit 0
}

[pscustomobject]@{
    TaskName = $taskNameClean
    StorySource = $storySourceResolved
    StoryboardPath = $storyboardPathResolved
    RepoRoot = $repoRootResolved
    ProjectsRoot = $ProjectsRoot
    ProjectRoot = $ProjectRoot
    PythonExe = $pythonExe
    Format = $Format
    RunMode = $RunMode
    ImageMode = $ImageMode
    ImageReference = $ImageReference
    ImageReferenceDenoise = $ImageReferenceDenoise
    Voice = $Voice
    VoiceStyle = $VoiceStyle
    SkipVoice = [bool]$SkipVoice
    UseExistingStoryboard = [bool]$UseExistingStoryboard
} | ConvertTo-Json -Depth 4 | Set-Content -Path $configPath -Encoding UTF8

$existingWorkers = @(Get-WorkerEntries -TaskFilter $taskNameClean)
$existingSupervisors = @(Get-SupervisorEntries -ConfigFilter $configPath)
if ($existingWorkers.Count -gt 0 -or $existingSupervisors.Count -gt 0) {
    if (Test-Path $statusPath) {
        try {
            $existingState = Get-Content $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $existingState.overall = "running"
            $existingState.current_node = [string]($existingState.current_node)
            $existingState.message = "Task is already running; duplicate launch request ignored."
            $existingState.updated_at = (Get-Date).ToString("s")
            $existingState | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
        }
        catch {}
    }
    Write-Output ("Ops board: {0}" -f $opsBoardUrl)
    [pscustomobject]@{
        task = $taskNameClean
        source = $storySourceResolved
        storyboard = $storyboardPathResolved
        config = $configPath
        status = $statusPath
        log = $logPath
        startup_launcher = $startupLauncher
        resume_script = $resumeScript
        resume_mode = "startup-folder"
        ops_board_url = $opsBoardUrl
        existing_worker_count = $existingWorkers.Count
        existing_supervisor_count = $existingSupervisors.Count
        already_running = $true
    } | ConvertTo-Json -Compress
    Release-LaunchLock -LockPath $launchLockPath
    exit 0
}

if (-not (Test-Path $statusPath)) {
    [pscustomobject]@{
        task = $taskNameClean
        source = $storySourceResolved
        storyboard = $storyboardPathResolved
        project = $ProjectRoot
        log = $logPath
        qa_summary = ""
        overall = "queued"
        current_node = "queued"
        message = "Task registered and waiting to start"
        updated_at = (Get-Date).ToString("s")
        counts = @{ scenes = 0; images = 0; audio = 0 }
        nodes = @{
            storyboard = @{ status = "pending"; detail = "" }
            voice = @{ status = "pending"; detail = "" }
            images = @{ status = "pending"; detail = "" }
            render = @{ status = "pending"; detail = "" }
            qa = @{ status = "pending"; detail = "" }
        }
    } | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
}
else {
    try {
        $existingState = Get-Content $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $existingState.overall = "queued"
        $existingState.current_node = "startup"
        $existingState.message = "Launching supervisor for background processing."
        $existingState.updated_at = (Get-Date).ToString("s")
        $existingState | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
    }
    catch {}
}

$startupContent = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$resumeScript" -ConfigPath "$configPath"
"@
Set-Content -Path $startupLauncher -Value $startupContent -Encoding ASCII

Ensure-OpsBoard -RepoRootPath $repoRootResolved
if (Test-Path $cleanupScript) {
    $cleanupArgs = Join-PSArguments @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $cleanupScript,
        "-TaskName", $taskNameClean
    )
    Start-Process -FilePath "powershell.exe" -ArgumentList $cleanupArgs -WorkingDirectory (Split-Path -Parent $cleanupScript) -WindowStyle Hidden -Wait
}

$existingWorkers = @(Get-WorkerEntries -TaskFilter $taskNameClean)
$existingSupervisors = @(Get-SupervisorEntries -ConfigFilter $configPath)
if ($existingWorkers.Count -eq 0 -and $existingSupervisors.Count -eq 0) {
    $existingSupervisors = @(Start-SupervisorProcess -ResumeScriptPath $resumeScript -WorkerConfigPath $configPath)
    if ($existingSupervisors.Count -eq 0) {
        $existingWorkers = @(Start-WorkerProcess -WorkerScriptPath $workerPath -WorkerConfigPath $configPath)
    }
    if ($existingSupervisors.Count -eq 0 -and $existingWorkers.Count -eq 0 -and (Test-Path $statusPath)) {
        try {
            $state = Get-Content $statusPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $state.overall = "failed"
            $state.current_node = "startup"
            $state.message = "Unable to launch supervisor or worker."
            $state.updated_at = (Get-Date).ToString("s")
            $state | ConvertTo-Json -Depth 8 | Set-Content -Path $statusPath -Encoding UTF8
        }
        catch {}
    }
}

$taskCommandParts = @(
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Quote-Arg $workerPath),
    "-ConfigPath", (Quote-Arg $configPath)
)
$taskCommand = $taskCommandParts -join " "

Write-Output ("Ops board: {0}" -f $opsBoardUrl)
[pscustomobject]@{
    task = $taskNameClean
    source = $storySourceResolved
    storyboard = $storyboardPathResolved
    command = $taskCommand
    config = $configPath
    status = $statusPath
    log = $logPath
    startup_launcher = $startupLauncher
    resume_script = $resumeScript
    resume_mode = "startup-folder"
    ops_board_url = $opsBoardUrl
    existing_worker_count = @(Get-WorkerEntries -TaskFilter $taskNameClean).Count
    existing_supervisor_count = @(Get-SupervisorEntries -ConfigFilter $configPath).Count
} | ConvertTo-Json -Compress
Release-LaunchLock -LockPath $launchLockPath
