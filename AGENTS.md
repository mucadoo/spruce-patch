# Agent instructions

This repo holds optional patches for spruceOS 4.6.0, plus an installer that copies the chosen pieces onto an SD card. The RetroAchievements piece runs on any device that card boots. The picture pieces are for a 640×480 screen and the installer refuses them when the card last booted a different resolution.

## Commits

- Do NOT include co-authoring trailers in commit messages. No `Co-authored-by:` lines, and no other co-author or AI attribution trailers.
- Write short, plain commit messages that describe the change.

## Repo contents

- `features.json` lists the install choices, in menu order. Each `id` is a folder under `payload/`.
- `payload/<id>/` holds only that piece's files, laid out with the same relative paths as the SD card root (for example `App/PyUI/...`).
- `install.ps1` and `install.bat` let the user pick one or more pieces, then back up and copy those files. Keep them working for a normal Windows user who double-clicks `install.bat`.
- `README.md` explains each piece and how to install it.

## Adding a piece

Add a folder under `payload/` and an entry in `features.json`. Do not put files directly in `payload/` outside a feature folder.

If two pieces write the same `.cfg`, keep each piece's own keys in its own file. The installer merges `key = value` lines when both pieces are selected, so one piece must not repeat the other piece's keys.

## Never commit

- `spruce-config.json`, RetroAchievements credentials, or any tokens and passwords.
- `App/RAOfflineProxy/data/` (config, sqlite database, logs, image cache, locks, keys).
- Device-written RetroArch runtime files (`.opt`, `.rmp`, and similar) unless they are an intentional change.
- Theme folders, overlay PNG packs, or other user content. Bezel pieces should be the small config files that point at art already on the card.
- `__pycache__/` and `.pyc` files.
