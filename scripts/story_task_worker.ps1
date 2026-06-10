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
$PSNativeCommandUseErrorActionPreference = $false
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

function Acquire-WorkerLock {
    New-Item -ItemType Directory -Force -Path $script:WorkerLockDir | Out-Null
    if (Test-Path $script:WorkerLockPath) {
        $staleLock = $false
        try {
            $existing = Get-Content $script:WorkerLockPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $existingPid = [int]($existing.pid)
            if ($existingPid -and $existingPid -ne $PID -and (Test-PidAlive -ProcessId $existingPid)) {
                return $false
            }
            $staleLock = $true
        }
        catch {
            $staleLock = $true
        }
        if ($staleLock) {
            try {
                Remove-Item -LiteralPath $script:WorkerLockPath -Force -ErrorAction Stop
            }
            catch {}
        }
    }
    try {
        $stream = [System.IO.File]::Open($script:WorkerLockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
        $writer = New-Object System.IO.StreamWriter($stream, [System.Text.Encoding]::UTF8)
        $writer.Write(([pscustomobject]@{
            pid = $PID
            task = $TaskName
            config = $ConfigPath
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

function Release-WorkerLock {
    if (-not (Test-Path $script:WorkerLockPath)) {
        return
    }
    try {
        $existing = Get-Content $script:WorkerLockPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([int]($existing.pid) -eq $PID) {
            Remove-Item -LiteralPath $script:WorkerLockPath -Force -ErrorAction SilentlyContinue
        }
    }
    catch {
        Remove-Item -LiteralPath $script:WorkerLockPath -Force -ErrorAction SilentlyContinue
    }
}

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $script:LogPath -Value $line -Encoding UTF8
}

function Enter-RenderMode {
    $syncProcessNames = @(
        "OneDrive",
        "OneDrive.Sync.Service",
        "Dropbox"
    )
    $stopped = @()
    foreach ($name in $syncProcessNames) {
        $processes = @(Get-Process -Name $name -ErrorAction SilentlyContinue)
        foreach ($process in $processes) {
            try {
                $stopped += [pscustomobject]@{
                    name = $process.ProcessName
                    id = $process.Id
                    path = $process.Path
                }
                Stop-Process -Id $process.Id -Force -ErrorAction Stop
            }
            catch {
                Write-Log ("RENDER MODE unable to stop {0}#{1}: {2}" -f $process.ProcessName, $process.Id, $_.Exception.Message)
            }
        }
    }
    if ($stopped.Count -gt 0) {
        $summary = ($stopped | ForEach-Object { "{0}#{1}" -f $_.name, $_.id }) -join ", "
        Write-Log ("RENDER MODE stopped sync apps: {0}" -f $summary)
    }
    else {
        Write-Log "RENDER MODE no OneDrive/Dropbox processes found"
    }
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
                image_skipped = 0
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
            image_skipped = $sceneState.ImageSkippedCount
        }
    }
    $state.updated_at = (Get-Date).ToString("s")
    $state | ConvertTo-Json -Depth 8 | Set-Content -Path $script:StatusPath -Encoding UTF8
}

function ConvertTo-ProcessArgument {
    param([string]$Value)
    if ($null -eq $Value) {
        return '""'
    }
    return '"' + ($Value -replace '"', '\"') + '"'
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments
    )
    Write-Log ("START {0}" -f $Label)
    Update-TaskStatus -Overall "running" -CurrentNode $Label -Message ("Running: {0}" -f $Label)
    $tempBase = Join-Path ([System.IO.Path]::GetTempPath()) ("story-step-{0}-{1}" -f ([System.IO.Path]::GetFileNameWithoutExtension($FilePath)), ([System.Guid]::NewGuid().ToString("N")))
    $stdoutPath = "$tempBase.out"
    $stderrPath = "$tempBase.err"
    $argumentLine = (@($FilePath) + $Arguments | ForEach-Object { ConvertTo-ProcessArgument ([string]$_) }) -join " "
    $proc = Start-Process -FilePath $script:PythonExe -ArgumentList $argumentLine -NoNewWindow -PassThru -Wait -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
    if (Test-Path $stdoutPath) {
        $stdoutText = Get-Content -Path $stdoutPath -Raw -Encoding UTF8
        if ($stdoutText) {
            $stdoutText | Out-File -FilePath $script:LogPath -Append -Encoding utf8
        }
        Remove-Item -LiteralPath $stdoutPath -Force -ErrorAction SilentlyContinue
    }
    if (Test-Path $stderrPath) {
        $stderrText = Get-Content -Path $stderrPath -Raw -Encoding UTF8
        if ($stderrText) {
            $stderrText | Out-File -FilePath $script:LogPath -Append -Encoding utf8
        }
        Remove-Item -LiteralPath $stderrPath -Force -ErrorAction SilentlyContinue
    }
    $exitCode = $proc.ExitCode
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
    $imageSkipped = 0
    foreach ($scene in $scenes) {
        if ($scene.image) {
            $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $script:ProjectRoot ([string]$scene.image) }
            if (Test-Path $imagePath) { $images++ }
        }
        if ($scene.audio) {
            $audioPath = if ([System.IO.Path]::IsPathRooted([string]$scene.audio)) { [string]$scene.audio } else { Join-Path $script:ProjectRoot ([string]$scene.audio) }
            if (Test-Path $audioPath) {
                $audioFile = Get-Item -LiteralPath $audioPath -ErrorAction SilentlyContinue
                if ($audioFile -and $audioFile.Length -ge 1024) { $audio++ }
            }
        }
        try {
            if ([string]$scene.local_image.validator.status -eq "skipped_after_failed_attempts") {
                $imageSkipped++
            }
        }
        catch {}
    }
    [pscustomobject]@{
        SceneCount = $scenes.Count
        ImageCount = $images
        AudioCount = $audio
        ImageSkippedCount = $imageSkipped
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

function Get-ManualQARequestPath {
    $requestDir = Join-Path (Split-Path -Parent $script:RepoRoot) "temp\story-qa-requests"
    return (Join-Path $requestDir ((Get-Slug $TaskName) + ".json"))
}

function Test-ManualQAPassed {
    $requestPath = Get-ManualQARequestPath
    if (-not (Test-Path $requestPath)) {
        return $false
    }
    try {
        $request = Get-Content $requestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $status = ([string]$request.status).ToLowerInvariant()
        return ($status -in @("passed", "pass", "approved", "done"))
    }
    catch {
        return $false
    }
}

function Block-RenderUntilManualQA {
    $requestPath = Get-ManualQARequestPath
    Write-Log ("RENDER BLOCKED waiting for manual Codex QA pass: {0}" -f $requestPath)
    Update-TaskStatus -Overall "warning" -CurrentNode "qa" -Message "Waiting for manual Codex QA check before render" -NodeUpdates @{
        qa = @{ status = "waiting"; detail = ("Click QA check, then wait for Codex visual QA to pass. Request file: {0}" -f $requestPath) }
        render = @{ status = "blocked"; detail = "Final render blocked until manual QA status is passed" }
    }
    Write-QASummary -Stage "waiting-for-manual-qa"
}

function Test-ComfyApiAlive {
    param([string]$Url = "http://127.0.0.1:8188/system_stats")
    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
        return ($response.StatusCode -eq 200)
    }
    catch {
        return $false
    }
}

function Ensure-ComfyService {
    if (Test-ComfyApiAlive) {
        Write-Log "COMFYUI already alive"
        return
    }
    $comfyServiceScript = Join-Path $script:RepoRoot "scripts\start_comfyui_service.ps1"
    if (-not (Test-Path $comfyServiceScript)) {
        throw "ComfyUI service script not found: $comfyServiceScript"
    }
    Write-Log "ENSURE ComfyUI service"
    $taskSlug = Get-Slug $script:TaskName
    $outLog = Join-Path (Split-Path -Parent $script:StatusPath) ("{0}-comfy-start.out.log" -f $taskSlug)
    $errLog = Join-Path (Split-Path -Parent $script:StatusPath) ("{0}-comfy-start.err.log" -f $taskSlug)
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", $comfyServiceScript,
        "-TimeoutSeconds", "45"
    ) -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru

    $deadline = (Get-Date).AddSeconds(90)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 2
        if (Test-ComfyApiAlive) {
            Write-Log "COMFYUI API became alive"
            return
        }
        try {
            if ($proc.HasExited) {
                break
            }
        }
        catch {
            break
        }
    }

    if (Test-ComfyApiAlive) {
        Write-Log "COMFYUI API alive after helper wait"
        return
    }

    try {
        if (-not $proc.HasExited) {
            $proc.Kill()
        }
    }
    catch {}
    $comfyErr = ""
    try {
        if (Test-Path -LiteralPath $errLog) {
            $comfyErr = (Get-Content -LiteralPath $errLog -Raw -ErrorAction SilentlyContinue).Trim()
        }
    }
    catch {}
    if ($comfyErr) {
        throw ("ComfyUI service failed to start: {0}" -f $comfyErr)
    }
    throw "ComfyUI service helper timed out"
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
        "--skip-images",
        "--skip-voice",
        "--skip-sfx",
        "--skip-render"
    )
    if ($script:ImageReference) {
        $args += @(
            "--image-reference", $script:ImageReference,
            "--image-reference-denoise", [string]$script:ImageReferenceDenoise
        )
    }
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
    if ($after.AudioCount -gt $state.AudioCount) {
        Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice progressing" -NodeUpdates @{
            voice = @{ status = "running"; detail = ("Audio progressed {0}/{1}" -f $after.AudioCount, $after.SceneCount) }
        }
    }
    return $false
}

