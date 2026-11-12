# Installs the spruce RetroAchievements / offline cache patch onto a Miyoo SD card.
# Run via install.bat (double-click) or: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = 'Stop'
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$payload = Join-Path $here 'payload'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# 1. Find the spruce SD card (removable drive labelled SPRUCE).
Write-Step 'Looking for the SPRUCE SD card...'
$cards = @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=2' |
    Where-Object { $_.VolumeName -eq 'SPRUCE' })

if ($cards.Count -eq 0) {
    throw 'No removable drive labelled SPRUCE was found. Insert the spruce SD card and run again.'
}
if ($cards.Count -gt 1) {
    throw ('More than one SPRUCE card found: ' + (($cards | ForEach-Object DeviceID) -join ', ') + '. Remove the extra card and run again.')
}
$card = $cards[0].DeviceID + '\'
Write-Host "Found SPRUCE card at $card"

# 2. Make sure it really is a spruce install.
foreach ($required in @('App\PyUI', 'App\RAOfflineProxy', 'spruce')) {
    if (-not (Test-Path -LiteralPath (Join-Path $card $required))) {
        throw "The card at $card does not look like spruce (missing $required)."
    }
}

# 3. Build the list of files to copy. Never touch user data or secrets.
$skip = @('spruce-config.json', 'config.json', 'proxy.sqlite3')
$files = Get-ChildItem -LiteralPath $payload -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($payload.Length).TrimStart('\')
    [pscustomobject]@{ Source = $_.FullName; Rel = $rel; Name = $_.Name }
} | Where-Object {
    $_.Name -notin $skip -and $_.Rel -notmatch '(^|\\)image_cache(\\|$)'
}
if (-not $files) { throw 'The payload folder is empty. Re-download the patch.' }

Write-Host ''
Write-Host "Files to install ($($files.Count)):"
$files | ForEach-Object { Write-Host "  $($_.Rel)" }
Write-Host ''

$answer = Read-Host 'Install these files onto the SPRUCE card? (y/N)'
if ($answer -notin @('y', 'Y', 'yes', 'YES')) { Write-Host 'Cancelled. Nothing was changed.'; exit 0 }

# 4. Back up the originals first.
$stamp     = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = Join-Path $env:USERPROFILE "spruce-patch-backup-$stamp"
Write-Step "Backing up current files to $backupDir"
foreach ($f in $files) {
    $target = Join-Path $card $f.Rel
    if (Test-Path -LiteralPath $target) {
        $dest = Join-Path $backupDir $f.Rel
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $dest) | Out-Null
        Copy-Item -LiteralPath $target -Destination $dest -Force
    }
}

# 5. Copy the patched files onto the card.
Write-Step 'Copying patched files...'
foreach ($f in $files) {
    $target = Join-Path $card $f.Rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $f.Source -Destination $target -Force
}

Write-Host ''
Write-Host 'Done. Safely eject the SD card, put it back in the Miyoo, and reboot.' -ForegroundColor Green
Write-Host "To undo, copy the files from $backupDir back onto the card."
