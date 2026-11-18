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

# Emu\N64\config.json holds the whole N64 menu. The patch only adds the keys it
# needs (per-game overrides), so merge those into the card's copy and keep the rest.
function Merge-JsonOverrides([string]$CardFile, [string]$PatchFile) {
    $target = [System.IO.File]::ReadAllText($CardFile) | ConvertFrom-Json
    $patch  = [System.IO.File]::ReadAllText($PatchFile) | ConvertFrom-Json
    function Merge-Node($into, $from) {
        foreach ($prop in $from.PSObject.Properties) {
            $existing = $into.PSObject.Properties[$prop.Name]
            if ($existing -and $existing.Value -is [pscustomobject] -and $prop.Value -is [pscustomobject]) {
                Merge-Node $existing.Value $prop.Value
            } else {
                $into | Add-Member -NotePropertyName $prop.Name -NotePropertyValue $prop.Value -Force
            }
        }
    }
    Merge-Node $target $patch
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("spruce-json-" + [guid]::NewGuid().ToString() + ".json")
    [System.IO.File]::WriteAllText($tmp, ($target | ConvertTo-Json -Depth 32))
    return $tmp
}

$skip = @('spruce-config.json', 'proxy.sqlite3')
$skipRel = @('App\RAOfflineProxy\data\config.json')
$found = @()
foreach ($feature in $selected) {
    $featureDir = Join-Path $payload ([string]$feature.id)
    if (-not (Test-Path -LiteralPath $featureDir)) { throw "Missing payload folder for $($feature.name)." }
    $found += @(Get-ChildItem -LiteralPath $featureDir -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($featureDir.Length).TrimStart('\')
        [pscustomobject]@{ Source = $_.FullName; Rel = $rel; Name = $_.Name; Feature = [string]$feature.name }
    } | Where-Object {
        $_.Name -notin $skip -and $_.Rel -notin $skipRel -and $_.Rel -notmatch '(^|\\)(image_cache|__pycache__)(\\|$)' -and $_.Name -notlike '*.pyc'
    })
}
if (-not $found) { throw 'Nothing to install for that choice. Re-download the patch.' }

