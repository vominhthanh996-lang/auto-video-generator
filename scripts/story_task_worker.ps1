param(
    [string]$ConfigPath = "",
    [string]$TaskName = "",
    [string]$StorySource = "",
    [string]$StoryboardPath = "",

    [string]$RepoRoot = "",
    [string]$ProjectsRoot = "",
    [string]$ProjectRoot = "",
    [string]$PythonExe = "python",
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

function Get-Slug {
    param([string]$Value)
    $slug = $Value.ToLowerInvariant() -replace "[^a-z0-9]+", "-"
    $slug = $slug.Trim("-")
    if (-not $slug) {
        return "story-video"
    }
    return $slug
}

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $script:LogPath -Value $line -Encoding UTF8
}

function ConvertTo-PlainHashtable {
    param([object]$Value)
    if ($null -eq $Value) {
        return $null
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $table = @{}
        foreach ($key in $Value.Keys) {
            $table[$key] = ConvertTo-PlainHashtable $Value[$key]
        }
        return $table
    }
    if ($Value -is [System.Collections.IEnumerable] -and -not ($Value -is [string])) {
        $items = @()
        foreach ($item in $Value) {
            $items += ,(ConvertTo-PlainHashtable $item)
        }
        return $items
    }
    if ($Value -is [pscustomobject]) {
        $table = @{}
        foreach ($property in $Value.PSObject.Properties) {
            $table[$property.Name] = ConvertTo-PlainHashtable $property.Value
        }
        return $table
    }
    return $Value
}

function Update-TaskStatus {
    param(
        [string]$Overall = "",
        [string]$CurrentNode = "",
        [string]$Message = "",
        [hashtable]$NodeUpdates = $null
    )
    $state = $null
    if (Test-Path $script:StatusPath) {
        try {
            $state = Get-Content $script:StatusPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $state = ConvertTo-PlainHashtable $state
        }
        catch {
            $state = $null
        }
    }
    if (-not $state) {
        $state = @{
            task = $TaskName
            source = $script:StorySource
            storyboard = $script:Storyboard
            project = $script:ProjectRoot
            log = $script:LogPath
            qa_summary = $script:QASummaryPath
            overall = "queued"
            current_node = "queued"
            message = ""
            updated_at = ""
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
        }
    }
    $state.task = $TaskName
    $state.source = $script:StorySource
    $state.storyboard = $script:Storyboard
    $state.project = $script:ProjectRoot
    $state.log = $script:LogPath
    $state.qa_summary = $script:QASummaryPath
    if ($Overall) {
        $state.overall = $Overall
    }
    if ($CurrentNode) {
        $state.current_node = $CurrentNode
    }
    if ($Message) {
        $state.message = $Message
    }
    if ($NodeUpdates) {
        foreach ($key in $NodeUpdates.Keys) {
            if (-not $state.nodes.ContainsKey($key)) {
                $state.nodes[$key] = @{ status = "pending"; detail = "" }
            }
            $update = $NodeUpdates[$key]
            if ($update.ContainsKey("status")) {
                $state.nodes[$key].status = $update["status"]
            }
            if ($update.ContainsKey("detail")) {
                $state.nodes[$key].detail = $update["detail"]
            }
        }
    }
    if (Test-Path $script:Storyboard) {
        $sceneState = Get-SceneState
        $state.counts = @{
            scenes = $sceneState.SceneCount
            images = $sceneState.ImageCount
            audio = $sceneState.AudioCount
        }
    }
    $state.updated_at = (Get-Date).ToString("s")
    $state | ConvertTo-Json -Depth 8 | Set-Content -Path $script:StatusPath -Encoding UTF8
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments
    )
    Write-Log ("START {0}" -f $Label)
    Update-TaskStatus -Overall "running" -CurrentNode $Label -Message ("Running: {0}" -f $Label)
    & $script:PythonExe $FilePath @Arguments *>> $script:LogPath
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Log ("FAIL {0} (exit {1})" -f $Label, $exitCode)
        Update-TaskStatus -Overall "failed" -CurrentNode $Label -Message ("Failed: {0}" -f $Label)
        throw "{0} failed with exit code {1}" -f $Label, $exitCode
    }
    Write-Log ("DONE {0}" -f $Label)
}

