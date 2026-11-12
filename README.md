# spruce Flip patch

Optional extras for **spruceOS 4.6.0** on the Miyoo Flip. The installer asks which pieces you want.

This is an unofficial patch. It is not part of spruceOS.

The patched spruce files stay under the [spruceOS license](https://creativecommons.org/licenses/by-nc/4.0/) (CC BY-NC 4.0, non-commercial). Copyright (c) 2024 SpruceOS, a project by SpruceUI.

## Pieces

**RetroAchievements offline cache**

- **Cache for offline** lets you pick a platform, a folder, or individual games. Games that are already cached are skipped. A game RetroAchievements does not know is marked **No achievements**. A known game whose dump has no set is marked **Unsupported version**. A file that cannot be read is marked **Could not read**. Those are not offered as still to cache.
- **Keep library offline** watches the whole library, or only the platforms you choose. When you turn it on, you can cache the games already in that folder, or only games you add later. [How the watch works](docs/keep-library-offline.md).
- **Cached Games** shows each game's own icon.
- **RetroAchievements** sits on the main settings list, under that name.
- Cached achievement images are served again. Stock spruce turned image serving off, which left icons and badges blank.

**Handheld bezels**

Frames for Game Boy, Game Boy Color, and GBA, using the overlay art already on the spruce card. NES, SNES, and Genesis stay full screen. That matches Knulli's default bezel pack on a 4:3 screen: those consoles were made for a 4:3 TV, so the pack has no frame for them there. Game Boy and GBA do.

**Sharp shader**

Knulli's default shader, sharp-bilinear-simple, on Game Boy, Game Boy Color, GBA, NES, SNES, and Genesis. Bilinear smoothing is turned off so the shader does the scaling. The shader file is already part of spruce. If you also install handheld bezels, the frames stay.

## Install

You need Windows, a spruceOS **4.6.0** card, and the card's volume name set to **SPRUCE** (that is the stock name).

1. Download this repo (Code → Download ZIP) and unzip it.
2. Put the SD card in the PC. Use the spruce card, the one labelled SPRUCE.
3. Double-click `install.bat`.
4. Type the numbers of the pieces you want, or `A` for all of them.
5. Read the file list and type `y` to confirm.
6. Eject the card, put it back in the Miyoo, and reboot.

The installer copies each current file to a backup folder in your user profile (`spruce-patch-backup-<date>`) before it overwrites anything. To undo, copy those files back onto the card in the same folders.

## What it does not touch

- `Saves\spruce\spruce-config.json` (your settings and login)
- `App\RAOfflineProxy\data\` (cache database, logs, and downloaded images)
- RetroArch core options and button remaps
- Themes, ROMs, and BIOS files
