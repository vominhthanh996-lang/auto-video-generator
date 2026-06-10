param()

$ErrorActionPreference = "Stop"

$pythonExe = "C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$repoRoot = "E:\ThanhMV\auto-video-generator"
$projectRoot = "E:\ThanhMV\video-projects\phe-tho-tap-01-phan-02-nguoi-dan-ong-khong-dung-day-duoc"
$storySource = "E:\ThanhMV\Content truyen\phe-tho-ta-nhat-duoc-ca-the-gioi\tap-01-khu-17-ngoai-thanh\ban-v3-dai-than\phan-02-nguoi-dan-ong-khong-dung-day-duoc.md"
$storyboard = Join-Path $projectRoot "storyboard.json"
$characterBible = Join-Path $projectRoot "character_voice_bible.json"
$referenceImage = "C:\Users\thanh\Downloads\fb8d05e9-8752-4bc9-912c-85580d64d714.png"
$logPath = "E:\ThanhMV\temp\chapter2_work_local_job.log"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

function Invoke-Step {
    param(
        [string]$Label,
        [string]$FilePath,
        [string[]]$Arguments
    )
    Write-Log ("START {0}" -f $Label)
    & $pythonExe $FilePath @Arguments
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Log ("FAIL {0} (exit {1})" -f $Label, $exitCode)
        throw "{0} failed with exit code {1}" -f $Label, $exitCode
    }
    Write-Log ("DONE {0}" -f $Label)
}

function Get-SceneState {
    $data = Get-Content $storyboard -Raw -Encoding UTF8 | ConvertFrom-Json
    $scenes = @($data.scenes)
    $images = 0
    $audio = 0
    foreach ($scene in $scenes) {
        if ($scene.image) {
            $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $projectRoot ([string]$scene.image) }
            if (Test-Path $imagePath) { $images++ }
        }
        if ($scene.audio) {
            $audioPath = if ([System.IO.Path]::IsPathRooted([string]$scene.audio)) { [string]$scene.audio } else { Join-Path $projectRoot ([string]$scene.audio) }
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

function Invoke-VoiceUntilComplete {
    $maxAttempts = 12
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $state = Get-SceneState
        if ($state.AudioCount -ge $state.SceneCount) {
            Write-Log ("VOICE complete {0}/{1}" -f $state.AudioCount, $state.SceneCount)
            return $true
        }
        Write-Log ("VOICE attempt {0}: current {1}/{2}" -f $attempt, $state.AudioCount, $state.SceneCount)
        try {
            Invoke-Step `
                -Label ("voice attempt {0}" -f $attempt) `
                -FilePath (Join-Path $repoRoot "scripts\generate_voice_edge.py") `
                -Arguments @(
                    "--storyboard", $storyboard,
                    "--voice", "vi-female",
                    "--voice-style", "wasteland-dark",
                    "--character-bible", $characterBible
                )
        }
        catch {
            Write-Log ("VOICE retry after error: {0}" -f $_.Exception.Message)
            Start-Sleep -Seconds 20
        }
    }
    $state = Get-SceneState
    Write-Log ("VOICE incomplete after retries: {0}/{1}" -f $state.AudioCount, $state.SceneCount)
    return $false
}

function Invoke-ImagesUntilComplete {
    while ($true) {
        $state = Get-SceneState
        if ($state.ImageCount -ge $state.SceneCount) {
            Write-Log ("IMAGES complete {0}/{1}" -f $state.ImageCount, $state.SceneCount)
            return
        }

        $targetScene = $null
        for ($i = 0; $i -lt $state.Scenes.Count; $i++) {
            $scene = $state.Scenes[$i]
            $imagePath = $null
            if ($scene.image) {
                $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $projectRoot ([string]$scene.image) }
            }
            if (-not $imagePath -or -not (Test-Path $imagePath)) {
                $targetScene = $i + 1
                break
            }
        }

        if (-not $targetScene) {
            Write-Log "No missing image scene found even though counts are incomplete."
            Start-Sleep -Seconds 5
            continue
        }

        Write-Log ("IMAGE next scene {0}" -f $targetScene)
        Invoke-Step `
            -Label ("image scene {0}" -f $targetScene) `
            -FilePath (Join-Path $repoRoot "scripts\generate_images_comfy_local.py") `
            -Arguments @(
                "--storyboard", $storyboard,
                "--aspect-ratio", "16:9",
                "--final-width", "1920",
                "--final-height", "1080",
                "--preset", "balanced",
                "--start-scene", [string]$targetScene,
                "--end-scene", [string]$targetScene,
                "--reference-image", $referenceImage,
                "--reference-denoise", "0.28"
            )
        Start-Sleep -Seconds 8
    }
}

function Invoke-FinalRender {
    Invoke-Step `
        -Label "final pipeline render" `
        -FilePath (Join-Path $repoRoot "scripts\run_story_pipeline.py") `
        -Arguments @(
            "--source", $storySource,
            "--project", $projectRoot,
            "--format", "youtube",
            "--image-mode", "comfy",
            "--run-mode", "work",
            "--image-reference", $referenceImage,
            "--image-reference-denoise", "0.28",
            "--skip-images",
            "--skip-voice"
        )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null
Write-Log "JOB START"

Push-Location $repoRoot
try {
    $voiceReady = Invoke-VoiceUntilComplete
    Invoke-ImagesUntilComplete
    if (-not $voiceReady) {
        Write-Log "Retrying voice after image generation"
        $voiceReady = Invoke-VoiceUntilComplete
    }
    if ($voiceReady) {
        Invoke-FinalRender
        Write-Log "JOB SUCCESS"
    }
    else {
        Write-Log "JOB PARTIAL: images finished, voice still incomplete, render skipped"
    }
}
catch {
    Write-Log ("JOB ERROR: {0}" -f $_.Exception.Message)
    throw
}
finally {
    Pop-Location
}
