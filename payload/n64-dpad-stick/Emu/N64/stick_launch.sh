#!/bin/sh
# Runs before spruce's launcher. $0 stays this file, so the launcher still sees Emu/N64.
export GAME="$(basename "$1")"
export EMU_JSON_PATH="/mnt/SDCARD/Emu/N64/config.json"
. /mnt/SDCARD/Emu/N64/n64_stick_input.sh
apply_n64_stick_input
. /mnt/SDCARD/spruce/scripts/emu/standard_launch.sh
