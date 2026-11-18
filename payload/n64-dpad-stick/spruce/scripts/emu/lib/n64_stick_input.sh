# Reads the N64 menu's Stick row and rewrites the core remap before RetroArch starts.
# "Left stick and D-pad" binds the D-pad to the N64 stick and keeps the left stick axes.
# "Left stick" takes those D-pad binds back off. The left stick stays on the controller profile.

apply_n64_stick_input() {
	[ -n "$EMU_JSON_PATH" ] && [ -f "$EMU_JSON_PATH" ] || return 0

	mode="$(jq -r --arg game "$GAME" '
		.menuOptions.stickInput as $o
		| if $o == null then ""
		  else ($o.overrides[$game] // $o.selected // "")
		  end' "$EMU_JSON_PATH" 2>/dev/null)"

	case "$mode" in
		"Left stick and D-pad"|"Left stick") ;;
		*) return 0 ;;
	esac

	dst="/mnt/SDCARD/RetroArch/.retroarch/config/remaps"
	[ -d "$dst" ] || return 0
	log_message "N64 stick: $mode"

	for dir in "$dst"/*; do
		[ -d "$dir" ] || continue
		name="$(basename "$dir")"
		case "$name" in
			*"n64"*|*"N64"*|*"Mupen64"*) ;;
			*) continue ;;
		esac
		rmp="${dir}/${name}.rmp"
		[ -f "$rmp" ] || continue
		_n64_set_stick_lines "$rmp" "$mode"
	done
}

_n64_set_stick_lines() {
	rmp="$1"
	mode="$2"
	tmp="${rmp}.stick.tmp"
	grep -v -E '^input_player1_l_[xy]_(minus|plus)_(btn|axis)[[:space:]]*=' "$rmp" > "$tmp" || true
	if [ "$mode" = "Left stick and D-pad" ]; then
		[ -s "$tmp" ] && [ -n "$(tail -c 1 "$tmp")" ] && echo >> "$tmp"
		cat >> "$tmp" <<'EOF'
input_player1_l_x_minus_axis = "-0"
input_player1_l_x_plus_axis = "+0"
input_player1_l_y_minus_axis = "-1"
input_player1_l_y_plus_axis = "+1"
input_player1_l_x_minus_btn = "13"
input_player1_l_x_plus_btn = "14"
input_player1_l_y_minus_btn = "11"
input_player1_l_y_plus_btn = "12"
EOF
	fi
	mv "$tmp" "$rmp"
}