function Get-SceneState {
    Ensure-StoryboardReady
    $data = Get-Content $script:Storyboard -Raw -Encoding UTF8 | ConvertFrom-Json
    $scenes = @($data.scenes)
    $images = 0
    $audio = 0
    foreach ($scene in $scenes) {
        if ($scene.image) {
            $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $script:ProjectRoot ([string]$scene.image) }
            if (Test-Path $imagePath) { $images++ }
        }
        if ($scene.audio) {
            $audioPath = if ([System.IO.Path]::IsPathRooted([string]$scene.audio)) { [string]$scene.audio } else { Join-Path $script:ProjectRoot ([string]$scene.audio) }
            if (Test-Path $audioPath) { $audio++ }
        }
    }
    [pscustomobject]@{
        SceneCount = $scenes.Count
        ImageCount = $images
        AudioCount = $audio
        Scenes = $scenes
    }
}

function Write-QASummary {
    param([string]$Stage)
    $state = Get-SceneState
    $summary = [pscustomobject]@{
        task = $TaskName
        stage = $Stage
        timestamp = (Get-Date).ToString("s")
        project = $script:ProjectRoot
        storyboard = $script:Storyboard
        scenes = $state.SceneCount
        images = $state.ImageCount
        audio = $state.AudioCount
        ready_for_render = ($state.SceneCount -gt 0 -and $state.ImageCount -ge $state.SceneCount -and ($script:SkipVoice -or $state.AudioCount -ge $state.SceneCount))
    }
    $summary | ConvertTo-Json -Depth 4 | Set-Content -Path $script:QASummaryPath -Encoding UTF8
}

function Validate-StoryboardText {
    Update-TaskStatus -CurrentNode "storyboard" -Message "Validating storyboard text" -NodeUpdates @{
        storyboard = @{ status = "running"; detail = "Validating text structure" }
    }
    Invoke-Step -Label "validate storyboard text" -FilePath (Join-Path $script:RepoRoot "scripts\validate_storyboard.py") -Arguments @(
        "--storyboard", $script:Storyboard,
        "--stage", "text"
    )
}

function Ensure-StoryboardReady {
    if (Test-Path $script:Storyboard) {
        return
    }
    if ($script:UseExistingStoryboard) {
        throw "Storyboard not found: $($script:Storyboard)"
    }
    Write-Log "STORYBOARD missing, regenerating from source"
    Update-TaskStatus -Overall "running" -CurrentNode "storyboard" -Message "Storyboard missing, rebuilding from source" -NodeUpdates @{
        storyboard = @{ status = "running"; detail = "Rebuilding missing storyboard" }
    }
    Initialize-Project
    if (-not (Test-Path $script:Storyboard)) {
        throw "Storyboard still missing after regeneration: $($script:Storyboard)"
    }
}

function Validate-StoryboardAll {
    Update-TaskStatus -CurrentNode "qa" -Message "Validating final storyboard assets" -NodeUpdates @{
        qa = @{ status = "running"; detail = "Checking storyboard against generated assets" }
    }
    Invoke-Step -Label "validate storyboard all" -FilePath (Join-Path $script:RepoRoot "scripts\validate_storyboard.py") -Arguments @(
        "--storyboard", $script:Storyboard,
        "--stage", "all"
    )
}

function Initialize-Project {
    if ($script:UseExistingStoryboard) {
        Write-Log "INIT skipped because UseExistingStoryboard=true"
        Update-TaskStatus -Overall "running" -CurrentNode "storyboard" -Message "Using existing storyboard" -NodeUpdates @{
            storyboard = @{ status = "done"; detail = "Using prebuilt storyboard" }
        }
        return
    }
    Update-TaskStatus -Overall "running" -CurrentNode "storyboard" -Message "Generating storyboard from source" -NodeUpdates @{
        storyboard = @{ status = "running"; detail = "Reading story and creating storyboard" }
    }
    $args = @(
        "--source", $script:StorySource,
        "--project", $script:ProjectRoot,
        "--format", $script:Format,
        "--image-mode", $script:ImageMode,
        "--run-mode", $script:RunMode,
        "--image-reference", $script:ImageReference,
        "--image-reference-denoise", [string]$script:ImageReferenceDenoise,
        "--skip-images",
        "--skip-voice",
        "--skip-sfx",
        "--skip-render"
    )
    Invoke-Step -Label "initialize project" -FilePath (Join-Path $script:RepoRoot "scripts\run_story_pipeline.py") -Arguments $args
}

