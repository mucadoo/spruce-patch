# Installs the chosen spruce patch pieces onto a spruceOS SD card.
# Run via install.bat (double-click) or: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = 'Stop'
$here    = Split-Path -Parent $MyInvocation.MyCommand.Path
$payload = Join-Path $here 'payload'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

$catalogPath = Join-Path $here 'features.json'
if (-not (Test-Path -LiteralPath $catalogPath)) { throw 'features.json is missing. Re-download the patch.' }
$catalog = @(Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json)
if ($catalog.Count -eq 0) { throw 'features.json has no install options.' }

Write-Host ''
Write-Host 'Choose what to install. Type the numbers separated by spaces, or A for all.'
Write-Host ''
for ($i = 0; $i -lt $catalog.Count; $i++) {
    Write-Host ("  {0}  {1}" -f ($i + 1), $catalog[$i].name)
    Write-Host ("     {0}" -f $catalog[$i].description)
}
Write-Host '  A  All of the above'
Write-Host '  Q  Cancel'
Write-Host ''
$choice = Read-Host 'Choice'

$selected = @()
if ($choice -match '^(a|all)$') {
    $selected = @($catalog)
} elseif ($choice -match '^(q|quit|n|no)$' -or [string]::IsNullOrWhiteSpace($choice)) {
    Write-Host 'Cancelled. Nothing was changed.'
    exit 0
} else {
    $seen = @{}
    foreach ($token in ($choice -split '[,\s]+')) {
        if ($token -notmatch '^\d+$') { throw "Unknown choice '$token'. Use numbers from the list, or A." }
        $index = [int]$token - 1
        if ($index -lt 0 -or $index -ge $catalog.Count) { throw "There is no option $token." }
        $id = [string]$catalog[$index].id
        if (-not $seen.ContainsKey($id)) {
            $seen[$id] = $true
            $selected += $catalog[$index]
        }
    }
}
if ($selected.Count -eq 0) { Write-Host 'Cancelled. Nothing was changed.'; exit 0 }

# Find the spruce SD card (removable drive labelled SPRUCE).
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

foreach ($required in @('App\PyUI', 'spruce', 'RetroArch')) {
    if (-not (Test-Path -LiteralPath (Join-Path $card $required))) {
        throw "The card at $card does not look like spruce (missing $required)."
    }
}

# The picture pieces use a 640x480 window and the 640x480 overlay pack. A card
# that has already booted records its device in Saves\ra-configs\retroarch-<device>.cfg.
function Get-CardScreen($root) {
    $ra = Join-Path $root 'Saves\ra-configs'
    if (-not (Test-Path -LiteralPath $ra)) { return $null }
    $latest = Get-ChildItem -LiteralPath $ra -Filter 'retroarch-*.cfg' -File |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) { return $null }
    $name = $latest.BaseName.Substring('retroarch-'.Length)
    $plat = Get-ChildItem -LiteralPath (Join-Path $root 'spruce\scripts\platform') -Recurse -Filter "$name.cfg" -File |
        Select-Object -First 1
    $width = $null
    $height = $null
    if ($plat) {
        $text = [System.IO.File]::ReadAllText($plat.FullName)
        if ($text -match 'DISPLAY_WIDTH="(\d+)"') { $width = $Matches[1] }
        if ($text -match 'DISPLAY_HEIGHT="(\d+)"') { $height = $Matches[1] }
    }
    return [pscustomobject]@{ Name = $name; Width = $width; Height = $height }
}

