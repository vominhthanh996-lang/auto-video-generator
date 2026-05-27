param(
    [Parameter(Mandatory = $true)]
    [string]$TaskName,

    [string]$StorySource = "",
    [string]$StoryboardPath = "",

    [string]$RepoRoot = "E:\ThanhMV\auto-video-generator",
    [string]$ProjectsRoot = "E:\ThanhMV\video-projects",
    [string]$ProjectRoot = "",
    [string]$Format = "youtube",
    [string]$RunMode = "work",
    [string]$ImageMode = "comfy",
    [string]$ImageReference = "C:\Users\thanh\Downloads\fb8d05e9-8752-4bc9-912c-85580d64d714.png",
    [double]$ImageReferenceDenoise = 0.28,
    [string]$Voice = "vi-female",
    [string]$VoiceStyle = "wasteland-dark",
    [switch]$SkipVoice,
    [switch]$UseExistingStoryboard
)

$ErrorActionPreference = "Stop"

function Test-OpsBoardAlive {
    try {
        $response = Invoke-WebRequest -Uri "http://127.0.0.1:8765/api/tasks" -UseBasicParsing -TimeoutSec 2
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
    Start-Sleep -Seconds 2
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

$taskNameClean = $TaskName.Trim()
if (-not $taskNameClean) {
    throw "TaskName cannot be empty."
}
if (-not $StorySource -and -not $StoryboardPath) {
    throw "StorySource or StoryboardPath is required."
}

$repoRootResolved = (Resolve-Path $RepoRoot).Path
$storySourceResolved = if ($StorySource) { (Resolve-Path $StorySource).Path } else { "" }
$storyboardPathResolved = if ($StoryboardPath) { (Resolve-Path $StoryboardPath).Path } else { "" }
$workerPath = Join-Path $repoRootResolved "scripts\story_task_worker.ps1"
$configPath = Join-Path "E:\ThanhMV\temp" ((Get-Slug $taskNameClean) + ".json")
$statusPath = Join-Path "E:\ThanhMV\temp\story-task-status" ((Get-Slug $taskNameClean) + ".json")
$logPath = Join-Path "E:\ThanhMV\temp" ((Get-Slug $taskNameClean) + ".log")
$resumeScript = Join-Path $repoRootResolved "scripts\resume_story_task_on_logon.ps1"
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
    PythonExe = "C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
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
    counts = @{
        scenes = 0
        images = 0
        audio = 0
    }
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

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", $resumeScript,
    "-ConfigPath", $configPath
) -WindowStyle Hidden

$taskCommandParts = @(
    "powershell.exe",
    "-NoProfile",
    "-ExecutionPolicy", "Bypass",
    "-File", (Quote-Arg $workerPath),
    "-ConfigPath", (Quote-Arg $configPath)
)
$taskCommand = $taskCommandParts -join " "

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
} | ConvertTo-Json -Compress
