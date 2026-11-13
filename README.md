# spruce patch

Optional extras for **spruceOS 4.6.0**. The installer asks which pieces you want.

This is an unofficial patch. It is not part of spruceOS.

The patched spruce files stay under the [spruceOS license](https://creativecommons.org/licenses/by-nc/4.0/) (CC BY-NC 4.0, non-commercial). Copyright (c) 2024 SpruceOS, a project by SpruceUI.

## Pieces

**RetroAchievements offline cache**

- **Cache for offline** lets you pick a platform, a folder, or individual games. Games that are already cached are skipped. A game RetroAchievements does not know is marked **No achievements**. A known game whose dump has no set is marked **Unsupported version**. A file that cannot be read is marked **Could not read**. Those are not offered as still to cache.
- **Keep library offline** watches the whole library, or only the platforms you choose. When you turn it on, you can cache the games already in that folder, or only games you add later. [How the watch works](docs/keep-library-offline.md).
- **Cached Games** shows each game's own icon.
- **RetroAchievements** sits on the main settings list, under that name.
- Cached achievement images are served again. Stock spruce turned image serving off, which left icons and badges blank.

**Handheld picture**

Tuned for a 3.5-inch 640×480 screen, following [Retro Game Corps' shader and overlay guide](https://retrogamecorps.com/2024/09/01/guide-shaders-and-overlays-on-retro-handhelds/). On a display this size he skips integer scale for GBA because 2× is only about 2.5 inches.

- Game Boy and Game Boy Color: the picture fills the screen height at the real 10:9 shape, bilinear off, sharp-shimmerless, Perfect frame in the side bars. Game Boy uses the Perfect DMG palette. Game Boy Color keeps accurate color correction, and its frame is at 80% so the grid does not darken the picture. Interframe blending is Simple.
- GBA: the picture fills the width (640×427), sharp-shimmerless evens the pixels, and the Perfect frame is the lighter 75% version.

The frames and the shader are already on a spruceOS 4.6.0 card. This piece only points at them. It is written for a 640×480 panel: Miyoo Flip, Miyoo A30, Miyoo Mini and Mini Plus, GKD Pixel 2, Anbernic RG28XX, the Anbernic RG XX models with a 640×480 screen, and the other spruce devices that use that same resolution. A different resolution, such as the TrimUI Brick or Smart Pro, is refused by the installer.

**Console picture**

NES, SNES, and Genesis fill the screen (aspect Full), with bilinear off and sharp-shimmerless so a non-integer scale does not leave uneven pixels. No frame. That is his preferred setup for pixel-era consoles on a 640×480 handheld: the largest image, with the pixels balanced, and without a heavy CRT shader.

**Save manager**

**Saves** is in the Apps menu. It lists every battery save and savestate under `Saves`, grouped by the core that wrote it, then by game. A savestate's picture shows in place of the icon. A file that is sitting outside a core folder is listed under **Other**.

Open a game and press A to delete the selected save or state. **Delete all** removes every save and state for that game. Each delete asks first, and a state's picture is removed with the state.

**Backup to Google Drive** is the first row. It packs battery saves and savestates and uploads a zip. The default Drive folder is `spruce-saves`. **Backup folders** changes that folder, and can send one platform to its own folder. It also chooses whether the backup is a zip or the save files themselves, whether to add a new copy, replace the last one, or keep the last few, and whether a save that has not changed is skipped. A platform here is one core group in the list, such as Gambatte or FCEUmm. Gambatte holds both Game Boy and Game Boy Color, so those two stay together. The handheld has no browser, so there are two ways to link it. On the handheld, choose **Link on this handheld**, scan the code with your phone, sign in, and type the code from the phone's address bar. Or, on a PC, double-click `link-gdrive.bat`. After either one, the backup runs from the Saves app when the handheld is on Wi-Fi.

## Install

You need Windows, a spruceOS **4.6.0** card, and the card's volume name set to **SPRUCE** (that is the stock name).

1. Download this repo (Code → Download ZIP) and unzip it.
2. Put the SD card in the PC. Use the spruce card, the one labelled SPRUCE.
3. Double-click `install.bat`.
4. Type the numbers of the pieces you want, or `A` for all of them.
5. Read the file list and type `y` to confirm.
6. Eject the card, put it back in the handheld, and reboot if you installed the RetroAchievements piece. The picture pieces apply the next time a game starts.

The installer copies each current file to a backup folder in your user profile (`spruce-patch-backup-<date>`) before it overwrites anything. To undo, copy those files back onto the card in the same folders.

## What it does not touch

- `Saves\spruce\spruce-config.json` (your settings and login)
- `App\RAOfflineProxy\data\` (cache database, logs, and downloaded images)
- RetroArch button remaps
- Themes, ROMs, and BIOS files
