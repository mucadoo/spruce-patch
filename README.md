# spruce RetroAchievements offline patch

A small patch for **spruceOS 4.6.0** on the Miyoo Flip. It makes the offline achievement cache easier to use, and it fixes blank achievement icons.

This is an unofficial patch. It is not part of spruceOS.

The patched spruce files stay under the [spruceOS license](https://creativecommons.org/licenses/by-nc/4.0/) (CC BY-NC 4.0, non-commercial). Copyright (c) 2024 SpruceOS, a project by SpruceUI.

## What it changes

- **Cache for offline** lets you pick a platform, a folder, or individual games. Games that are already cached are skipped. A game that was checked and has no RetroAchievements set is marked **No achievements**, in the list and on the progress screen.
- **Keep library offline** watches the whole library, or only the platforms you choose, and caches games you add later.
- **Cached Games** shows each game's own icon.
- **RetroAchievements** sits on the main settings list, under that name.
- Cached achievement images are served again. Stock spruce turned image serving off, which left icons and badges blank.

Your ROMs, saves, RetroAchievements login, and existing cache are left alone.

## Install

You need Windows, a spruceOS **4.6.0** card, and the card's volume name set to **SPRUCE** (that is the stock name).

1. Download this repo (Code → Download ZIP) and unzip it.
2. Put the SD card in the PC. Use the spruce card, the one labelled SPRUCE.
3. Double-click `install.bat`.
4. Read the file list and type `y` to confirm.
5. Eject the card, put it back in the Miyoo, and reboot.

The installer copies each current file to a backup folder in your user profile (`spruce-patch-backup-<date>`) before it overwrites anything. To undo the patch, copy those files back onto the card in the same folders.

## What it does not touch

- `Saves\spruce\spruce-config.json` (your settings and login)
- `App\RAOfflineProxy\data\` (cache database, logs, and downloaded images)
- RetroArch core options and button remaps
- Themes, ROMs, and BIOS files