function Invoke-ImageStep {
    $state = Get-SceneState
    $handledCount = $state.ImageCount + $state.ImageSkippedCount
    if ($handledCount -ge $state.SceneCount) {
        Write-Log ("IMAGES complete {0}/{1} (skipped {2})" -f $state.ImageCount, $state.SceneCount, $state.ImageSkippedCount)
        Update-TaskStatus -Overall "running" -CurrentNode "images" -Message "Images complete" -NodeUpdates @{
            images = @{ status = "done"; detail = ("Images ready {0}/{1}, skipped {2}" -f $state.ImageCount, $state.SceneCount, $state.ImageSkippedCount) }
        }
        return $true
    }

    $targetScene = $null
    for ($i = 0; $i -lt $state.Scenes.Count; $i++) {
        $scene = $state.Scenes[$i]
        $validatorStatus = ""
        try { $validatorStatus = [string]$scene.local_image.validator.status } catch {}
        if ($validatorStatus -eq "skipped_after_failed_attempts") {
            continue
        }
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
    $targetSceneData = $state.Scenes[$targetScene - 1]
    $targetImagePath = $null
    if ($targetSceneData.image) {
        $targetImagePath = if ([System.IO.Path]::IsPathRooted([string]$targetSceneData.image)) { [string]$targetSceneData.image } else { Join-Path $script:ProjectRoot ([string]$targetSceneData.image) }
    }
    Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Generating image scene {0}" -f $targetScene) -NodeUpdates @{
        images = @{ status = "running"; detail = ("Current scene {0}, images {1}/{2}, skipped {3}" -f $targetScene, $state.ImageCount, $state.SceneCount, $state.ImageSkippedCount) }
    }

    if ($script:ImageMode -eq "comfy") {
        try {
            Ensure-ComfyService
        }
        catch {
            Write-Log ("IMAGE retry after ComfyUI ensure failed on scene {0}: {1}" -f $targetScene, $_.Exception.Message)
            Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Retrying image scene {0}" -f $targetScene) -NodeUpdates @{
                images = @{ status = "warning"; detail = ("ComfyUI unavailable for scene {0}, will retry" -f $targetScene) }
            }
            return $false
        }
    }

    $imageArgs = @(
        "--storyboard", $script:Storyboard,
        "--aspect-ratio", $script:AspectRatio,
        "--final-width", [string]$script:FinalWidth,
        "--final-height", [string]$script:FinalHeight,
        "--preset", "safe",
        "--start-scene", [string]$targetScene,
        "--end-scene", [string]$targetScene
    )
    if ($script:ImageReference) {
        $imageArgs += @(
            "--reference-image", $script:ImageReference,
            "--reference-denoise", [string]$script:ImageReferenceDenoise
        )
    }
    try {
        Invoke-Step -Label ("image scene {0}" -f $targetScene) -FilePath (Join-Path $script:RepoRoot "scripts\generate_images_comfy_local.py") -Arguments $imageArgs
    }
    catch {
        Write-Log ("IMAGE retry after error on scene {0}: {1}" -f $targetScene, $_.Exception.Message)
        Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Retrying image scene {0}" -f $targetScene) -NodeUpdates @{
            images = @{ status = "warning"; detail = ("Scene {0} failed once, will retry" -f $targetScene) }
        }
        return $false
    }
    if ($targetImagePath -and -not (Test-Path $targetImagePath)) {
        $postState = Get-SceneState
        $postScene = $postState.Scenes[$targetScene - 1]
        $postValidatorStatus = ""
        try { $postValidatorStatus = [string]$postScene.local_image.validator.status } catch {}
        if ($postValidatorStatus -eq "skipped_after_failed_attempts") {
            Write-Log ("IMAGE scene {0} skipped after validator failures" -f $targetScene)
            Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Skipping image scene {0} after failed validation" -f $targetScene) -NodeUpdates @{
                images = @{ status = "warning"; detail = ("Scene {0} skipped after repeated validator failures" -f $targetScene) }
            }
            return $false
        }
        Write-Log ("IMAGE output missing after scene {0}: {1}" -f $targetScene, $targetImagePath)
        Update-TaskStatus -Overall "running" -CurrentNode "images" -Message ("Missing output for image scene {0}" -f $targetScene) -NodeUpdates @{
            images = @{ status = "warning"; detail = ("Scene {0} did not produce an output file, retrying" -f $targetScene) }
        }
        return $false
    }
    Start-Sleep -Seconds 5
    return $false
}

