param(
  [int]$SinceHours = 24,
  [int]$Limit = 300,
  [int]$PreviewChars = 1200,
  [string]$OutputDir = "$PSScriptRoot\reports",
  [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

function Get-OutlookApplication {
  try {
    return [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
  } catch {
    return New-Object -ComObject Outlook.Application
  }
}

function ShortText {
  param([string]$Text, [int]$MaxLength)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $clean = (($Text -replace "\s+", " ").Trim())
  if ($clean.Length -gt $MaxLength) { return $clean.Substring(0, $MaxLength) }
  return $clean
}

function Clean-MailBody {
  param([string]$Text, [int]$MaxLength = 900)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $clean = (($Text -replace "\r", "`n") -replace "\n+", "`n").Trim()
  $splitPatterns = @(
    "`nFrom:",
    "`nSent:",
    "`n________________________________",
    "`nRespectfully,",
    "`nBest regards,",
    "`nThank you and Best Regards,",
    "`nThis communication is for its intended recipient",
    "`n[THIS IS AN AUTOMATED MESSAGE"
  )
  foreach ($pattern in $splitPatterns) {
    $idx = $clean.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase)
    if ($idx -gt 0) {
      $clean = $clean.Substring(0, $idx).Trim()
    }
  }
  $clean = (($clean -replace "\s+", " ").Trim())
  if ($clean.Length -gt $MaxLength) { return $clean.Substring(0, $MaxLength).Trim() + "..." }
  return $clean
}

function Get-Priority {
  param($Messages)
  $hay = (($Messages | ForEach-Object { "$($_.Subject) $($_.BodyPreview)" }) -join " ").ToLowerInvariant()
  if ($hay -match "urgent|high priority|fail|deadline|asap|immediate|by\s+\w+day|before|due") { return "Urgent" }
  if ($hay -match "please help|please update|need to|needs to|required|request|approval|approve|confirm|review|fix|hotfix|fcc|validation|manual") { return "Follow-up" }
  if ($hay -match "jira|otp|xác minh|automated|notification|fy[iy]") { return "FYI" }
  return "Review"
}

function Get-Category {
  param($Messages)
  $hay = (($Messages | ForEach-Object { "$($_.Folder) $($_.Subject) $($_.BodyPreview)" }) -join " ").ToLowerInvariant()
  if ($hay -match "jira|rd0450|atlassian") { return "Jira / Tracker" }
  if ($hay -match "fcc|certification|certificate|csr") { return "Compliance" }
  if ($hay -match "vehicle validation|field test|validation") { return "Validation" }
  if ($hay -match "deadline|full test|test request") { return "Test Request" }
  if ($hay -match "firmware|database|db|component|emmc|pcb|schematic|rspro|parser|api|backend|mode[s]? 5|mode[s]? 6|mode[s]? 8") { return "Engineering Update" }
  if ($hay -match "approval|approve|manual|qsg|artwork|graphic|logo|printing") { return "Approval / Artwork" }
  if ($hay -match "factory visit|schedule|trip|visa") { return "Schedule" }
  return "General"
}

function Get-Action {
  param($Messages, [string]$Priority, [string]$Category)
  $latest = @($Messages | Sort-Object ReceivedTime -Descending)[0]
  $text = "$($latest.Subject) $($latest.BodyPreview)"
  if ($Category -eq "Jira / Tracker") { return "Review only if assigned to you or waiting for your confirmation." }
  if ($Category -eq "Validation" -and $text -match "(?i)fail") { return "Open the validation report, identify owner, and reply with feedback/fix plan." }
  if ($Category -eq "Test Request") { return "Confirm owner, run requested tests, capture logs, and submit results before deadline." }
  if ($Category -eq "Approval / Artwork") { return "Apply latest review comments or confirm approval status, then resend/release when approved." }
  if ($Category -eq "Compliance") { return "Add this to compliance tracking and confirm affected products." }
  if ($Category -eq "Schedule") { return "Confirm people, timing, and blockers such as visa/travel status." }
  if ($Category -eq "Engineering Update") { return "Update the relevant firmware/database/component document or confirm implementation status." }
  if ($Priority -eq "Urgent") { return "Review and respond today." }
  if ($Priority -eq "Follow-up") { return "Check whether your team owns the next step." }
  return "No immediate action unless this is your owner area."
}

function Get-ThreadTitle {
  param($Latest)
  if (-not [string]::IsNullOrWhiteSpace($Latest.ConversationTopic)) { return $Latest.ConversationTopic }
  return $Latest.Subject
}

function Convert-MailItem {
  param($Item, [string]$FolderPath)

  $senderAddress = ""
  $conversationId = ""
  $conversationTopic = ""
  $to = ""
  $cc = ""
  $body = ""

  try { $senderAddress = [string]$Item.SenderEmailAddress } catch {}
  try { $conversationId = [string]$Item.ConversationID } catch {}
  try { $conversationTopic = [string]$Item.ConversationTopic } catch {}
  try { $to = [string]$Item.To } catch {}
  try { $cc = [string]$Item.CC } catch {}
  try { $body = [string]$Item.Body } catch {}

  [pscustomobject]@{
    ReceivedTime      = $Item.ReceivedTime
    Folder            = $FolderPath
    ConversationID    = $conversationId
    ConversationTopic = $conversationTopic
    SenderName        = [string]$Item.SenderName
    SenderEmail       = $senderAddress
    To                = $to
    Cc                = $cc
    Subject           = [string]$Item.Subject
    HasAttachments    = [bool]$Item.Attachments.Count
    BodyPreview       = (ShortText $body $PreviewChars)
  }
}

function Read-MailFolder {
  param($MailFolder, [string]$Filter, $Messages)

  try {
    $items = $MailFolder.Items
    $items.Sort("[ReceivedTime]", $true)
    $restricted = $items.Restrict($Filter)

    foreach ($item in $restricted) {
      if ($Messages.Count -ge $Limit) { break }
      if ($item -and $item.MessageClass -like "IPM.Note*") {
        $Messages.Add((Convert-MailItem $item $MailFolder.FolderPath)) | Out-Null
      }
    }
  } catch {
    # Some Outlook folders do not expose mail items or are unavailable offline.
  }

  foreach ($subFolder in $MailFolder.Folders) {
    if ($Messages.Count -ge $Limit) { break }
    Read-MailFolder $subFolder $Filter $Messages
  }
}

function New-ThreadMarkdown {
  param($Thread)

  $messages = @($Thread.Group | Sort-Object ReceivedTime)
  $latest = @($messages | Sort-Object ReceivedTime -Descending)[0]
  $priority = Get-Priority $messages
  $category = Get-Category $messages
  $action = Get-Action $messages $priority $category
  $title = Get-ThreadTitle $latest
  $folders = @($messages | Select-Object -ExpandProperty Folder -Unique) -join "; "
  $senders = @($messages | ForEach-Object {
    if ($_.SenderEmail) { "$($_.SenderName) <$($_.SenderEmail)>" } else { $_.SenderName }
  } | Select-Object -Unique) -join "; "

  $attachmentMark = if (@($messages | Where-Object { $_.HasAttachments }).Count -gt 0) { "Yes" } else { "No" }
  $latestPreview = Clean-MailBody $latest.BodyPreview 900

  @"
### [$priority] $title

- **Category:** $category
- **Folders:** $folders
- **Latest sender:** $($latest.SenderName) <$($latest.SenderEmail)>
- **Participants:** $senders
- **Latest time:** $($latest.ReceivedTime)
- **Attachments:** $attachmentMark
- **Latest update:** $latestPreview
- **Action:** $action
"@
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$rangeEnd = Get-Date
$rangeStart = $rangeEnd.AddHours(-$SinceHours)
$filter = "[ReceivedTime] >= '$($rangeStart.ToString("g"))' AND [ReceivedTime] < '$($rangeEnd.ToString("g"))'"

$outlook = Get-OutlookApplication
$namespace = $outlook.GetNamespace("MAPI")
$messages = New-Object System.Collections.Generic.List[object]

foreach ($storeRoot in $namespace.Folders) {
  if ($messages.Count -ge $Limit) { break }
  Read-MailFolder $storeRoot $filter $messages
}

$sortedMessages = @($messages | Sort-Object ReceivedTime -Descending)
$today = (Get-Date).ToString("yyyy-MM-dd")
$runTime = (Get-Date).ToString("HH:mm:ss")
$reportPath = Join-Path $OutputDir "mail-report-$today.md"
$jsonPath = Join-Path $OutputDir "mail-report-$today-$($runTime.Replace(':','')).json"

$payload = [pscustomobject]@{
  Source = "Outlook Desktop COM"
  Mailbox = $namespace.CurrentUser.Name
  Scope = "All Outlook folders"
  RangeStart = $rangeStart.ToString("yyyy-MM-dd HH:mm:ss")
  RangeEnd = $rangeEnd.ToString("yyyy-MM-dd HH:mm:ss")
  Count = $sortedMessages.Count
  Messages = $sortedMessages
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $jsonPath -Encoding UTF8

$threads = @($sortedMessages | Group-Object ConversationID | Sort-Object {
  (@($_.Group | Sort-Object ReceivedTime -Descending)[0]).ReceivedTime
} -Descending)

$threadSummaries = @($threads | ForEach-Object {
  $msgs = @($_.Group)
  $latest = @($msgs | Sort-Object ReceivedTime -Descending)[0]
  [pscustomobject]@{
    Title = Get-ThreadTitle $latest
    Priority = Get-Priority $msgs
    Category = Get-Category $msgs
    LatestSender = if ($latest.SenderEmail) { "$($latest.SenderName) <$($latest.SenderEmail)>" } else { $latest.SenderName }
    LatestTime = $latest.ReceivedTime
    Folders = (@($msgs | Select-Object -ExpandProperty Folder -Unique) -join "; ")
    Action = Get-Action $msgs (Get-Priority $msgs) (Get-Category $msgs)
    HasAttachments = @($msgs | Where-Object { $_.HasAttachments }).Count -gt 0
    LatestUpdate = Clean-MailBody $latest.BodyPreview 240
  }
})

$priorityThreads = @($threadSummaries | Where-Object { $_.Priority -in @("Urgent", "Follow-up") } | Select-Object -First 7)
$actionThreads = @($threadSummaries | Where-Object { $_.Priority -in @("Urgent", "Follow-up") } | Select-Object -First 12)
$watchThreads = @($threadSummaries | Where-Object { $_.Priority -eq "Review" } | Select-Object -First 8)
$noiseThreads = @($threadSummaries | Where-Object { $_.Priority -eq "FYI" } | Select-Object -First 8)

$header = @"
# Outlook Mail Report - $today

Mailbox: $($namespace.CurrentUser.Name)  
Report file: $reportPath

"@

if (-not (Test-Path $reportPath)) {
  $header | Set-Content -Path $reportPath -Encoding UTF8
}

@"

## Run $runTime

Range: $($rangeStart.ToString("yyyy-MM-dd HH:mm:ss")) -> $($rangeEnd.ToString("yyyy-MM-dd HH:mm:ss"))  
Total messages: $($sortedMessages.Count)  
Total conversations: $($threads.Count)

## Top Priorities

"@ | Add-Content -Path $reportPath -Encoding UTF8

if ($priorityThreads.Count -eq 0) {
  "- No urgent/follow-up conversations detected in this run." | Add-Content -Path $reportPath -Encoding UTF8
} else {
  $rank = 1
  foreach ($item in $priorityThreads) {
    "$rank. **$($item.Priority) - $($item.Title)**  " | Add-Content -Path $reportPath -Encoding UTF8
    "   Latest: $($item.LatestSender) at $($item.LatestTime). $($item.LatestUpdate)" | Add-Content -Path $reportPath -Encoding UTF8
    $rank++
  }
}

@"

## Action Required

| Priority | Category | Thread | Latest sender | Action |
|---|---|---|---|---|
"@ | Add-Content -Path $reportPath -Encoding UTF8

foreach ($item in $actionThreads) {
  $safeTitle = ($item.Title -replace "\|", "/")
  $safeAction = ($item.Action -replace "\|", "/")
  "| $($item.Priority) | $($item.Category) | $safeTitle | $($item.LatestSender) | $safeAction |" | Add-Content -Path $reportPath -Encoding UTF8
}

## Conversation Briefs

"## Conversation Briefs`n" | Add-Content -Path $reportPath -Encoding UTF8

foreach ($thread in $threads) {
  New-ThreadMarkdown $thread | Add-Content -Path $reportPath -Encoding UTF8
}

@"

## Watchlist

"@ | Add-Content -Path $reportPath -Encoding UTF8

if ($watchThreads.Count -eq 0) {
  "- No medium-priority watchlist threads detected." | Add-Content -Path $reportPath -Encoding UTF8
} else {
  foreach ($item in $watchThreads) {
    "- **$($item.Title)** - $($item.Category), latest from $($item.LatestSender)." | Add-Content -Path $reportPath -Encoding UTF8
  }
}

"`n## Noise / FYI`n" | Add-Content -Path $reportPath -Encoding UTF8

if ($noiseThreads.Count -eq 0) {
  "- No obvious noise/FYI-only threads detected." | Add-Content -Path $reportPath -Encoding UTF8
} else {
  foreach ($item in $noiseThreads) {
    "- **$($item.Title)** - $($item.Category), latest from $($item.LatestSender)." | Add-Content -Path $reportPath -Encoding UTF8
  }
}

Write-Host "Report saved: $reportPath"
Write-Host "Raw JSON saved: $jsonPath"

if ($OpenReport) {
  Start-Process -FilePath $reportPath
}