$pictureIds = @('bezels', 'console-scale')
if (@($selected | Where-Object { $pictureIds -contains [string]$_.id }).Count -gt 0) {
    foreach ($needed in @(
        'RetroArch\.retroarch\overlay\640x480\Perfect',
        'RetroArch\.retroarch\shaders\sharpshimmerless\sharp-shimmerless.glslp'
    )) {
        if (-not (Test-Path -LiteralPath (Join-Path $card $needed))) {
            throw "This card is missing $needed. The picture pieces use the overlay pack and shader that spruceOS 4.6.0 already ships."
        }
    }
    $screen = Get-CardScreen $card
    if ($screen -and $screen.Width -and $screen.Height -and -not ($screen.Width -eq '640' -and $screen.Height -eq '480')) {
        throw ("This card last booted a $($screen.Name) ($($screen.Width)x$($screen.Height)). " +
            "The picture pieces are for a 640x480 screen. Install the RetroAchievements piece on its own, or boot the card in a 640x480 device first.")
    }
    if ($screen) {
        Write-Host "Picture pieces: $($screen.Name), $($screen.Width)x$($screen.Height)."
    } else {
        Write-Host 'Picture pieces: no device has booted this card yet. They are for a 640x480 screen.'
    }
}

function Merge-RetroarchCfg($sources) {
    $settings = [ordered]@{}
    foreach ($source in $sources) {
        foreach ($line in [System.IO.File]::ReadAllLines($source)) {
            if ($line -match '^\s*([^=#]+?)\s*=\s*(.*)$') {
                $settings[$Matches[1].Trim()] = $line.Trim()
            }
        }
    }
    $text = (($settings.Values) -join "`n") + "`n"
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("spruce-cfg-" + [guid]::NewGuid().ToString() + ".cfg")
    [System.IO.File]::WriteAllText($tmp, $text)
    return $tmp
}

$skip = @('spruce-config.json', 'config.json', 'proxy.sqlite3')
$found = @()
foreach ($feature in $selected) {
    $featureDir = Join-Path $payload ([string]$feature.id)
    if (-not (Test-Path -LiteralPath $featureDir)) { throw "Missing payload folder for $($feature.name)." }
    $found += @(Get-ChildItem -LiteralPath $featureDir -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($featureDir.Length).TrimStart('\')
        [pscustomobject]@{ Source = $_.FullName; Rel = $rel; Name = $_.Name; Feature = [string]$feature.name }
    } | Where-Object {
        $_.Name -notin $skip -and $_.Rel -notmatch '(^|\\)(image_cache|__pycache__)(\\|$)' -and $_.Name -notlike '*.pyc'
    })
}
if (-not $found) { throw 'Nothing to install for that choice. Re-download the patch.' }

# RetroArch cfgs and core-option files are merged, never replaced: keep what is already
# on the card, and let the patch's own keys win. This also covers a card that already
# has another piece installed.
$files = @()
foreach ($group in ($found | Group-Object Rel)) {
    $items = @($group.Group)
    $isCfg = $items[0].Name -like '*.cfg' -or $items[0].Name -like '*.opt'
    $cardTarget = Join-Path $card $items[0].Rel
    if ($isCfg) {
        $sources = @()
        if (Test-Path -LiteralPath $cardTarget) { $sources += $cardTarget }
        $sources += @($items.Source)
        $files += [pscustomobject]@{
            Source  = Merge-RetroarchCfg $sources
            Rel     = $items[0].Rel
            Name    = $items[0].Name
            Feature = ($items.Feature -join ' + ')
        }
    } else {
        $files += $items[0]
    }
}

Write-Host ''
Write-Host "Installing:"
$selected | ForEach-Object { Write-Host "  - $($_.name)" }
Write-Host ''
Write-Host "Files ($($files.Count)):"
$files | ForEach-Object { Write-Host "  $($_.Rel)" }
Write-Host ''

$answer = Read-Host 'Install these files onto the SPRUCE card? (y/N)'
if ($answer -notin @('y', 'Y', 'yes', 'YES')) { Write-Host 'Cancelled. Nothing was changed.'; exit 0 }

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

Write-Step 'Copying files...'
foreach ($f in $files) {
    $target = Join-Path $card $f.Rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $f.Source -Destination $target -Force
}

Write-Host ''
Write-Host 'Done. Safely eject the SD card, put it back in the handheld, and reboot.' -ForegroundColor Green
Write-Host "To undo, copy the files from $backupDir back onto the card."
