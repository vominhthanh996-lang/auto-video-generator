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
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $boardScript
    ) -WindowStyle Hidden
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

$taskNameClean = $TaskName.Trim()
if (-not $taskNameClean) {
    throw "TaskName cannot be empty."
}
if (-not $StorySource -and -not $StoryboardPath) {
    throw "StorySource or StoryboardPath is required."
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
$configPath = Join-Path $tempRoot ((Get-Slug $taskNameClean) + ".json")
$statusPath = Join-Path (Join-Path $tempRoot "story-task-status") ((Get-Slug $taskNameClean) + ".json")
$logPath = Join-Path $tempRoot ((Get-Slug $taskNameClean) + ".log")
$resumeScript = Join-Path $repoRootResolved "scripts\resume_story_task_on_logon.ps1"
$cleanupScript = Join-Path $repoRootResolved "scripts\cleanup_duplicate_story_tasks.ps1"
$startupFolder = [Environment]::GetFolderPath("Startup")
$startupLauncher = Join-Path $startupFolder ((Get-Slug $taskNameClean) + ".cmd")
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $statusPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null

[pscustomobject]@{
    TaskName = $taskNameClean
    StorySource = $storySourceResolved
    StoryboardPath = $storyboardPathResolved
    RepoRoot = $repoRootResolved
    ProjectsRoot = $ProjectsRoot
    ProjectRoot = $ProjectRoot
    PythonExe = "python"
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

$startupContent = @"
@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$resumeScript" -ConfigPath "$configPath"
"@
Set-Content -Path $startupLauncher -Value $startupContent -Encoding ASCII

Ensure-OpsBoard -RepoRootPath $repoRootResolved
if (Test-Path $cleanupScript) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $cleanupScript,
        "-TaskName", $taskNameClean
    ) -WindowStyle Hidden -Wait
}

$existingWorkers = @(Get-WorkerEntries -TaskFilter $taskNameClean)
if ($existingWorkers.Count -eq 0) {
    Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $resumeScript,
        "-ConfigPath", $configPath
    ) -WindowStyle Hidden
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
} | ConvertTo-Json -Compress
