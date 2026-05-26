param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,

    [Parameter(Mandatory = $true)]
    [string]$ScriptPath,

    [Parameter(Mandatory = $true)]
    [string]$LogPath,

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$PipelineArgs
)

$ErrorActionPreference = "Stop"

$logDir = Split-Path -Parent $LogPath
if ($logDir) {
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
}

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
}

Write-Log "START background pipeline"
Write-Log ("Python: {0}" -f $PythonExe)
Write-Log ("Script: {0}" -f $ScriptPath)
Write-Log ("Args: {0}" -f ($PipelineArgs -join " "))

try {
    & $PythonExe $ScriptPath @PipelineArgs *>> $LogPath
    $exitCode = $LASTEXITCODE
    Write-Log ("EXIT {0}" -f $exitCode)
    exit $exitCode
}
catch {
    Write-Log ("ERROR {0}" -f $_.Exception.Message)
    throw
}
