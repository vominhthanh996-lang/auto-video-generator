param(
    [string]$PrimaryCheckpoint = "",
    [string]$SecondaryCheckpoint = "",
    [double]$PrimaryWeight = 0.70,
    [double]$SecondaryWeight = 0.30,
    [string]$OutputCheckpoint = ""
)

$ErrorActionPreference = "Stop"

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot

function Resolve-ComfyRoot {
    $candidates = @(
        (Join-Path $workRoot "tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"),
        (Join-Path $workRoot "ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"),
        (Join-Path $workRoot "tools\ComfyUI"),
        (Join-Path $workRoot "ComfyUI"),
        "D:\ThanhMV\tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable",
        "E:\ThanhMV\tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
    )
    foreach ($candidate in $candidates) {
        if (-not $candidate) { continue }
        try {
            $resolved = (Resolve-Path $candidate -ErrorAction Stop).Path
            if (Test-Path (Join-Path $resolved "ComfyUI\main.py")) {
                return $resolved
            }
        }
        catch {}
    }
    throw "Unable to locate ComfyUI portable root."
}

$comfyRoot = Resolve-ComfyRoot
$defaultCheckpointDir = Join-Path $comfyRoot "ComfyUI\models\checkpoints"
$comfyPython = Join-Path $comfyRoot "python_embeded\python.exe"

if (-not $PrimaryCheckpoint) {
    $PrimaryCheckpoint = Join-Path $defaultCheckpointDir "dreamshaper_8.safetensors"
}
if (-not $SecondaryCheckpoint) {
    $SecondaryCheckpoint = Join-Path $defaultCheckpointDir "Realistic_Vision_V6.0_NV_B1.safetensors"
}
if (-not $OutputCheckpoint) {
    $OutputCheckpoint = Join-Path $defaultCheckpointDir "dreamsafe_rv6_ytsafe_mix.safetensors"
}

& $comfyPython `
    (Join-Path $scriptRoot "merge_sd15_checkpoints.py") `
    --primary $PrimaryCheckpoint `
    --secondary $SecondaryCheckpoint `
    --primary-weight ([string]$PrimaryWeight) `
    --secondary-weight ([string]$SecondaryWeight) `
    --output $OutputCheckpoint