function Invoke-FinalRender {
    Update-TaskStatus -Overall "running" -CurrentNode "render" -Message "Rendering final video" -NodeUpdates @{
        render = @{ status = "running"; detail = "Rendering final mp4" }
    }
    $args = @(
        "--project", $script:ProjectRoot,
        "--format", $script:Format,
        "--image-mode", $script:ImageMode,
        "--run-mode", $script:RunMode,
        "--skip-images",
        "--skip-voice"
    )
    if ($script:StorySource) {
        $args = @("--source", $script:StorySource) + $args
    }
    if ($script:ImageReference) {
        $args += @(
            "--image-reference", $script:ImageReference,
            "--image-reference-denoise", [string]$script:ImageReferenceDenoise
        )
    }
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
$repoVenvPython = Join-Path $script:RepoRoot ".venv\Scripts\python.exe"
if ((-not $PythonExe -or $PythonExe -eq "python") -and (Test-Path -LiteralPath $repoVenvPython)) {
    $PythonExe = $repoVenvPython
}
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
$script:WorkerLockDir = Join-Path $tempRoot "story-task-locks"
$script:WorkerLockPath = Join-Path $script:WorkerLockDir ((Get-Slug $TaskName) + ".lock")

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
if (-not (Acquire-WorkerLock)) {
    try {
        Add-Content -Path $script:LogPath -Value ("[{0}] DUPLICATE worker suppressed for {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $TaskName) -Encoding UTF8
    }
    catch {}
    exit 0
}
Write-Log "JOB START"
Write-Log ("TASK {0}" -f $TaskName)
Enter-RenderMode
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
    $voiceBlocked = $false
    $lastAudioCount = -1
    $voiceStallCount = 0
    $maxVoiceAttempts = 80
    while (-not ($voiceReady -and $imageReady)) {
        if (-not $voiceReady -and -not $script:SkipVoice -and -not $voiceBlocked) {
            $voiceBefore = Get-SceneState
            $voiceAttempt++
            $voiceReady = Invoke-VoiceAttempt -Attempt $voiceAttempt
            $voiceAfter = Get-SceneState
            if ($voiceReady) {
                $voiceStallCount = 0
            }
            else {
                if ($voiceAfter.AudioCount -gt $lastAudioCount) {
                    $lastAudioCount = $voiceAfter.AudioCount
                    $voiceStallCount = 0
                }
                else {
                    $voiceStallCount++
                }
                if ($voiceStallCount -ge 4 -or $voiceAttempt -ge $maxVoiceAttempts) {
                    $voiceBlocked = $true
                    Write-Log ("VOICE stalled after {0} attempts with audio {1}/{2}" -f $voiceAttempt, $voiceAfter.AudioCount, $voiceAfter.SceneCount)
                    Update-TaskStatus -Overall "running" -CurrentNode "voice" -Message "Voice stalled; allowing image pass to continue" -NodeUpdates @{
                        voice = @{ status = "warning"; detail = ("Voice stalled at {0}/{1} after {2} attempts" -f $voiceAfter.AudioCount, $voiceAfter.SceneCount, $voiceAttempt) }
                    }
                }
            }
            Write-QASummary -Stage ("voice-pass-{0}" -f $voiceAttempt)
        }
        if (-not $imageReady) {
            $imageReady = Invoke-ImageStep
            Write-QASummary -Stage "image-step"
        }
        if ($voiceReady -and $imageReady) {
            break
        }
        if ($voiceBlocked -and -not $voiceReady -and $imageReady) {
            break
        }
    }
    $finalSceneState = Get-SceneState
    if (($voiceReady -or $script:SkipVoice) -and ($finalSceneState.ImageCount -ge $finalSceneState.SceneCount)) {
        if (-not (Test-ManualQAPassed)) {
            Block-RenderUntilManualQA
            Write-Log "JOB WAITING FOR MANUAL QA"
            return
        }
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
        $warningMessage = if ($finalSceneState.ImageSkippedCount -gt 0) {
            "Image validation skipped one or more scenes; render blocked"
        }
        elseif (-not $voiceReady -and -not $script:SkipVoice) {
            "Images finished but voice incomplete"
        }
        else {
            "Task finished with partial assets"
        }
        $renderDetail = if ($finalSceneState.ImageSkippedCount -gt 0) {
            ("Render blocked because {0} image scene(s) were skipped by validator" -f $finalSceneState.ImageSkippedCount)
        }
        elseif (-not $voiceReady -and -not $script:SkipVoice) {
            "Render waiting for full audio"
        }
        else {
            "Render blocked because required assets are incomplete"
        }
        Update-TaskStatus -Overall "warning" -CurrentNode "qa" -Message $warningMessage -NodeUpdates @{
            render = @{ status = "blocked"; detail = $renderDetail }
            qa = @{ status = "warning"; detail = "Partial output only" }
        }
        Write-QASummary -Stage "partial-output"
        Write-Log ("JOB PARTIAL: {0}" -f $warningMessage)
    }
}
catch {
    Write-Log ("JOB ERROR: {0}" -f $_.Exception.Message)
    Update-TaskStatus -Overall "failed" -CurrentNode "error" -Message $_.Exception.Message
    throw
}
finally {
    Release-WorkerLock
    Pop-Location
}
