param(
  [Parameter(Mandatory=$true)]
  [string]$Storyboard,

  [string]$Voice = "",

  [int]$Rate = 0,

  [int]$Volume = 100
)

Add-Type -AssemblyName System.Speech

$storyboardPath = [System.IO.Path]::GetFullPath($Storyboard)
$storyboardDir = [System.IO.Path]::GetDirectoryName($storyboardPath)
$assetsDir = Join-Path $storyboardDir "assets"
New-Item -ItemType Directory -Force -Path $assetsDir | Out-Null

$json = [System.IO.File]::ReadAllText($storyboardPath, [System.Text.Encoding]::UTF8)
$config = $json | ConvertFrom-Json

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = $Rate
$synth.Volume = $Volume

if ($Voice -ne "") {
  $synth.SelectVoice($Voice)
}

$index = 0
foreach ($scene in $config.scenes) {
  $index += 1
  $text = $scene.narration
  if ([string]::IsNullOrWhiteSpace($text)) {
    $text = $scene.subtitle
  }
  if ([string]::IsNullOrWhiteSpace($text)) {
    $text = $scene.text
  }
  if ([string]::IsNullOrWhiteSpace($text)) {
    throw "Scene $index has no narration/subtitle/text."
  }

  if ([string]::IsNullOrWhiteSpace($scene.audio)) {
    $fileName = "scene-{0:D2}.wav" -f $index
    $scene | Add-Member -NotePropertyName audio -NotePropertyValue ("assets/" + $fileName) -Force
  }

  $audioPath = $scene.audio
  if (-not [System.IO.Path]::IsPathRooted($audioPath)) {
    $audioPath = Join-Path $storyboardDir $audioPath
  }
  $audioPath = [System.IO.Path]::GetFullPath($audioPath)
  New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($audioPath)) | Out-Null

  $synth.SetOutputToWaveFile($audioPath)
  $synth.Speak($text)
  $synth.SetOutputToNull()

  if ([string]::IsNullOrWhiteSpace($scene.subtitle)) {
    $scene | Add-Member -NotePropertyName subtitle -NotePropertyValue $text -Force
  }
}

$outJson = $config | ConvertTo-Json -Depth 20
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($storyboardPath, $outJson, $utf8NoBom)

Write-Output (@{
  storyboard = $storyboardPath
  scenes = $config.scenes.Count
  voice = $synth.Voice.Name
} | ConvertTo-Json)
