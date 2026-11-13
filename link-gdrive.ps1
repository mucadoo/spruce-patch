# Links the Saves app to Google Drive. One sign-in in the browser, then the
# handheld can upload a backup of every battery save and savestate.
# Pass -BinaryOnly to put the uploader on the card without signing in.

param([switch]$BinaryOnly)

$ErrorActionPreference = 'Stop'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

$cards = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=2' |
    Where-Object { $_.VolumeName -eq 'SPRUCE' })
if ($cards.Count -eq 0) { throw 'No removable drive labelled SPRUCE was found. Insert the spruce SD card and run again.' }
if ($cards.Count -gt 1) { throw 'More than one SPRUCE card is connected. Remove the extra card and run again.' }
$card = $cards[0].DeviceID + '\'
$app = Join-Path $card 'App\SaveManager'
if (-not (Test-Path -LiteralPath $app)) { throw "Saves is not on this card yet ($app)." }

Write-Step 'Checking the current rclone release...'
$versionLine = (Invoke-RestMethod 'https://downloads.rclone.org/version.txt').ToString().Trim()
if ($versionLine -notmatch 'v\d+\.\d+\.\d+') { throw "Unexpected rclone version line: $versionLine" }
$version = $Matches[0]
$base = "https://downloads.rclone.org/$version"
$sums = @{}
foreach ($line in (Invoke-RestMethod "$base/SHA256SUMS").ToString().Split("`n")) {
    if ($line -match '^([0-9a-fA-F]{64})\s+(\S+)') { $sums[$Matches[2]] = $Matches[1].ToLower() }
}

function Get-RcloneZip($platform) {
    $name = "rclone-$version-$platform.zip"
    if (-not $sums.ContainsKey($name)) { throw "No checksum published for $name." }
    $dest = Join-Path ([System.IO.Path]::GetTempPath()) $name
    Write-Step "Downloading $name"
    Invoke-WebRequest -Uri "$base/$name" -OutFile $dest
    $hash = (Get-FileHash -LiteralPath $dest -Algorithm SHA256).Hash.ToLower()
    if ($hash -ne $sums[$name]) { throw "Checksum does not match for $name." }
    $extract = Join-Path ([System.IO.Path]::GetTempPath()) ("rclone-" + $platform)
    if (Test-Path -LiteralPath $extract) { Remove-Item -LiteralPath $extract -Recurse -Force }
    Expand-Archive -LiteralPath $dest -DestinationPath $extract -Force
    return $extract
}

$onCard = Join-Path $app 'rclone'
$haveUploader = (Test-Path -LiteralPath $onCard) -and ((Get-Item -LiteralPath $onCard).Length -gt 1MB)
if (-not $haveUploader) {
    $linux = Get-RcloneZip 'linux-arm64'
    $binary = Get-ChildItem -LiteralPath $linux -Recurse -Filter 'rclone' -File | Select-Object -First 1
    if (-not $binary) { throw 'The linux rclone archive did not contain the rclone program.' }
    Copy-Item -LiteralPath $binary.FullName -Destination $onCard -Force
}
Write-Host "Uploader is on the card."

if ($BinaryOnly) { return }

Write-Step 'Opening the browser so you can sign in to Google Drive...'
Write-Host 'Allow rclone to create files in your Drive. This does not give it your whole Drive.'
$windows = Get-RcloneZip 'windows-amd64'
$rclone = Get-ChildItem -LiteralPath $windows -Recurse -Filter 'rclone.exe' -File | Select-Object -First 1
if (-not $rclone) { throw 'The windows rclone archive did not contain rclone.exe.' }
$output = & $rclone.FullName authorize 'drive' '{"scope":"drive.file"}' 2>&1 | Out-String
$match = [regex]::Match($output, '\{[^{}]*"refresh_token"[^{}]*\}')
if (-not $match.Success) { throw 'Google Drive was not linked. Sign in in the browser, then run this again.' }
$token = $match.Groups[0].Value.Trim()
$conf = "[gdrive]`r`ntype = drive`r`nscope = drive.file`r`ntoken = " + $token + "`r`n"
$confPath = Join-Path $app 'rclone.conf'
[System.IO.File]::WriteAllText($confPath, $conf)
Write-Host ''
Write-Host 'Linked. Put the card back in the handheld, open Apps, then Saves, then Backup to Google Drive.' -ForegroundColor Green
Write-Host 'The handheld needs Wi-Fi for the upload.'
