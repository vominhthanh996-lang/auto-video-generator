param(
  [switch]$Scheduled,
  [switch]$UseAI,
  [int]$SinceHours = 24,
  [string]$OutputDir = "$PSScriptRoot\reports"
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$ErrorActionPreference = "Stop"

function Get-OutlookApplication {
  try { return [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application") }
  catch { return New-Object -ComObject Outlook.Application }
}

function Clean-Text {
  param([string]$Text, [int]$MaxLength = 900)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $clean = (($Text -replace "`r", "`n") -replace "`n+", "`n").Trim()
  foreach ($pattern in @("`nFrom:", "`nSent:", "`n________________________________", "`nRespectfully,", "`nBest regards,", "`nThis communication is for its intended recipient", "`n[THIS IS AN AUTOMATED MESSAGE")) {
    $idx = $clean.IndexOf($pattern, [System.StringComparison]::OrdinalIgnoreCase)
    if ($idx -gt 0) { $clean = $clean.Substring(0, $idx).Trim() }
  }
  $clean = (($clean -replace "\s+", " ").Trim())
  if ($clean.Length -gt $MaxLength) { return $clean.Substring(0, $MaxLength).Trim() + "..." }
  return $clean
}

function Get-LeadMessage {
  param([string]$Text, [int]$MaxLength = 650)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $clean = (($Text -replace "`r", "`n") -replace "`n+", "`n").Trim()
  $idx = $clean.IndexOf("`nFrom:", [StringComparison]::OrdinalIgnoreCase)
  if ($idx -gt 0) { $clean = $clean.Substring(0, $idx) }
  foreach ($pattern in @("`nRespectfully,", "`nBest regards,", "`nThank you and Best Regards,", "`nThis communication is for its intended recipient", "`n[THIS IS AN AUTOMATED MESSAGE")) {
    $p = $clean.IndexOf($pattern, [StringComparison]::OrdinalIgnoreCase)
    if ($p -gt 0) { $clean = $clean.Substring(0, $p) }
  }
  $clean = (($clean -replace "\s+", " ").Trim())
  if ($clean.Length -gt $MaxLength) { return $clean.Substring(0, $MaxLength).Trim() + "..." }
  return $clean
}

function Get-QuotedStory {
  param([string]$Text, [int]$MaxItems = 4)
  $items = New-Object System.Collections.Generic.List[string]
  if ([string]::IsNullOrWhiteSpace($Text)) { return @() }
  $normalized = (($Text -replace "`r", "`n") -replace "`n+", "`n")
  $matches = [regex]::Matches($normalized, "(?ims)\nFrom:\s*(?<from>.+?)\nSent:\s*(?<sent>.+?)(?:\nTo:\s*(?<to>.*?))?(?:\nCc:\s*(?<cc>.*?))?\nSubject:\s*(?<subject>.+?)(?<body>.*?)(?=\nFrom:\s|\z)")
  foreach ($m in $matches) {
    if ($items.Count -ge $MaxItems) { break }
    $from = (($m.Groups["from"].Value -replace "\s+", " ").Trim())
    $subject = (($m.Groups["subject"].Value -replace "\s+", " ").Trim())
    $body = Get-LeadMessage $m.Groups["body"].Value 220
    if ($from -or $subject) {
      $line = "$from"
      if ($subject) { $line += " - $subject" }
      if ($body) { $line += ": $body" }
      $items.Add($line) | Out-Null
    }
  }
  return @($items)
}

function Read-OutlookMessages {
  param([int]$SinceHours, [int]$Limit, [int]$PreviewChars)

  $rangeEnd = Get-Date
  $rangeStart = $rangeEnd.AddHours(-$SinceHours)
  $filter = "[ReceivedTime] >= '$($rangeStart.ToString("g"))' AND [ReceivedTime] < '$($rangeEnd.ToString("g"))'"
  $messages = New-Object System.Collections.Generic.List[object]

  function Convert-Item {
    param($Item, [string]$FolderPath)
    $body = ""; $sender = ""; $cid = ""; $topic = ""; $to = ""; $cc = ""
    try { $body = [string]$Item.Body } catch {}
    try { $sender = [string]$Item.SenderEmailAddress } catch {}
    try { $cid = [string]$Item.ConversationID } catch {}
    try { $topic = [string]$Item.ConversationTopic } catch {}
    try { $to = [string]$Item.To } catch {}
    try { $cc = [string]$Item.CC } catch {}
    [pscustomobject]@{
      ReceivedTime = $Item.ReceivedTime
      Folder = $FolderPath
      ConversationID = $cid
      ConversationTopic = $topic
      SenderName = [string]$Item.SenderName
      SenderEmail = $sender
      To = $to
      Cc = $cc
      Subject = [string]$Item.Subject
      HasAttachments = [bool]$Item.Attachments.Count
      BodyPreview = (Clean-Text $body $PreviewChars)
      LeadMessage = (Get-LeadMessage $body 900)
      QuotedStory = (@(Get-QuotedStory $body 4) -join " || ")
    }
  }

  function Scan-Folder {
    param($Folder)
    if ($messages.Count -ge $Limit) { return }
    try {
      $items = $Folder.Items
      $items.Sort("[ReceivedTime]", $true)
      $restricted = $items.Restrict($filter)
      foreach ($item in $restricted) {
        if ($messages.Count -ge $Limit) { break }
        if ($item -and $item.MessageClass -like "IPM.Note*") {
          $messages.Add((Convert-Item $item $Folder.FolderPath)) | Out-Null
        }
      }
    } catch {}
    foreach ($sub in $Folder.Folders) {
      if ($messages.Count -ge $Limit) { break }
      Scan-Folder $sub
    }
  }

  $outlook = Get-OutlookApplication
  $namespace = $outlook.GetNamespace("MAPI")
  foreach ($root in $namespace.Folders) {
    if ($messages.Count -ge $Limit) { break }
    Scan-Folder $root
  }

  [pscustomobject]@{
    Mailbox = $namespace.CurrentUser.Name
    RangeStart = $rangeStart
    RangeEnd = $rangeEnd
    Messages = @($messages | Sort-Object ReceivedTime -Descending)
  }
}

function Get-Priority {
  param($Messages)
  $hay = (($Messages | ForEach-Object { "$($_.Subject) $($_.BodyPreview)" }) -join " ").ToLowerInvariant()
  if ($hay -match "urgent|high priority|fail|deadline|asap|immediate|before|due") { return "Urgent" }
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
  if ($Category -eq "Approval / Artwork") { return "Apply review comments or confirm approval status, then resend/release when approved." }
  if ($Category -eq "Compliance") { return "Add this to compliance tracking and confirm affected products." }
  if ($Category -eq "Schedule") { return "Confirm people, timing, and blockers such as visa/travel status." }
  if ($Category -eq "Engineering Update") { return "Update the relevant firmware/database/component document or confirm implementation status." }
  if ($Priority -eq "Urgent") { return "Review and respond today." }
  if ($Priority -eq "Follow-up") { return "Check whether your team owns the next step." }
  return "No immediate action unless this is your owner area."
}

function Get-ImpactScore {
  param($Messages, [string]$Priority, [string]$Category)
  $score = 0
  if ($Priority -eq "Urgent") { $score += 40 }
  elseif ($Priority -eq "Follow-up") { $score += 25 }
  elseif ($Priority -eq "Review") { $score += 10 }
  if ($Category -in @("Validation","Test Request","Compliance")) { $score += 25 }
  elseif ($Category -in @("Engineering Update","Approval / Artwork")) { $score += 15 }
  if (@($Messages | Where-Object { $_.HasAttachments }).Count -gt 0) { $score += 5 }
  $hay = (($Messages | ForEach-Object { "$($_.Subject) $($_.BodyPreview)" }) -join " ").ToLowerInvariant()
  if ($hay -match "fail|deadline|high priority|immediate|hotfix|customer") { $score += 20 }
  if ($score -gt 100) { $score = 100 }
  return $score
}

function Get-StoryConclusion {
  param($Messages, [string]$Category)
  $latest = @($Messages | Sort-Object ReceivedTime -Descending)[0]
  $text = "$($latest.Subject) $($latest.LeadMessage) $($latest.BodyPreview)"
  if ($Category -eq "Validation" -and $text -match "(?i)fail") { return "Validation failed; owner should open the report and reply with feedback or a fix plan." }
  if ($Category -eq "Test Request") { return "This is a test request with timing pressure; confirm owner, capture logs, and run the requested test." }
  if ($Category -eq "Compliance") { return "This is a compliance decision or reminder; add it to tracking and confirm affected products." }
  if ($Category -eq "Approval / Artwork") { return "This thread is in review or approval; handle the latest feedback before release or next step." }
  if ($Category -eq "Engineering Update") { return "There is a technical change or direction; update the related firmware, database, component file, or document." }
  if ($Category -eq "Schedule") { return "Schedule is not fully locked; confirm people, dates, travel status, and blockers." }
  if ($Category -eq "Jira / Tracker") { return "Tracker notification; review only if assigned to you or waiting for your confirmation." }
  return "No clear decision detected; review if this thread belongs to your owner area."
}

function Build-ThreadSummaries {
  param($Messages)
  $threads = @($Messages | Group-Object ConversationID | Sort-Object { (@($_.Group | Sort-Object ReceivedTime -Descending)[0]).ReceivedTime } -Descending)
  @($threads | ForEach-Object {
    $msgs = @($_.Group)
    $latest = @($msgs | Sort-Object ReceivedTime -Descending)[0]
    $priority = Get-Priority $msgs
    $category = Get-Category $msgs
    $title = if ($latest.ConversationTopic) { $latest.ConversationTopic } else { $latest.Subject }
    [pscustomobject]@{
      Title = $title
      Priority = $priority
      Category = $category
      LatestSender = "$($latest.SenderName) <$($latest.SenderEmail)>"
      LatestTime = $latest.ReceivedTime
      Folders = (@($msgs | Select-Object -ExpandProperty Folder -Unique) -join "; ")
      Participants = (@($msgs | ForEach-Object { "$($_.SenderName) <$($_.SenderEmail)>" } | Select-Object -Unique) -join "; ")
      Attachments = (@($msgs | Where-Object { $_.HasAttachments }).Count -gt 0)
      LatestUpdate = (Clean-Text $latest.BodyPreview 800)
      Action = Get-Action $msgs $priority $category
      Score = Get-ImpactScore $msgs $priority $category
      Story = (Get-LeadMessage $latest.LeadMessage 700)
      History = $latest.QuotedStory
      Conclusion = Get-StoryConclusion $msgs $category
    }
  })
}

function New-OfflineReport {
  param($Data, $Threads, [string]$ReportPath)
  $priorityThreads = @($Threads | Where-Object { $_.Priority -in @("Urgent", "Follow-up") } | Sort-Object Score,LatestTime -Descending | Select-Object -First 8)
  $actions = @($Threads | Where-Object { $_.Priority -in @("Urgent", "Follow-up") } | Sort-Object Score,LatestTime -Descending | Select-Object -First 14)
  $watch = @($Threads | Where-Object { $_.Priority -eq "Review" } | Select-Object -First 8)
  $noise = @($Threads | Where-Object { $_.Priority -eq "FYI" } | Select-Object -First 8)
  $runTime = (Get-Date).ToString("HH:mm:ss")

  $lines = New-Object System.Collections.Generic.List[string]
  $lines.Add("# Outlook Mail Report - $((Get-Date).ToString('yyyy-MM-dd'))")
  $lines.Add("")
  $lines.Add("**Mailbox:** $($Data.Mailbox)  ")
  $lines.Add("**Range:** $($Data.RangeStart.ToString('yyyy-MM-dd HH:mm')) -> $($Data.RangeEnd.ToString('yyyy-MM-dd HH:mm'))  ")
  $lines.Add("**Run:** $runTime  ")
  $lines.Add("**Messages / Conversations:** $($Data.Messages.Count) / $($Threads.Count)")
  $lines.Add("")
  $lines.Add("## Top Priorities")
  $rank = 1
  foreach ($item in $priorityThreads) {
    $lines.Add("$rank. **$($item.Priority) - $($item.Title)**  ")
    $lines.Add("   Score $($item.Score)/100. Latest: $($item.LatestSender) at $($item.LatestTime). $($item.Conclusion)")
    $rank++
  }
  if ($rank -eq 1) { $lines.Add("- No urgent/follow-up conversations detected.") }
  $lines.Add("")
  $lines.Add("## Action Required")
  $lines.Add("")
  $lines.Add("| Score | Priority | Category | Thread | Latest sender | Action |")
  $lines.Add("|---|---|---|---|---|---|")
  foreach ($item in $actions) {
    $lines.Add("| $($item.Score) | $($item.Priority) | $($item.Category) | $(($item.Title -replace '\|','/')) | $($item.LatestSender) | $(($item.Action -replace '\|','/')) |")
  }
  $lines.Add("")
  $lines.Add("## Conversation Briefs")
  foreach ($item in $Threads) {
    $lines.Add("")
    $lines.Add("### [$($item.Priority)] $($item.Title)")
    $lines.Add("")
    $lines.Add("- **Category:** $($item.Category)")
    $lines.Add("- **Folders:** $($item.Folders)")
    $lines.Add("- **Latest sender:** $($item.LatestSender)")
    $lines.Add("- **Participants:** $($item.Participants)")
    $lines.Add("- **Latest time:** $($item.LatestTime)")
    $lines.Add("- **Attachments:** $($item.Attachments)")
    $lines.Add("- **Story:** $($item.Story)")
    if (-not [string]::IsNullOrWhiteSpace($item.History)) {
      $lines.Add("- **Earlier context:**")
      foreach ($h in ($item.History -split " \|\| ")) {
        if (-not [string]::IsNullOrWhiteSpace($h)) { $lines.Add("  - $h") }
      }
    }
    $lines.Add("- **Conclusion:** $($item.Conclusion)")
    $lines.Add("- **Action:** $($item.Action)")
  }
  $lines.Add("")
  $lines.Add("## Watchlist")
  foreach ($item in $watch) { $lines.Add("- **$($item.Title)** - $($item.Category), latest from $($item.LatestSender).") }
  if ($watch.Count -eq 0) { $lines.Add("- No medium-priority watchlist threads detected.") }
  $lines.Add("")
  $lines.Add("## Noise / FYI")
  foreach ($item in $noise) { $lines.Add("- **$($item.Title)** - $($item.Category), latest from $($item.LatestSender).") }
  if ($noise.Count -eq 0) { $lines.Add("- No obvious noise/FYI-only threads detected.") }
  $lines | Set-Content -Path $ReportPath -Encoding UTF8
}

function New-AIReport {
  param($Data, [string]$ApiKey, [string]$ReportPath)
  $model = if ($env:OPENAI_MODEL) { $env:OPENAI_MODEL } else { "gpt-4.1-mini" }
  $compact = [pscustomobject]@{
    mailbox = $Data.Mailbox
    rangeStart = $Data.RangeStart.ToString("yyyy-MM-dd HH:mm")
    rangeEnd = $Data.RangeEnd.ToString("yyyy-MM-dd HH:mm")
    messages = @($Data.Messages | Select-Object ReceivedTime,Folder,ConversationID,ConversationTopic,SenderName,SenderEmail,To,Cc,Subject,HasAttachments,BodyPreview)
  } | ConvertTo-Json -Depth 6

  $prompt = @"
You are writing a professional Vietnamese daily Outlook mail report for an engineering manager.
Group by conversation/thread. Do not list raw email one by one unless needed.
Sections: Top Priorities, Action Required table, Conversation Briefs, Watchlist, Noise/FYI.
For each thread include folder, latest sender, participants, context/story, latest update, conclusion, action needed.
Make it concise but enough that the reader does not need to open Outlook.

MAIL_JSON:
$compact
"@

  $body = @{
    model = $model
    messages = @(
      @{ role = "system"; content = "You create clear professional Vietnamese operational reports." },
      @{ role = "user"; content = $prompt }
    )
    temperature = 0.2
  } | ConvertTo-Json -Depth 8

  try {
    $req = [Net.HttpWebRequest]::Create("https://api.openai.com/v1/chat/completions")
    $req.Method = "POST"
    $req.Timeout = 120000
    $req.ContentType = "application/json"
    $req.Headers.Add("Authorization", "Bearer $ApiKey")
    $bytes = [Text.Encoding]::UTF8.GetBytes($body)
    $req.ContentLength = $bytes.Length
    $stream = $req.GetRequestStream()
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Close()
    $httpResp = $req.GetResponse()
    $reader = New-Object IO.StreamReader($httpResp.GetResponseStream())
    $raw = $reader.ReadToEnd()
    $reader.Close()
    $resp = $raw | ConvertFrom-Json
  } catch {
    $detail = $_.Exception.Message
    try {
      if ($_.Exception.Response) {
        $reader = New-Object IO.StreamReader($_.Exception.Response.GetResponseStream())
        $detail = $reader.ReadToEnd()
        $reader.Close()
      }
    } catch {}
    throw "OpenAI API error using model '$model': $detail"
  }
  $resp.choices[0].message.content | Set-Content -Path $ReportPath -Encoding UTF8
}

function Export-ExcelReport {
  param($Data, $Threads, [string]$XlsxPath)

  Add-Type -AssemblyName System.IO.Compression.FileSystem

  function XmlEscape([object]$Value) {
    if ($null -eq $Value) { return "" }
    return [Security.SecurityElement]::Escape([string]$Value)
  }

  function ColName([int]$Index) {
    $name = ""
    while ($Index -gt 0) {
      $Index--
      $name = [char](65 + ($Index % 26)) + $name
      $Index = [math]::Floor($Index / 26)
    }
    return $name
  }

  function SheetXml($Rows) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="18"/><cols><col min="1" max="1" width="22" customWidth="1"/><col min="2" max="2" width="80" customWidth="1"/><col min="3" max="20" width="24" customWidth="1"/></cols><sheetData>')
    for ($r = 0; $r -lt $Rows.Count; $r++) {
      $rowNum = $r + 1
      [void]$sb.Append("<row r=`"$rowNum`">")
      $cells = @($Rows[$r])
      for ($c = 0; $c -lt $cells.Count; $c++) {
        $ref = "$(ColName ($c + 1))$rowNum"
        $value = XmlEscape $cells[$c]
        [void]$sb.Append("<c r=`"$ref`" t=`"inlineStr`"><is><t>$value</t></is></c>")
      }
      [void]$sb.Append("</row>")
    }
    [void]$sb.Append("</sheetData></worksheet>")
    return $sb.ToString()
  }

  function StorySheetXml($Rows) {
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.Append('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetFormatPr defaultRowHeight="18"/><cols><col min="1" max="1" width="18" customWidth="1"/><col min="2" max="2" width="120" customWidth="1"/></cols><sheetData>')
    for ($r = 0; $r -lt $Rows.Count; $r++) {
      $rowNum = $r + 1
      [void]$sb.Append("<row r=`"$rowNum`">")
      $cells = @($Rows[$r])
      for ($c = 0; $c -lt $cells.Count; $c++) {
        $ref = "$(ColName ($c + 1))$rowNum"
        $value = XmlEscape $cells[$c]
        [void]$sb.Append("<c r=`"$ref`" t=`"inlineStr`"><is><t xml:space=`"preserve`">$value</t></is></c>")
      }
      [void]$sb.Append("</row>")
    }
    [void]$sb.Append("</sheetData></worksheet>")
    return $sb.ToString()
  }

  function WriteUtf8([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content, [Text.UTF8Encoding]::new($false))
  }

  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("OutlookMailReporterXlsx_" + [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Force -Path $tmp | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $tmp "_rels") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $tmp "xl\_rels") | Out-Null
  New-Item -ItemType Directory -Force -Path (Join-Path $tmp "xl\worksheets") | Out-Null

  @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
'@ | ForEach-Object { WriteUtf8 (Join-Path $tmp "[Content_Types].xml") $_ }

  @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
'@ | ForEach-Object { WriteUtf8 (Join-Path $tmp "_rels\.rels") $_ }

  @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Summary" sheetId="1" r:id="rId1"/>
    <sheet name="Actions" sheetId="2" r:id="rId2"/>
    <sheet name="Story Report" sheetId="3" r:id="rId3"/>
    <sheet name="Messages" sheetId="4" r:id="rId4"/>
  </sheets>
</workbook>
'@ | ForEach-Object { WriteUtf8 (Join-Path $tmp "xl\workbook.xml") $_ }

  @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/>
</Relationships>
'@ | ForEach-Object { WriteUtf8 (Join-Path $tmp "xl\_rels\workbook.xml.rels") $_ }

  $summaryRows = @(
    @("Mailbox", $Data.Mailbox),
    @("Range", "$($Data.RangeStart) -> $($Data.RangeEnd)"),
    @("Messages", $Data.Messages.Count),
    @("Conversations", $Threads.Count)
  )
  $actionRows = @(,@("Score","Priority","Category","Latest time","Latest sender","Title","Conclusion","Action"))
  foreach ($t in @($Threads | Sort-Object Score,LatestTime -Descending)) {
    $actionRows += ,@($t.Score,$t.Priority,$t.Category,[string]$t.LatestTime,$t.LatestSender,$t.Title,$t.Conclusion,$t.Action)
  }

  $storyRows = @(,@("Field","Value"))
  $index = 1
  foreach ($t in @($Threads | Sort-Object Score,LatestTime -Descending)) {
    $storyRows += ,@("Thread $index", $t.Title)
    $storyRows += ,@("Score / Priority", "$($t.Score)/100 - $($t.Priority) - $($t.Category)")
    $storyRows += ,@("Latest", "$($t.LatestTime) - $($t.LatestSender)")
    $storyRows += ,@("Folders", $t.Folders)
    $storyRows += ,@("Story", $t.Story)
    $storyRows += ,@("Earlier context", $t.History)
    $storyRows += ,@("Conclusion", $t.Conclusion)
    $storyRows += ,@("Action", $t.Action)
    $storyRows += ,@("", "")
    $index++
  }
  $messageRows = @(,@("ReceivedTime","Folder","ConversationTopic","SenderName","SenderEmail","Subject","HasAttachments","BodyPreview"))
  foreach ($m in $Data.Messages) {
    $messageRows += ,@([string]$m.ReceivedTime,$m.Folder,$m.ConversationTopic,$m.SenderName,$m.SenderEmail,$m.Subject,[string]$m.HasAttachments,$m.BodyPreview)
  }

  WriteUtf8 (Join-Path $tmp "xl\worksheets\sheet1.xml") (SheetXml $summaryRows)
  WriteUtf8 (Join-Path $tmp "xl\worksheets\sheet2.xml") (SheetXml $actionRows)
  WriteUtf8 (Join-Path $tmp "xl\worksheets\sheet3.xml") (StorySheetXml $storyRows)
  WriteUtf8 (Join-Path $tmp "xl\worksheets\sheet4.xml") (SheetXml $messageRows)

  if (Test-Path $XlsxPath) { Remove-Item -LiteralPath $XlsxPath -Force }
  [System.IO.Compression.ZipFile]::CreateFromDirectory($tmp, $XlsxPath)
  Remove-Item -LiteralPath $tmp -Recurse -Force
  return "Excel saved: $XlsxPath"
}

function Install-ReportSchedule {
  param([string]$InstallDir, [string]$OutputDir, [int]$SinceHours, [bool]$UseAI, [string[]]$Times)
  $runner = Join-Path $InstallDir "OutlookMailReporterGUI.ps1"
  if (-not (Test-Path $runner)) { throw "Cannot find OutlookMailReporterGUI.ps1 in $InstallDir" }
  foreach ($timeText in $Times) {
    $taskName = "Outlook Mail Reporter $($timeText.Replace(':',''))"
    $modeArg = if ($UseAI) { "-UseAI" } else { "" }
    $arg = "-ExecutionPolicy Bypass -File `"$runner`" -Scheduled -SinceHours $SinceHours -OutputDir `"$OutputDir`" $modeArg"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg
    $trigger = @(
      (New-ScheduledTaskTrigger -Daily -At $timeText),
      (New-ScheduledTaskTrigger -AtLogOn)
    )
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  }
}

function Uninstall-ReportSchedule {
  Get-ScheduledTask | Where-Object { $_.TaskName -like "Outlook Mail Reporter*" } | ForEach-Object {
    Unregister-ScheduledTask -TaskName $_.TaskName -Confirm:$false
  }
}

function Run-Report {
  param([bool]$UseAI, [string]$ApiKey, [int]$SinceHours, [string]$OutputDir)
  New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
  $date = (Get-Date).ToString("yyyy-MM-dd")
  $stamp = (Get-Date).ToString("HHmmss")
  $md = Join-Path $OutputDir "mail-report-$date.md"
  $xlsx = Join-Path $OutputDir "mail-report-$date-$stamp.xlsx"
  $json = Join-Path $OutputDir "mail-report-$date-$stamp.json"
  $data = Read-OutlookMessages -SinceHours $SinceHours -Limit 400 -PreviewChars 1400
  $threads = Build-ThreadSummaries $data.Messages
  $data | ConvertTo-Json -Depth 8 | Set-Content -Path $json -Encoding UTF8
  if ($UseAI) { New-AIReport -Data $data -ApiKey $ApiKey -ReportPath $md } else { New-OfflineReport -Data $data -Threads $threads -ReportPath $md }
  $excelMsg = Export-ExcelReport -Data $data -Threads $threads -XlsxPath $xlsx
  [pscustomobject]@{ Markdown=$md; Excel=$xlsx; Json=$json; ExcelMessage=$excelMsg; MessageCount=$data.Messages.Count; ThreadCount=$threads.Count }
}

if ($Scheduled) {
  $logDir = Join-Path $OutputDir "logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $log = Join-Path $logDir ("scheduled-" + (Get-Date).ToString("yyyy-MM-dd") + ".log")
  try {
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
      [System.Windows.Forms.MessageBox]::Show($message, "Outlook Mail Reporter Error", "OK", "Error") | Out-Null
    } catch {}
    throw
  }
  return
}

$form = New-Object Windows.Forms.Form
$form.Text = "Outlook Mail Reporter"
$form.Size = New-Object Drawing.Size(720, 440)
$form.StartPosition = "CenterScreen"

$label = New-Object Windows.Forms.Label
$label.Text = "Outlook Mail Reporter"
$label.Font = New-Object Drawing.Font("Segoe UI", 16, [Drawing.FontStyle]::Bold)
$label.Location = New-Object Drawing.Point(18, 16)
$label.Size = New-Object Drawing.Size(500, 34)
$form.Controls.Add($label)

$offline = New-Object Windows.Forms.RadioButton
$offline.Text = "Non-AI offline report"
$offline.Checked = $true
$offline.Location = New-Object Drawing.Point(24, 70)
$offline.Size = New-Object Drawing.Size(190, 24)
$form.Controls.Add($offline)

$ai = New-Object Windows.Forms.RadioButton
$ai.Text = "Read mail with AI"
$ai.Location = New-Object Drawing.Point(230, 70)
$ai.Size = New-Object Drawing.Size(160, 24)
$form.Controls.Add($ai)

$apiLabel = New-Object Windows.Forms.Label
$apiLabel.Text = "OpenAI API Key"
$apiLabel.Location = New-Object Drawing.Point(24, 108)
$apiLabel.Size = New-Object Drawing.Size(120, 22)
$form.Controls.Add($apiLabel)

$apiBox = New-Object Windows.Forms.TextBox
$apiBox.Location = New-Object Drawing.Point(150, 104)
$apiBox.Size = New-Object Drawing.Size(390, 24)
$apiBox.UseSystemPasswordChar = $true
$apiBox.Text = [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User")
$form.Controls.Add($apiBox)

$saveKey = New-Object Windows.Forms.Button
$saveKey.Text = "Save Key"
$saveKey.Location = New-Object Drawing.Point(555, 102)
$saveKey.Size = New-Object Drawing.Size(100, 28)
$saveKey.Add_Click({
  if ([string]::IsNullOrWhiteSpace($apiBox.Text)) {
    [Windows.Forms.MessageBox]::Show("API key is empty.") | Out-Null
  } else {
    [Environment]::SetEnvironmentVariable("OPENAI_API_KEY", $apiBox.Text.Trim(), "User")
    $env:OPENAI_API_KEY = $apiBox.Text.Trim()
    [Windows.Forms.MessageBox]::Show("API key saved to current Windows user environment.") | Out-Null
  }
})
$form.Controls.Add($saveKey)

$modelLabel = New-Object Windows.Forms.Label
$modelLabel.Text = "Model"
$modelLabel.Location = New-Object Drawing.Point(24, 142)
$modelLabel.Size = New-Object Drawing.Size(120, 22)
$form.Controls.Add($modelLabel)

$modelBox = New-Object Windows.Forms.ComboBox
$modelBox.Location = New-Object Drawing.Point(150, 138)
$modelBox.Size = New-Object Drawing.Size(210, 24)
$modelBox.DropDownStyle = "DropDown"
[void]$modelBox.Items.Add("gpt-4.1-mini")
[void]$modelBox.Items.Add("gpt-4.1")
[void]$modelBox.Items.Add("gpt-4o-mini")
[void]$modelBox.Items.Add("gpt-4o")
$savedModel = [Environment]::GetEnvironmentVariable("OPENAI_MODEL", "User")
$modelBox.Text = if ($savedModel) { $savedModel } else { "gpt-4.1-mini" }
$form.Controls.Add($modelBox)

$saveModel = New-Object Windows.Forms.Button
$saveModel.Text = "Save Model"
$saveModel.Location = New-Object Drawing.Point(375, 136)
$saveModel.Size = New-Object Drawing.Size(100, 28)
$saveModel.Add_Click({
  if ([string]::IsNullOrWhiteSpace($modelBox.Text)) {
    [Windows.Forms.MessageBox]::Show("Model is empty.") | Out-Null
  } else {
    [Environment]::SetEnvironmentVariable("OPENAI_MODEL", $modelBox.Text.Trim(), "User")
    $env:OPENAI_MODEL = $modelBox.Text.Trim()
    [Windows.Forms.MessageBox]::Show("Model saved to current Windows user environment.") | Out-Null
  }
})
$form.Controls.Add($saveModel)

$hoursLabel = New-Object Windows.Forms.Label
$hoursLabel.Text = "Read last hours"
$hoursLabel.Location = New-Object Drawing.Point(24, 176)
$hoursLabel.Size = New-Object Drawing.Size(120, 22)
$form.Controls.Add($hoursLabel)

$hours = New-Object Windows.Forms.NumericUpDown
$hours.Location = New-Object Drawing.Point(150, 172)
$hours.Size = New-Object Drawing.Size(80, 24)
$hours.Minimum = 1
$hours.Maximum = 168
$hours.Value = 24
$form.Controls.Add($hours)

$outLabel = New-Object Windows.Forms.Label
$outLabel.Text = "Output folder"
$outLabel.Location = New-Object Drawing.Point(24, 214)
$outLabel.Size = New-Object Drawing.Size(120, 22)
$form.Controls.Add($outLabel)

$outBox = New-Object Windows.Forms.TextBox
$outBox.Location = New-Object Drawing.Point(150, 210)
$outBox.Size = New-Object Drawing.Size(390, 24)
$outBox.Text = Join-Path $PSScriptRoot "reports"
$form.Controls.Add($outBox)

$browse = New-Object Windows.Forms.Button
$browse.Text = "Browse"
$browse.Location = New-Object Drawing.Point(555, 208)
$browse.Size = New-Object Drawing.Size(100, 28)
$browse.Add_Click({
  $dlg = New-Object Windows.Forms.FolderBrowserDialog
  $dlg.SelectedPath = $outBox.Text
  if ($dlg.ShowDialog() -eq "OK") { $outBox.Text = $dlg.SelectedPath }
})
$form.Controls.Add($browse)

$run = New-Object Windows.Forms.Button
$run.Text = "Generate Report"
$run.Font = New-Object Drawing.Font("Segoe UI", 10, [Drawing.FontStyle]::Bold)
$run.Location = New-Object Drawing.Point(24, 258)
$run.Size = New-Object Drawing.Size(150, 36)
$form.Controls.Add($run)

$openFolder = New-Object Windows.Forms.Button
$openFolder.Text = "Open Reports"
$openFolder.Location = New-Object Drawing.Point(190, 258)
$openFolder.Size = New-Object Drawing.Size(120, 36)
$openFolder.Add_Click({ New-Item -ItemType Directory -Force -Path $outBox.Text | Out-Null; Start-Process $outBox.Text })
$form.Controls.Add($openFolder)

$scheduleBox = New-Object Windows.Forms.GroupBox
$scheduleBox.Text = "Automatic schedule"
$scheduleBox.Location = New-Object Drawing.Point(340, 246)
$scheduleBox.Size = New-Object Drawing.Size(324, 62)
$form.Controls.Add($scheduleBox)

$t0810 = New-Object Windows.Forms.CheckBox
$t0810.Text = "08:10"
$t0810.Checked = $true
$t0810.Location = New-Object Drawing.Point(12, 24)
$t0810.Size = New-Object Drawing.Size(66, 24)
$scheduleBox.Controls.Add($t0810)

$t1145 = New-Object Windows.Forms.CheckBox
$t1145.Text = "11:45"
$t1145.Checked = $true
$t1145.Location = New-Object Drawing.Point(82, 24)
$t1145.Size = New-Object Drawing.Size(66, 24)
$scheduleBox.Controls.Add($t1145)

$t1545 = New-Object Windows.Forms.CheckBox
$t1545.Text = "15:45"
$t1545.Checked = $true
$t1545.Location = New-Object Drawing.Point(152, 24)
$t1545.Size = New-Object Drawing.Size(66, 24)
$scheduleBox.Controls.Add($t1545)

$installSchedule = New-Object Windows.Forms.Button
$installSchedule.Text = "Install"
$installSchedule.Location = New-Object Drawing.Point(222, 20)
$installSchedule.Size = New-Object Drawing.Size(44, 28)
$scheduleBox.Controls.Add($installSchedule)

$removeSchedule = New-Object Windows.Forms.Button
$removeSchedule.Text = "Remove"
$removeSchedule.Location = New-Object Drawing.Point(268, 20)
$removeSchedule.Size = New-Object Drawing.Size(52, 28)
$scheduleBox.Controls.Add($removeSchedule)

$status = New-Object Windows.Forms.TextBox
$status.Location = New-Object Drawing.Point(24, 316)
$status.Size = New-Object Drawing.Size(640, 60)
$status.Multiline = $true
$status.ReadOnly = $true
$status.ScrollBars = "Vertical"
$form.Controls.Add($status)

$ai.Add_CheckedChanged({
  if ($ai.Checked -and [string]::IsNullOrWhiteSpace($apiBox.Text)) {
    $status.Text = "AI mode selected. Paste an OpenAI API key and click Save Key, or switch to Non-AI."
  }
})

$run.Add_Click({
  try {
    $run.Enabled = $false
    $status.Text = "Reading Outlook and generating report..."
    [Windows.Forms.Application]::DoEvents()
    $key = if ($apiBox.Text) { $apiBox.Text.Trim() } else { [Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User") }
    if (-not [string]::IsNullOrWhiteSpace($modelBox.Text)) { $env:OPENAI_MODEL = $modelBox.Text.Trim() }
    if ($ai.Checked -and [string]::IsNullOrWhiteSpace($key)) {
      [Windows.Forms.MessageBox]::Show("AI mode needs OPENAI_API_KEY. Paste your key, click Save Key, then run again.") | Out-Null
      return
    }
    $result = Run-Report -UseAI:$ai.Checked -ApiKey $key -SinceHours ([int]$hours.Value) -OutputDir $outBox.Text
    $status.Text = "Done.`r`nMessages: $($result.MessageCount), Threads: $($result.ThreadCount)`r`nMarkdown: $($result.Markdown)`r`nExcel: $($result.Excel)`r`nJSON: $($result.Json)`r`n$result.ExcelMessage"
  } catch {
    $status.Text = "Error: $($_.Exception.Message)"
    [Windows.Forms.MessageBox]::Show($status.Text, "Outlook Mail Reporter") | Out-Null
  } finally {
    $run.Enabled = $true
  }
})

$installSchedule.Add_Click({
  try {
    $times = @()
    if ($t0810.Checked) { $times += "08:10" }
    if ($t1145.Checked) { $times += "11:45" }
    if ($t1545.Checked) { $times += "15:45" }
    if ($times.Count -eq 0) { throw "Select at least one schedule time." }
    if ($ai.Checked -and [string]::IsNullOrWhiteSpace($apiBox.Text) -and [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable("OPENAI_API_KEY", "User"))) {
      throw "AI schedule needs an OPENAI_API_KEY. Paste your key and click Save Key first."
    }
    New-Item -ItemType Directory -Force -Path $outBox.Text | Out-Null
    Install-ReportSchedule -InstallDir $PSScriptRoot -OutputDir $outBox.Text -SinceHours ([int]$hours.Value) -UseAI:$ai.Checked -Times $times
    $status.Text = "Installed automatic schedule: $($times -join ', ').`r`nMode: $(if ($ai.Checked) { 'AI' } else { 'Non-AI' })`r`nOutput: $($outBox.Text)"
  } catch {
    $status.Text = "Schedule install error: $($_.Exception.Message)"
    [Windows.Forms.MessageBox]::Show($status.Text, "Outlook Mail Reporter") | Out-Null
  }
})

$removeSchedule.Add_Click({
  try {
    Uninstall-ReportSchedule
    $status.Text = "Removed Outlook Mail Reporter scheduled tasks."
  } catch {
    $status.Text = "Schedule remove error: $($_.Exception.Message)"
    [Windows.Forms.MessageBox]::Show($status.Text, "Outlook Mail Reporter") | Out-Null
  }
})

[Windows.Forms.Application]::EnableVisualStyles()
[void]$form.ShowDialog()
