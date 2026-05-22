param(
  [int]$SinceHours = 24,
  [string]$OutputDir = "$PSScriptRoot\reports",
  [switch]$UseAI
)

$ErrorActionPreference = "Stop"
$logDir = Join-Path $OutputDir "logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ("scheduled-" + (Get-Date).ToString("yyyy-MM-dd") + ".log")

try {
  $guiScript = Join-Path $PSScriptRoot "OutlookMailReporterGUI.ps1"
  $content = Get-Content $guiScript -Raw
  $prefix = $content.Substring(0, $content.IndexOf('$form = New-Object Windows.Forms.Form'))
  Invoke-Expression $prefix

  $key = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
  if ($UseAI -and [string]::IsNullOrWhiteSpace($key)) {
    throw "AI mode requested but OPENAI_API_KEY is missing."
  }

  $result = Run-Report -UseAI:$UseAI -ApiKey $key -SinceHours $SinceHours -OutputDir $OutputDir
  "[$(Get-Date)] OK Markdown=$($result.Markdown) Excel=$($result.Excel) Json=$($result.Json)" | Add-Content -Path $log -Encoding UTF8
} catch {
  $message = "Outlook Mail Reporter failed:`r`n`r`n$($_.Exception.Message)`r`n`r`nCommon fixes:`r`n- Open Outlook Desktop and make sure the mailbox is signed in.`r`n- If using AI mode, save OPENAI_API_KEY in the UI.`r`n- Make sure this folder still exists:`r`n$PSScriptRoot`r`n`r`nLog:`r`n$log"
  "[$(Get-Date)] ERROR $($_.Exception.Message)" | Add-Content -Path $log -Encoding UTF8
  try {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($message, "Outlook Mail Reporter Error", "OK", "Error") | Out-Null
  } catch {}
  throw
}