function Invoke-VoiceAttempt {
    param([int]$Attempt)
    if ($script:SkipVoice) {
        Write-Log "VOICE skipped by request"
        Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice skipped" -NodeUpdates @{
            voice = @{ status = "skipped"; detail = "Voice generation skipped by config" }
        }
        return $true
    }
    $state = Get-SceneState
    if ($state.AudioCount -ge $state.SceneCount) {
        Write-Log ("VOICE complete {0}/{1}" -f $state.AudioCount, $state.SceneCount)
        Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice complete" -NodeUpdates @{
            voice = @{ status = "done"; detail = ("Audio ready {0}/{1}" -f $state.AudioCount, $state.SceneCount) }
        }
        return $true
    }
    $voiceArgs = @(
        "--storyboard", $script:Storyboard,
        "--voice", $script:Voice,
        "--voice-style", $script:VoiceStyle
    )
    if (Test-Path $script:CharacterBible) {
        $voiceArgs += @("--character-bible", $script:CharacterBible)
    }
    Write-Log ("VOICE attempt {0}: current {1}/{2}" -f $Attempt, $state.AudioCount, $state.SceneCount)
    Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message ("Voice attempt {0}" -f $Attempt) -NodeUpdates @{
        voice = @{ status = "running"; detail = ("Attempt {0}, audio {1}/{2}" -f $Attempt, $state.AudioCount, $state.SceneCount) }
    }
    try {
        Invoke-Step -Label ("voice attempt {0}" -f $Attempt) -FilePath (Join-Path $script:RepoRoot "scripts\generate_voice_edge.py") -Arguments $voiceArgs
    }
    catch {
        Write-Log ("VOICE retry after error: {0}" -f $_.Exception.Message)
        Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice retrying after error" -NodeUpdates @{
            voice = @{ status = "warning"; detail = $_.Exception.Message }
        }
    }
    $after = Get-SceneState
    if ($after.AudioCount -ge $after.SceneCount) {
        Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice complete" -NodeUpdates @{
            voice = @{ status = "done"; detail = ("Audio ready {0}/{1}" -f $after.AudioCount, $after.SceneCount) }
        }
        return $true
    }
    return $false
}

function Invoke-ImageStep {
    $state = Get-SceneState
    if ($state.ImageCount -ge $state.SceneCount) {
        Write-Log ("IMAGES complete {0}/{1}" -f $state.ImageCount, $state.SceneCount)
        Update-TaskStatus -Overall "running" -CurrentNode "images" -Message "Images complete" -NodeUpdates @{
            images = @{ status = "done"; detail = ("Images ready {0}/{1}" -f $state.ImageCount, $state.SceneCount) }
        }
        return $true
    }

    $targetScene = $null
    for ($i = 0; $i -lt $state.Scenes.Count; $i++) {
        $scene = $state.Scenes[$i]
        $imagePath = $null
        if ($scene.image) {
            $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $script:ProjectRoot ([string]$scene.image) }
        }
        if (-not $imagePath -or -not (Test-Path $imagePath)) {
            $targetScene = $i + 1
            break
        }
    }

    if (-not $targetScene) {
        return $true
    }
    Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Generating image scene {0}" -f $targetScene) -NodeUpdates @{
        images = @{ status = "running"; detail = ("Current scene {0}, images {1}/{2}" -f $targetScene, $state.ImageCount, $state.SceneCount) }
    }

    $imageArgs = @(
        "--storyboard", $script:Storyboard,
        "--aspect-ratio", $script:AspectRatio,
        "--final-width", [string]$script:FinalWidth,
        "--final-height", [string]$script:FinalHeight,
        "--preset", "balanced",
        "--start-scene", [string]$targetScene,
        "--end-scene", [string]$targetScene,
        "--reference-image", $script:ImageReference,
        "--reference-denoise", [string]$script:ImageReferenceDenoise
    )
    Invoke-Step -Label ("image scene {0}" -f $targetScene) -FilePath (Join-Path $script:RepoRoot "scripts\generate_images_comfy_local.py") -Arguments $imageArgs
    Start-Sleep -Seconds 5
    return $false
}

