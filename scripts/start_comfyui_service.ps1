param(
    [string]$ComfyRoot = "",
    [string]$Url = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot
if (-not $ComfyRoot) {
    $ComfyRoot = Join-Path $workRoot "ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
}
$ComfyRoot = (Resolve-Path $ComfyRoot).Path
$runBat = Join-Path $ComfyRoot "run_nvidia_gpu.bat"
$logDir = Join-Path $workRoot "temp"
$outLog = Join-Path $logDir "comfyui-service-out.log"
$errLog = Join-Path $logDir "comfyui-service-err.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Test-ComfyAlive {
    try {
        $response = Invoke-WebRequest -Uri "$Url/system_stats" -UseBasicParsing -TimeoutSec 3
        return $response.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

if (Test-ComfyAlive) {
    [pscustomobject]@{ status = "alive"; url = $Url; comfy_root = $ComfyRoot } | ConvertTo-Json -Compress
    exit 0
}

$existing = Get-CimInstance Win32_Process | Where-Object {
    ($_.Name -match "cmd|python") -and ($_.CommandLine -like "*ComfyUI*main.py*" -or $_.CommandLine -like "*run_nvidia_gpu.bat*")
}
if (-not $existing) {
    if (-not (Test-Path $runBat)) {
        throw "ComfyUI launcher not found: $runBat"
    }
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "run_nvidia_gpu.bat" -WorkingDirectory $ComfyRoot -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
}

$checks = [Math]::Max(1, [int][Math]::Ceiling($TimeoutSeconds / 5.0))
for ($i = 0; $i -lt $checks; $i++) {
    Start-Sleep -Seconds 5
    if (Test-ComfyAlive) {
        [pscustomobject]@{ status = "started"; url = $Url; comfy_root = $ComfyRoot } | ConvertTo-Json -Compress
        exit 0
    }
}
throw "ComfyUI did not start on $Url within $TimeoutSeconds seconds"
