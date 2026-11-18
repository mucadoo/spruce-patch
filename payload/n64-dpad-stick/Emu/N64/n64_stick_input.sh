# The Stick row in the N64 menu. RetroArch only applies input_player1_l_*_btn
# from a core .cfg. The same lines in a .rmp are ignored, so this writes the .cfg.

N64_RA_CONFIG="${N64_RA_CONFIG:-/mnt/SDCARD/RetroArch/.retroarch/config}"

apply_n64_stick_input() {
	[ -n "$EMU_JSON_PATH" ] && [ -f "$EMU_JSON_PATH" ] || return 0

	global="$(jq -r '.menuOptions.stickInput.selected // ""' "$EMU_JSON_PATH" 2>/dev/null)"
	override="$(jq -r --arg game "$GAME" '.menuOptions.stickInput.overrides[$game] // ""' "$EMU_JSON_PATH" 2>/dev/null)"

	case "$global" in
		"Left stick and D-pad"|"Left stick") ;;
		*) return 0 ;;
	esac

	if command -v log_message >/dev/null 2>&1; then
		log_message "N64 stick: ${override:-$global}"
	fi

	cores='Mupen64Plus-Next
Mupen64Plus GLES2
LudicrousN64 2K22 Xtreme Amped
ParaLLEl N64
ParaLLEl N64 Xtreme Amped'

	printf '%s\n' "$cores" | while IFS= read -r name; do
		[ -n "$name" ] || continue
		dir="$N64_RA_CONFIG/$name"
		mkdir -p "$dir" 2>/dev/null || continue
		if [ "$global" = "Left stick and D-pad" ]; then
			_n64_stick_cfg "$dir/$name.cfg" on
		else
			_n64_stick_cfg "$dir/$name.cfg" clear
		fi

		game="${GAME%.*}"
		[ -n "$game" ] || continue
		if [ -z "$override" ] || [ "$override" = "$global" ]; then
			_n64_stick_cfg "$dir/$game.cfg" clear
		elif [ "$override" = "Left stick and D-pad" ]; then
			_n64_stick_cfg "$dir/$game.cfg" on
		elif [ "$override" = "Left stick" ]; then
			_n64_stick_cfg "$dir/$game.cfg" off
		fi
	done
}

_n64_stick_cfg() {
	file="$1"
	want="$2"
	[ -f "$file" ] || [ "$want" != "clear" ] || return 0
	tmp="${file}.stick.tmp"
	if [ -f "$file" ]; then
		grep -v -E '^input_player1_l_[xy]_(minus|plus)_btn[[:space:]]*=' "$file" > "$tmp" || true
	else
		: > "$tmp"
	fi
	if [ "$want" = "on" ] || [ "$want" = "off" ]; then
		[ -s "$tmp" ] && [ -n "$(tail -c 1 "$tmp")" ] && echo >> "$tmp"
		if [ "$want" = "on" ]; then
			value_l=13; value_r=14; value_u=11; value_d=12
		else
			value_l=nul; value_r=nul; value_u=nul; value_d=nul
		fi
		cat >> "$tmp" <<EOF
input_player1_l_x_minus_btn = "$value_l"
input_player1_l_x_plus_btn = "$value_r"
input_player1_l_y_minus_btn = "$value_u"
input_player1_l_y_plus_btn = "$value_d"
EOF
	fi
	mv "$tmp" "$file"
}
