param()

$ErrorActionPreference = "Stop"

$pythonExe = "C:\Users\thanh\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$repoRoot = "E:\ThanhMV\auto-video-generator"
$projectRoot = "E:\ThanhMV\video-projects\phe-tho-tap-01-phan-02-nguoi-dan-ong-khong-dung-day-duoc"
$storyboard = Join-Path $projectRoot "storyboard.json"
$referenceImage = "C:\Users\thanh\Downloads\fb8d05e9-8752-4bc9-912c-85580d64d714.png"
$logPath = "E:\ThanhMV\temp\chapter2_images_only_job.log"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logPath -Value $line -Encoding UTF8
}

function Get-SceneState {
    $data = Get-Content $storyboard -Raw -Encoding UTF8 | ConvertFrom-Json
    $scenes = @($data.scenes)
    $images = 0
    foreach ($scene in $scenes) {
        if ($scene.image) {
            $imagePath = if ([System.IO.Path]::IsPathRooted([string]$scene.image)) { [string]$scene.image } else { Join-Path $projectRoot ([string]$scene.image) }
            if (Test-Path $imagePath) { $images++ }
        }
    }
    [pscustomobject]@{
        SceneCount = $scenes.Count
        ImageCount = $images
        Scenes = $scenes
    }
}

function Invoke-SceneImage {
    param([int]$SceneNumber)
    Write-Log ("START image scene {0}" -f $SceneNumber)
    & $pythonExe `
        (Join-Path $repoRoot "scripts\generate_images_comfy_local.py") `
        --storyboard $storyboard `
        --aspect-ratio 16:9 `
        --final-width 1920 `
        --final-height 1080 `
        --preset balanced `
        --start-scene $SceneNumber `
        --end-scene $SceneNumber `
        --reference-image $referenceImage `
        --reference-denoise 0.28
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) {
        Write-Log ("FAIL image scene {0} exit {1}" -f $SceneNumber, $exitCode)
        throw "Image scene $SceneNumber failed"
    }
    Write-Log ("DONE image scene {0}" -f $SceneNumber)
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $logPath) | Out-Null
Write-Log "JOB START"

Push-Location $repoRoot
try {
    while ($true) {
        $state = Get-SceneState
        if ($state.ImageCount -ge $state.SceneCount) {
            Write-Log ("JOB SUCCESS images {0}/{1}" -f $state.ImageCount, $state.SceneCount)
            break
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
            Write-Log "No target scene found, sleeping 5s"
            Start-Sleep -Seconds 5
            continue
        }

        Invoke-SceneImage -SceneNumber $targetScene
        Start-Sleep -Seconds 8
    }
}
catch {
    Write-Log ("JOB ERROR: {0}" -f $_.Exception.Message)
    throw
}
finally {
    Pop-Location
}