# RetroArch cfgs, core options and remaps are merged, never replaced: keep what is already
# on the card, and let the patch's own keys win. This also covers a card that already
# has another piece installed.
$files = @()
foreach ($group in ($found | Group-Object Rel)) {
    $items = @($group.Group)
    $isCfg = $items[0].Name -like '*.cfg' -or $items[0].Name -like '*.opt' -or $items[0].Name -like '*.rmp'
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
    } elseif ($items[0].Rel -eq 'Emu\N64\config.json') {
        if (-not (Test-Path -LiteralPath $cardTarget)) {
            Write-Host "Skipped $($items[0].Rel): the card has no N64 menu config to merge into."
            continue
        }
        $merged = $cardTarget
        foreach ($item in $items) { $merged = Merge-JsonOverrides $merged $item.Source }
        $files += [pscustomobject]@{
            Source  = $merged
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

function Hide-BootMenuFromGames([string]$Card) {
    $roms = Join-Path $Card 'App\PyUI\main-ui\games\utils\rom_utils.py'
    if (-not (Test-Path -LiteralPath $roms)) { return }
    $text = [System.IO.File]::ReadAllText($roms)
    if ($text.Contains('_NOT_A_GAME')) { return }
    $nl = "`n"
    if ($text.Contains("`r`n")) { $nl = "`r`n" }
    $marker = "from pathlib import Path${nl}${nl}class RomUtils:"
    if (-not $text.Contains($marker)) {
        Write-Host 'Could not update the games menu. DS may still show when it only has the boot menu.'
        return
    }
    $note = @"
from pathlib import Path

# spruce leaves these in the DS folders so the launcher has a file to open.
# They are not games. A system that only has one of them stays off the games menu.
_NOT_A_GAME = {"bootmenu.nds", "bootmenudsi.nds"}

class RomUtils:
"@
    $note = $note -replace "`r`n", $nl
    $text = $text.Replace($marker, $note.TrimEnd() + $nl)
    $fileSkip = "                        continue${nl}${nl}                    if len(valid_suffix_set) == 0:"
    $fileSkipNew = "                        continue${nl}${nl}                    if entry.name.lower() in _NOT_A_GAME:${nl}                        continue${nl}${nl}                    if len(valid_suffix_set) == 0:"
    $listSkip = "                    if name.startswith('.'):${nl}                        continue${nl}${nl}                    try:"
    $listSkipNew = "                    if name.startswith('.'):${nl}                        continue${nl}${nl}                    if name.lower() in _NOT_A_GAME:${nl}                        continue${nl}${nl}                    try:"
    if (-not $text.Contains($fileSkip) -or -not $text.Contains($listSkip)) {
        Write-Host 'Could not update the games menu. DS may still show when it only has the boot menu.'
        return
    }
    $text = $text.Replace($fileSkip, $fileSkipNew).Replace($listSkip, $listSkipNew)
    [System.IO.File]::WriteAllText($roms, $text)
}

function Add-HotkeysMenu([string]$Card) {
    $menu = Join-Path $Card 'App\PyUI\main-ui\menus\settings\basic_settings_menu.py'
    if (-not (Test-Path -LiteralPath $menu)) { return }
    $text = [System.IO.File]::ReadAllText($menu)
    if ($text.Contains('HotkeysMenu')) { return }
    $nl = "`n"
    if ($text.Contains("`r`n")) { $nl = "`r`n" }
    $import = "from menus.settings.about_menu import AboutMenu"
    if (-not $text.Contains($import)) {
        Write-Host 'Could not add the Hotkeys row. The settings menu layout was not recognised.'
        return
    }
    $text = $text.Replace($import, "from menus.settings.about_menu import AboutMenu${nl}from menus.settings.hotkeys_menu import HotkeysMenu")
    $method = "    def launch_about(self,input):"
    $methodNew = "    def launch_hotkeys(self,input):${nl}        if(ControllerInput.A == input):${nl}            HotkeysMenu().show_menu()${nl}${nl}    def launch_about(self,input):"
    $entry = 'primary_text=Language.aboutThisDevice(),'
    $entryNew = @"
primary_text="Hotkeys",
                            value_text=None,
                            image_path=None,
                            image_path_selected=None,
                            description=None,
                            icon=None,
                            value=self.launch_hotkeys
                        )
                )

            option_list.append(
                    GridOrListEntry(
                            primary_text=Language.aboutThisDevice(),
"@
    $entryNew = $entryNew -replace "`r`n", $nl
    if (-not $text.Contains($method) -or -not $text.Contains($entry)) {
        Write-Host 'Could not add the Hotkeys row. The settings menu layout was not recognised.'
        return
    }
    $text = $text.Replace($method, $methodNew).Replace($entry, $entryNew.TrimEnd())
    [System.IO.File]::WriteAllText($menu, $text)
}

function Enable-N64StickMenu([string]$Card) {
    $launchPath = Join-Path $Card 'spruce\scripts\emu\standard_launch.sh'
    if (-not (Test-Path -LiteralPath $launchPath)) { return }
    $text = [System.IO.File]::ReadAllText($launchPath)
    if ($text.Contains('n64_stick_input.sh')) { return }
    $nl = "`n"
    if ($text.Contains("`r`n")) { $nl = "`r`n" }
    $old = "load_n64_controller_profile${nl}			run_retroarch"
    $new = "load_n64_controller_profile${nl}			[ -f /mnt/SDCARD/spruce/scripts/emu/lib/n64_stick_input.sh ] && . /mnt/SDCARD/spruce/scripts/emu/lib/n64_stick_input.sh && apply_n64_stick_input${nl}			run_retroarch"
    if (-not $text.Contains($old)) {
        Write-Host 'Could not add the N64 stick option to the launch script. Its layout was not recognised.'
        return
    }
    [System.IO.File]::WriteAllText($launchPath, $text.Replace($old, $new))
}

function Move-DisplaySettingsToRoot([string]$Card) {
    $basicPath = Join-Path $Card 'App\PyUI\main-ui\menus\settings\basic_settings_menu.py'
    $extraPath = Join-Path $Card 'App\PyUI\main-ui\menus\settings\extra_settings_menu.py'
    if (-not (Test-Path -LiteralPath $basicPath) -or -not (Test-Path -LiteralPath $extraPath)) { return }
    $basic = [System.IO.File]::ReadAllText($basicPath)
    $extra = [System.IO.File]::ReadAllText($extraPath)
    $nl = "`n"
    if ($basic.Contains("`r`n")) { $nl = "`r`n" }

    if (-not $basic.Contains('DisplaySettingsMenu')) {
        $import = 'from menus.settings.about_menu import AboutMenu'
        $method = '    def launch_about(self,input):'
        $ret    = '        return option_list'
        $retCount = ([regex]::Matches($basic, [regex]::Escape($ret))).Count
        if (-not $basic.Contains($import) -or -not $basic.Contains($method) -or $retCount -ne 1) {
            Write-Host 'Could not move Display settings to the main Settings menu. The settings menu layout was not recognised.'
            return
        }
        $basic = $basic.Replace($import, $import + $nl + 'from menus.settings.display_settings_menu import DisplaySettingsMenu')
        $basic = $basic.Replace($method, '    def launch_display(self,input):' + $nl +
            '        if(ControllerInput.A == input):' + $nl +
            '            DisplaySettingsMenu().show_menu()' + $nl + $nl + $method)
        $add = @"
        display_at = next((i for i, entry in enumerate(option_list) if entry.primary_text == Language.additional_settings()), len(option_list))
        option_list.insert(display_at, GridOrListEntry(
                        primary_text=Language.display_settings(),
                        value_text=None,
                        image_path=None,
                        image_path_selected=None,
                        description=None,
                        icon=None,
                        value=self.launch_display
                    ))
        return option_list
"@
        $add = ($add -replace "`r?`n", $nl).TrimEnd()
        $basic = $basic.Replace($ret, $add)
        [System.IO.File]::WriteAllText($basicPath, $basic)
    }

    if ($extra.Contains('# Only show display settings')) {
        $pattern = '(?s)        # Only show display settings.*?(?=\s*option_list\.append\(\s*GridOrListEntry\(\s*primary_text=Language\.animation_settings\(\))'
        $newExtra = [regex]::Replace($extra, $pattern, '', 1)
        if ($newExtra -eq $extra) {
            Write-Host 'Could not remove Display settings from Additional settings. Its layout was not recognised.'
        } else {
            [System.IO.File]::WriteAllText($extraPath, $newExtra)
        }
    }
}

function Enable-SaveAutoBackup([string]$Card) {
    $main = Join-Path $Card 'App\PyUI\main-ui\mainui.py'
    if (-not (Test-Path -LiteralPath $main)) { return }
    $text = [System.IO.File]::ReadAllText($main)
    if ($text.Contains('def _start_save_backup(')) { return }
    $call = "    audio_route_thread.start()"
    if (-not $text.Contains($call)) { return }
    $nl = "`n"
    if ($text.Contains("`r`n")) { $nl = "`r`n" }
    $text = $text.Replace($call, "$call$nl    _start_save_backup()")
    $fn = @"

def _start_save_backup():
    """Start the save backup timer. It keeps running after a game launches."""
    script = "/mnt/SDCARD/App/SaveManager/auto_backup.sh"
    if not os.path.isfile(script):
        return
    import subprocess
    try:
        subprocess.Popen(
            ["/bin/sh", script],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        pass

"@
    $fn = $fn -replace "`r`n", $nl
    $text = $text.Replace("def start_background_threads():", "$fn" + "def start_background_threads():")
    [System.IO.File]::WriteAllText($main, $text)
}

Write-Step 'Copying files...'
foreach ($f in $files) {
    $target = Join-Path $card $f.Rel
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
    Copy-Item -LiteralPath $f.Source -Destination $target -Force
}

if (@($selected | Where-Object { $_.id -eq 'saves' }).Count -gt 0) {
    Enable-SaveAutoBackup $card
}
if (@($selected | Where-Object { $_.id -eq 'hotkeys' }).Count -gt 0) {
    Add-HotkeysMenu $card
}
if (@($selected | Where-Object { $_.id -eq 'display' }).Count -gt 0) {
    Move-DisplaySettingsToRoot $card
}
if (@($selected | Where-Object { $_.id -eq 'n64-dpad-stick' }).Count -gt 0) {
    Enable-N64StickMenu $card
}
Hide-BootMenuFromGames $card

Write-Host ''
Write-Host 'Done. Safely eject the SD card, put it back in the handheld, and reboot.' -ForegroundColor Green
Write-Host "To undo, copy the files from $backupDir back onto the card."
