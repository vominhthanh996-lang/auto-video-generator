param(
  [int]$Limit = 20,
  [string]$Folder = "Inbox",
  [datetime]$Date = (Get-Date),
  [switch]$InboxOnly,
  [int]$PreviewChars = 1200
)

$ErrorActionPreference = "Stop"

function Convert-MailItem {
  param($Item, $FolderPath)

  $senderAddress = $null
  try { $senderAddress = $Item.SenderEmailAddress } catch {}
  $conversationId = ""
  $conversationTopic = ""
  $to = ""
  $cc = ""
  try { $conversationId = $Item.ConversationID } catch {}
  try { $conversationTopic = $Item.ConversationTopic } catch {}
  try { $to = $Item.To } catch {}
  try { $cc = $Item.CC } catch {}
  $bodyPreview = ""
  try {
    $bodyPreview = (($Item.Body -replace "\s+", " ").Trim())
    if ($bodyPreview.Length -gt $PreviewChars) {
      $bodyPreview = $bodyPreview.Substring(0, $PreviewChars)
    }
  } catch {}

  [pscustomobject]@{
    ReceivedTime   = $Item.ReceivedTime
    Folder         = $FolderPath
    ConversationID = $conversationId
    ConversationTopic = $conversationTopic
    SenderName     = $Item.SenderName
    SenderEmail    = $senderAddress
    To             = $to
    Cc             = $cc
    Subject        = $Item.Subject
    Importance     = $Item.Importance
    HasAttachments = [bool]$Item.Attachments.Count
    BodyPreview    = $bodyPreview
  }
}

try {
  $outlook = [Runtime.InteropServices.Marshal]::GetActiveObject("Outlook.Application")
} catch {
  $outlook = New-Object -ComObject Outlook.Application
}
$namespace = $outlook.GetNamespace("MAPI")

$dayStart = Get-Date -Date $Date -Hour 0 -Minute 0 -Second 0
$dayEnd = $dayStart.AddDays(1)
$filter = "[ReceivedTime] >= '$($dayStart.ToString("g"))' AND [ReceivedTime] < '$($dayEnd.ToString("g"))'"
$messages = New-Object System.Collections.Generic.List[object]

function Read-MailFolder {
  param($MailFolder)

  if ($messages.Count -ge $Limit) { return }

  try {
    $items = $MailFolder.Items
    $items.Sort("[ReceivedTime]", $true)
    $restricted = $items.Restrict($filter)

    foreach ($item in $restricted) {
      if ($messages.Count -ge $Limit) { break }
      if ($item -and $item.MessageClass -like "IPM.Note*") {
        $messages.Add((Convert-MailItem $item $MailFolder.FolderPath)) | Out-Null
      }
    }
  } catch {
    # Some Outlook folders do not expose mail items or are unavailable offline.
  }

  if (-not $InboxOnly) {
    foreach ($subFolder in $MailFolder.Folders) {
      Read-MailFolder $subFolder
      if ($messages.Count -ge $Limit) { break }
    }
  }
}

if ($InboxOnly) {
  # olFolderInbox = 6. This uses the default mailbox signed into Outlook Desktop.
  Read-MailFolder ($namespace.GetDefaultFolder(6))
} else {
  foreach ($storeRoot in $namespace.Folders) {
    Read-MailFolder $storeRoot
    if ($messages.Count -ge $Limit) { break }
  }
}

$sortedMessages = @($messages | Sort-Object ReceivedTime -Descending)

[pscustomobject]@{
  Source = "Outlook Desktop COM"
  Mailbox = $namespace.CurrentUser.Name
  Scope = $(if ($InboxOnly) { "Default Inbox" } else { "All Outlook folders" })
  Date = $dayStart.ToString("yyyy-MM-dd")
  Count = $sortedMessages.Count
  Messages = $sortedMessages
} | ConvertTo-Json -Depth 5