function Invoke-FinalRender {
    Update-TaskStatus -Overall "running" -CurrentNode "render" -Message "Rendering final video" -NodeUpdates @{
        render = @{ status = "running"; detail = "Rendering final mp4" }
    }
    $args = @(
        "--source", $script:StorySource,
        "--project", $script:ProjectRoot,
        "--format", $script:Format,
        "--image-mode", $script:ImageMode,
        "--run-mode", $script:RunMode,
        "--image-reference", $script:ImageReference,
        "--image-reference-denoise", [string]$script:ImageReferenceDenoise,
        "--skip-images",
        "--skip-voice"
    )
    Invoke-Step -Label "final render" -FilePath (Join-Path $script:RepoRoot "scripts\run_story_pipeline.py") -Arguments $args
}

if ($ConfigPath) {
    $config = Get-Content $ConfigPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $TaskName = [string]$config.TaskName
    $StorySource = [string]$config.StorySource
    $StoryboardPath = [string]$config.StoryboardPath
    $RepoRoot = [string]$config.RepoRoot
    $ProjectsRoot = [string]$config.ProjectsRoot
    $ProjectRoot = [string]$config.ProjectRoot
    $PythonExe = [string]$config.PythonExe
    $Format = [string]$config.Format
    $RunMode = [string]$config.RunMode
    $ImageMode = [string]$config.ImageMode
    $ImageReference = [string]$config.ImageReference
    $ImageReferenceDenoise = [double]$config.ImageReferenceDenoise
    $Voice = [string]$config.Voice
    $VoiceStyle = [string]$config.VoiceStyle
    $SkipVoice = [bool]$config.SkipVoice
    $UseExistingStoryboard = [bool]$config.UseExistingStoryboard
}

if (-not $RepoRoot) {
    $RepoRoot = $defaultRepoRoot
}
if (-not $ProjectsRoot) {
    $ProjectsRoot = Join-Path $defaultWorkRoot "video-projects"
}

if (-not $TaskName) {
    throw "TaskName is required."
}
if (-not $StorySource -and -not $StoryboardPath) {
    throw "StorySource or StoryboardPath is required."
}

$script:RepoRoot = (Resolve-Path $RepoRoot).Path
$script:PythonExe = $PythonExe
$script:Format = $Format
$script:RunMode = $RunMode
$script:ImageMode = $ImageMode
$script:ImageReference = $ImageReference
$script:ImageReferenceDenoise = $ImageReferenceDenoise
$script:Voice = $Voice
$script:VoiceStyle = $VoiceStyle
$script:SkipVoice = [bool]$SkipVoice
$script:UseExistingStoryboard = [bool]$UseExistingStoryboard

if ($StorySource) {
    $script:StorySource = (Resolve-Path $StorySource).Path
}
else {
    $script:StorySource = ""
}

if ($StoryboardPath) {
    $script:Storyboard = (Resolve-Path $StoryboardPath).Path
    $script:ProjectRoot = Split-Path -Parent $script:Storyboard
}
else {
    $projectSlug = Get-Slug ([System.IO.Path]::GetFileNameWithoutExtension($script:StorySource))
    $script:ProjectRoot = if ($ProjectRoot) { $ProjectRoot } else { Join-Path $ProjectsRoot $projectSlug }
    $script:ProjectRoot = [System.IO.Path]::GetFullPath($script:ProjectRoot)
    $script:Storyboard = Join-Path $script:ProjectRoot "storyboard.json"
}
$script:CharacterBible = Join-Path $script:ProjectRoot "character_voice_bible.json"
$tempRoot = Join-Path (Split-Path -Parent $script:RepoRoot) "temp"
$script:LogPath = Join-Path $tempRoot ("{0}.log" -f (Get-Slug $TaskName))
$script:QASummaryPath = Join-Path $script:ProjectRoot "qa-summary.json"
$script:StatusPath = Join-Path (Join-Path $tempRoot "story-task-status") ((Get-Slug $TaskName) + ".json")

