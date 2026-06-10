param(
    [string]$ComfyRoot = "",
    [string]$Url = "http://127.0.0.1:8188",
    [int]$TimeoutSeconds = 180
)

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot
$workRoot = Split-Path -Parent $repoRoot

function Resolve-ComfyRoot {
    param(
        [string]$RequestedRoot,
        [string]$RepoRoot
    )
    $candidates = @()
    if ($RequestedRoot) {
        $candidates += $RequestedRoot
    }
    if ($env:COMFY_ROOT) {
        $candidates += $env:COMFY_ROOT
    }
    if ($env:AUTO_VIDEO_COMFY_ROOT) {
        $candidates += $env:AUTO_VIDEO_COMFY_ROOT
    }
    $candidates += @(
        (Join-Path $workRoot "tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"),
        (Join-Path $workRoot "ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"),
        "D:\ThanhMV\tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable",
        "E:\ThanhMV\tools\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable"
    )
    foreach ($candidate in $candidates) {
        if (-not $candidate) {
            continue
        }
        try {
            $resolved = (Resolve-Path $candidate -ErrorAction Stop).Path
            if (Test-Path (Join-Path $resolved "ComfyUI\main.py")) {
                return $resolved
            }
        }
        catch {}
    }
    throw "ComfyUI root not found. Set COMFY_ROOT or pass -ComfyRoot explicitly."
}

if (-not $ComfyRoot) {
    $ComfyRoot = ""
}
$ComfyRoot = Resolve-ComfyRoot -RequestedRoot $ComfyRoot -RepoRoot $repoRoot
$pythonExe = Join-Path $ComfyRoot "python_embeded\python.exe"
$mainPy = Join-Path $ComfyRoot "ComfyUI\main.py"
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
    if (-not (Test-Path $pythonExe) -or -not (Test-Path $mainPy)) {
        throw "ComfyUI embedded python or main.py not found under: $ComfyRoot"
    }
    Start-Process -FilePath $pythonExe -ArgumentList @(
        "-s",
        $mainPy,
        "--windows-standalone-build",
        "--listen", "127.0.0.1",
        "--port", "8188",
        "--lowvram"
    ) -WorkingDirectory (Join-Path $ComfyRoot "ComfyUI") -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog
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
