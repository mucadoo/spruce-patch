# Keep library offline

**Keep library offline** is the RetroAchievements watch. It is separate from **Cache for offline**, which caches games only when you start it.

The watch lives in the proxy service. It keeps running after you leave the menu. Turning it on does not cache anything by itself until you pick that, or until a later pass finds a game that was not there before.

## What you turn on

Settings → RetroAchievements → Keep library offline.

- **Whole library** watches every platform folder under ROMs.
- A platform row watches only that platform.
- Whole library replaces any single platforms you had on. Turning one platform off while the whole library is on leaves every other platform watched.
- Left or right, or A, flips the row. B leaves the menu.

## The choice when you turn a watch on

The menu counts games in the folder you picked that are not cached yet, not already waiting, and not already checked as having no RetroAchievements set.

- **Cache the N games already here** turns the watch on and starts a background cache of that same folder. The progress screen opens. B leaves the screen and the cache keeps going. Open **Background cache** later to see it or stop what is still waiting.
- **Only cache games I add later** turns the watch on and remembers every ROM already in that folder. Those files are not queued. A game you copy in afterwards is picked up on a later pass.
- If that count is zero, the menu does not ask. It watches, and only games added later are cached.
- B on the choice turns nothing on.

The count follows the row you used. Whole library counts the whole library. One platform counts that platform.

## What a pass actually does

The service looks for work about once a minute. A watched folder is due every 30 minutes, and only while you are not playing (about 5 minutes after the last RetroAchievements request from a game). It also waits if a cache you started is still hashing that folder.

A pass lists ROM files from A to Z. It skips `Imgs`, hidden folders, and anything deeper than 12 folders. For each file it has not handled before:

- Already cached, or already waiting in the queue: leave it.
- Already checked, and RetroAchievements has no set for that ROM: leave it.
- Anything else: hash it and add it to the queue. The watch does not download the achievement data itself.

Hashing does not need Wi-Fi. Downloading does. The service caches the queue while the Flip is online, idle, and signed in to RetroAchievements. One 30-minute window caches up to 100 games. The first 20 go out together, then the rest are spaced about 18 seconds apart, so RetroAchievements is not hit in one burst. A game with no matching set does not use that budget. An unsupported ROM version is treated as no match and is not listed under Cached Games.

A file the watch could not read is skipped on later passes. Turn that watch off and on again if you want those files tried again.

Games you add are not instant. They wait for the next pass, then for a free spot in the 100-game window.

## While a watch or a cache is running

Starting another cache asks you to open **Background cache** or to add the new games to the one already running. That includes a watch pass that is still hashing, and games the watch has already queued.

## Turning it off, and clearing the cache

Turning a row off stops that watch and forgets which files it had already seen there. It does not delete games that are already cached.

**Clear offline cache** deletes cached games, icons, the waiting queue, and the watch's memory of files it has seen. Your login and pending awards stay. The watch stays turned on. Because that memory is gone, the next pass queues games that are not cached. Turn the watch off and on again and pick **Only cache games I add later** if you do not want that.
