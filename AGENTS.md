# Agent instructions

This repo holds a patch for spruceOS 4.6.0 (RetroAchievements offline cache menu, watch settings, and related fixes) plus an installer that copies it onto a Miyoo SD card.

## Commits

- Do NOT include co-authoring trailers in commit messages. No `Co-authored-by:` lines, and no other co-author or AI attribution trailers.
- Write short, plain commit messages that describe the change.

## Repo contents

- `payload/` holds only changed files, laid out with the same relative paths as the SD card root (for example `App/PyUI/...`).
- `install.ps1` and `install.bat` install the payload onto the card with a backup. Keep them working for a normal Windows user who double-clicks `install.bat`.
- `README.md` explains installation for end users.

## Never commit

- `spruce-config.json`, RetroAchievements credentials, or any tokens and passwords.
- `App/RAOfflineProxy/data/` (config, sqlite database, logs, image cache, locks, keys).
- Device-written RetroArch runtime files (`.opt`, `.rmp`, and similar) unless they are an intentional change.
- Theme folders or other user content.
