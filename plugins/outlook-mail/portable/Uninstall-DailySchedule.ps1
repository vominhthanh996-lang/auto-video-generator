param(
  [string]$TaskPrefix = "Outlook Mail Report"
)

Get-ScheduledTask | Where-Object { $_.TaskName -like "$TaskPrefix*" } | ForEach-Object {
  Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
  Write-Host "Removed scheduled task: $($_.TaskName)"
}
