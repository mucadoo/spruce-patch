# spruce patch

Optional extras for **spruceOS 4.6.0**. The installer asks which pieces you want.

This is an unofficial patch. It is not part of spruceOS.

The patched spruce files stay under the [spruceOS license](https://creativecommons.org/licenses/by-nc/4.0/) (CC BY-NC 4.0, non-commercial). Copyright (c) 2024 SpruceOS, a project by SpruceUI.

## Pieces

**RetroAchievements offline cache**

- **Cache for offline** lets you pick a platform, a folder, or individual games. Games that are already cached are skipped. A game RetroAchievements does not know is marked **No achievements**. A known game whose dump has no set is marked **Unsupported version**. A file that cannot be read is marked **Could not read**. Those are not offered as still to cache.
- **Cache when launched** is on unless you turn it off. Launching a game caches it when it is not cached yet, including its icon and badges. A game that is already cached is left alone. Left or right changes it.
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

**N64**

Stays on LudicrousN64, the fast core spruce already uses, so RetroAchievements still runs. The whole library keeps framebuffer emulation off, high-level RSP, and a one-step CPU overclock. That is the speed setup.

Two games cannot live with that:

- **Paper Mario** runs on Mupen64Plus-Next, not LudicrousN64. LudicrousN64 freezes at Luigi's door on this handheld's ARM CPU, and its slower modes stutter badly. Next runs it with the threaded renderer, the color buffer copy off, and the CPU overclock on for this game only. Its audio latency is 128 ms to smooth out the music. The installer adds one per-game entry to the N64 menu config to send Paper Mario there. The pause menu can open a moment late, and its background may look slightly wrong.
- **Donkey Kong 64** stays on LudicrousN64. It turns the overclock off and copies the color buffer, and also copies the depth buffer. Without the depth copy the picture breaks up. Its stick deadzone is wider, so a resting stick does not swing the camera.

Every other N64 game is unchanged.

**N64 D-pad as stick**

On every N64 core (LudicrousN64, Mupen64Plus-Next, Mupen64Plus GLES2, ParaLLEl N64, and ParaLLEl N64 Xtreme Amped), the left stick drives the N64 stick. **Stick** in the N64 configuration (press X on a game) chooses whether the D-pad does too.

- **Left stick and D-pad** is the default. Up, down, left, and right on the D-pad move the stick, and the left stick keeps doing it. The D-pad still works as a D-pad, so RetroArch's menu still responds to it.
- **Left stick** takes the D-pad off the stick. The left stick is unchanged.

The change applies the next time a game launches. Left or right on the row sets it for every N64 game. A on the row can set it for one game. The N64 launcher (`Emu/N64/stick_launch.sh`) writes the D-pad binds into each N64 core's RetroArch config, and it runs before spruce's own launch script. Spruce recopies its controller layout onto some cores at launch, so the binds are kept out of the remap files.

**Save manager**

**Saves** is in the Apps menu. The home screen lists each console that has saves, with the theme's console icon, the number of games, and the time of the newest save. The console comes from the matching ROM, so Game Boy and Game Boy Color games are listed apart even though Gambatte saves both in one folder. Open a console to see its games with their box art, and open a game to see its battery save, its savestates with their pictures, and the time each was written. A file sitting outside a core folder is marked as a loose file.

Press A on a save or state to delete it. **Delete everything for this game** removes every save and state for that game. Each delete asks first, and a state's picture is removed with the state.

**Back up now** is the first row. It shows when the last backup ran, uploads straight away, and shows progress while it runs. **Backup settings** uses the same controls as the spruce settings: left and right change a value, and A opens a list or the keyboard. It sets the Drive folder (`spruce-saves` by default), **Platform folders** to send one core's saves to their own folder, **Backup as** zip or save files, **Copies to keep** (all, latest only, or the last few), **Only changed saves**, and **Automatic backup** (every 15 minutes, 30 minutes, hour, 6 hours, day, or a number of minutes you type). Off means it only runs when you choose it. The timer starts with the menu, waits until Wi-Fi is up and a game is not running, and keeps going after you launch a game. Reboot once after installing so the timer is running. Platform folders are set per core, so Gambatte's Game Boy and Game Boy Color saves share one folder. The handheld has no browser, so there are two ways to link Google Drive. On the handheld, choose **Link on this handheld**, scan the code with your phone, sign in, and type the code from the phone's address bar. Or, on a PC, double-click `link-gdrive.bat`. After either one, backups run when the handheld is on Wi-Fi.

**Games menu**

Nintendo DS and DSi stay off the games menu when the only file in the folder is spruce's boot menu (`BootMenu.nds` or `BootMenuDSi.nds`). That file is there so the DS launcher has something to open. It is not a game, so it does not put the system on the menu. Add a real game and the system shows up. The installer applies this whenever it runs.

**Display presets**

**Display settings** is a row in the top Settings menu, above Additional settings. It starts with two presets. Press A on one to apply it. The sliders underneath update to match.

- **Default** puts the picture back to the stock Flip values: backlight 10, brightness 7, contrast 10, saturation 14, hue 10.
- **Dimmest** sets the backlight to its lowest step that still lights the panel, brightness to 8, and contrast to 2. Saturation and hue stay where they are. The lamp cannot go lower than that step without switching off.

**E-Reader**

Replaces the stock E-Reader and adds offline English (WordNet 3.1), French, and Portuguese (Wiktionary) dictionaries, picked by the language of each book. Books stay in `Roms/EBOOKS`. Highlights and the reading position stay in the reader's store and are not touched by a later install.

- **Y** selects a word. The D-pad moves the cursor, and holding it repeats. **A** opens **Look up**, **Search book**, **Highlight**, **Underline**, **Strike out** (or **Remove highlight**). **B** or **Y** leaves selection. Every word you look up goes to a word list.
- The book's own type sizes are used. The title and chapter titles are larger than the body, italics and bold are kept, quotes are indented, and preformatted text uses a monospace font. Jpeg, png, and gif pictures are shown.
- **Select** opens the book menu: chapters, bookmarks, next and previous mark, book map, go to a percent, go to a page (Page mode), view pictures (full screen with zoom), jump back, look up a typed word, reading stats, the word list, highlights, and export of highlights and words to a text file. On a footnote link, **A** also offers **Show note**.
- **X** opens settings (theme, font, size, shoulder buttons, progress, a three-place bar with time left, clock and battery, margins, line spacing, justify, indent, paragraph gap, bold text, hyphenation, word spacing, scroll overlap, dictionary choice, screen dim, epub style switch, highlight colors, picture filters, thin chapter bar, cover screen, automatic night theme, auto exit; layout is remembered for each book). **A** shows or hides the progress line. **Menu** quits.
- The book list shows the title and author from each book, how far you got, and **Continue** for the book you read last. **Start** changes the order (name, title, author, series, recent). **Y** opens options: properties, favorites, mark finished, hide finished books, library search with an on-screen keyboard, rename and delete.
- Opens epub, FB2, HTML, Markdown and text files (UTF-8, UTF-16 and Latin-1), and CBZ comic books.

The full guide, including every button, what is saved, and what the dictionary can and cannot look up, is in [spruce-ereader](https://github.com/mucadoo/spruce-ereader). The reader is GPL. The dictionary and hyphenation notices ship with their files.

**Hotkey list**

**Hotkeys** is a row in Settings, above About. It lists the chords spruce is using on this device: brightness, screenshot, volume, sleep, and shut down, then what a tap and a hold of Menu do, then the RetroArch chords. The RetroArch ones use whichever button you picked for the hotkey (Select, Start, or Menu). If that setting is Custom, they are shown as Hotkey plus the other button. Changing a chord in Button Settings and opening Hotkeys again shows the new one. Nothing on this screen changes a setting.

## Install

You need Windows, a spruceOS **4.6.0** card, and the card's volume name set to **SPRUCE** (that is the stock name).

1. Download this repo (Code → Download ZIP) and unzip it.
2. Put the SD card in the PC. Use the spruce card, the one labelled SPRUCE.
3. Double-click `install.bat`.
4. Type the numbers of the pieces you want, or `A` for all of them.
5. Read the file list and type `y` to confirm.
6. Eject the card, put it back in the handheld, and reboot if you installed the RetroAchievements piece. The picture pieces apply the next time a game starts. The E-Reader is ready the next time you open it.

The installer copies each current file to a backup folder in your user profile (`spruce-patch-backup-<date>`) before it overwrites anything. To undo, copy those files back onto the card in the same folders.

## What it does not touch

- `Saves\spruce\spruce-config.json` (your settings and login)
- `App\RAOfflineProxy\data\` (cache database, logs, and downloaded images)
- RetroArch button remaps
- Themes, ROMs, and BIOS files
