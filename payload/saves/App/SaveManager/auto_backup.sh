#!/bin/sh
# Backs up saves on the interval chosen in the Saves app.
# The menu starts this once. It keeps running while a game is open.
trap '' HUP

APP=/mnt/SDCARD/App/SaveManager
LOG=/mnt/SDCARD/Saves/spruce/save-backup.log
LAST="$APP/last-auto.txt"
PIDFILE=/tmp/save-backup-watchdog.pid

if [ -f "$PIDFILE" ]; then
    old=$(cat "$PIDFILE" 2>/dev/null)
    if [ -n "$old" ] && [ -d "/proc/$old" ]; then
        exit 0
    fi
fi
echo $$ > "$PIDFILE"

if [ -x /mnt/SDCARD/spruce/flip/bin/python3.10 ]; then
    PY=/mnt/SDCARD/spruce/flip/bin/python3.10
elif [ -x /mnt/SDCARD/spruce/bin64/python/bin/python3 ]; then
    PY=/mnt/SDCARD/spruce/bin64/python/bin/python3
elif [ -x /mnt/SDCARD/spruce/bin/python/bin/python3 ]; then
    PY=/mnt/SDCARD/spruce/bin/python/bin/python3
else
    PY=python3
fi

game_running() {
    ps | grep -v grep | grep -E 'retroarch|drastic|PPSSPP|ppsspp' >/dev/null 2>&1
}

wifi_up() {
    ip route show default 2>/dev/null | grep . >/dev/null 2>&1
}

while true; do
    sleep 30
    minutes=$("$PY" "$APP/save_manager.py" --minutes 2>/dev/null)
    case "$minutes" in
        ''|*[!0-9]*) minutes=0 ;;
    esac
    [ "$minutes" -gt 0 ] 2>/dev/null || continue
    [ -f "$APP/rclone" ] || continue
    [ -f "$APP/rclone.conf" ] || continue
    game_running && continue
    wifi_up || continue
    now=$(date +%s 2>/dev/null)
    case "$now" in
        ''|*[!0-9]*) continue ;;
    esac
    last=0
    if [ -f "$LAST" ]; then
        last=$(cat "$LAST" 2>/dev/null)
        case "$last" in
            ''|*[!0-9]*) last=0 ;;
        esac
    fi
    need=$((minutes * 60))
    elapsed=$((now - last))
    [ "$elapsed" -ge "$need" ] || continue
    mkdir -p /mnt/SDCARD/Saves/spruce 2>/dev/null
    echo "---- $(date 2>/dev/null)" >> "$LOG"
    if "$PY" "$APP/save_manager.py" --backup >> "$LOG" 2>&1; then
        echo "$now" > "$LAST"
    fi
done