if ($script:UseExistingStoryboard -and -not (Test-Path $script:Storyboard)) {
    throw "Storyboard not found: $($script:Storyboard)"
}

switch ($script:Format) {
    "youtube" {
        $script:AspectRatio = "16:9"
        $script:FinalWidth = 1920
        $script:FinalHeight = 1080
    }
    "tiktok" {
        $script:AspectRatio = "9:16"
        $script:FinalWidth = 1080
        $script:FinalHeight = 1920
    }
    default {
        throw "Unsupported format: $($script:Format)"
    }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $script:LogPath) | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $script:StatusPath) | Out-Null
Write-Log "JOB START"
Write-Log ("TASK {0}" -f $TaskName)
if ($script:StorySource) {
    Write-Log ("SOURCE {0}" -f $script:StorySource)
}
Write-Log ("STORYBOARD {0}" -f $script:Storyboard)
Write-Log ("PROJECT {0}" -f $script:ProjectRoot)
Update-TaskStatus -Overall "running" -CurrentNode "storyboard" -Message "Task started" -NodeUpdates @{
    storyboard = @{ status = "pending"; detail = "Waiting for initialization" }
    voice = @{ status = "pending"; detail = "" }
    images = @{ status = "pending"; detail = "" }
    render = @{ status = "pending"; detail = "" }
    qa = @{ status = "pending"; detail = "" }
}

Push-Location $script:RepoRoot
try {
    Initialize-Project
    Validate-StoryboardText
    Update-TaskStatus -Overall "running" -CurrentNode "storyboard" -Message "Storyboard ready" -NodeUpdates @{
        storyboard = @{ status = "done"; detail = "Storyboard validated" }
    }
    Write-QASummary -Stage "storyboard-ready"
    $voiceReady = [bool]$script:SkipVoice
    $imageReady = $false
    $voiceAttempt = 0
    while (-not ($voiceReady -and $imageReady)) {
        if (-not $voiceReady -and -not $script:SkipVoice) {
            $voiceAttempt++
            $voiceReady = Invoke-VoiceAttempt -Attempt $voiceAttempt
            Write-QASummary -Stage ("voice-pass-{0}" -f $voiceAttempt)
        }
        if (-not $imageReady) {
            $imageReady = Invoke-ImageStep
            Write-QASummary -Stage "image-step"
        }
        if ($voiceReady -and $imageReady) {
            break
        }
        if ($voiceAttempt -ge 12 -and -not $voiceReady -and $imageReady) {
            break
        }
    }
    if ($voiceReady -or $script:SkipVoice) {
        Validate-StoryboardAll
        Update-TaskStatus -Overall "running" -CurrentNode "qa" -Message "QA passed, ready to render" -NodeUpdates @{
            qa = @{ status = "done"; detail = "Storyboard/assets validation passed" }
        }
        Write-QASummary -Stage "ready-for-render"
        Invoke-FinalRender
        Update-TaskStatus -Overall "success" -CurrentNode "render" -Message "Render finished" -NodeUpdates @{
            render = @{ status = "done"; detail = "Final mp4 rendered" }
        }
        Write-QASummary -Stage "render-finished"
        Write-Log "JOB SUCCESS"
    }
    else {
        Update-TaskStatus -Overall "warning" -CurrentNode "voice" -Message "Images finished but voice incomplete" -NodeUpdates @{
            render = @{ status = "blocked"; detail = "Render waiting for full audio" }
            qa = @{ status = "warning"; detail = "Partial output only" }
        }
        Write-QASummary -Stage "partial-output"
        Write-Log "JOB PARTIAL: images finished, voice incomplete, render skipped"
    }
}
catch {
    Write-Log ("JOB ERROR: {0}" -f $_.Exception.Message)
    Update-TaskStatus -Overall "failed" -CurrentNode "error" -Message $_.Exception.Message
    throw
}
finally {
    Pop-Location
}
