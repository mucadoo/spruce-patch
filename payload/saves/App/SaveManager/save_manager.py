"""Apps-menu list of battery saves and savestates on the spruce card."""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import zipfile

ROOT = "/mnt/SDCARD/Saves"
DEFAULT_DRIVE_FOLDER = "spruce-saves"
STATE_RE = re.compile(
    r"^(?P<game>.+)\.state(?P<slot>\.auto|\d+)?(?P<thumb>\.png)?$",
    re.IGNORECASE,
)
SAVE_RE = re.compile(
    r"^(?P<game>.+)\.(?P<ext>srm|rtc|sav|eep|fla|flash|dsv)$",
    re.IGNORECASE,
)
SAVE_LABELS = {
    "srm": "Battery save",
    "sav": "Save",
    "eep": "EEPROM",
    "fla": "Flash",
    "flash": "Flash",
    "rtc": "Clock",
    "dsv": "Save",
}


def run():
    SaveApp(ROOT).loop()


def scan(root):
    """Cores, then games, then the files for each game."""
    grouped = {}
    thumbs = []
    for base in (os.path.join(root, "saves"), os.path.join(root, "states")):
        if not os.path.isdir(base):
            continue
        _collect(base, grouped, thumbs)
    for thumb in thumbs:
        key = (thumb["core"], thumb["game"], "state", thumb["slot"])
        item = grouped.get(key)
        if item is None:
            grouped[(thumb["core"], thumb["game"], "thumb", thumb["slot"])] = {
                "label": "State thumbnail",
                "path": thumb["path"],
                "thumb": None,
                "image": thumb["path"],
                "size": thumb["size"],
                "mtime": thumb["mtime"],
                "rank": 4,
                "slot_sort": _slot_sort(thumb["slot"]),
            }
        else:
            item["thumb"] = thumb["path"]
            item["image"] = thumb["path"]

    cores = {}
    for (core, game, _kind, _slot), item in grouped.items():
        cores.setdefault(core, {}).setdefault(game, []).append(item)

    library = []
    for name, games in cores.items():
        game_rows = []
        for game_name, files in games.items():
            files.sort(key=lambda item: (item["rank"], item["slot_sort"], item["label"].casefold()))
            game_rows.append({
                "name": game_name,
                "files": files,
                "mtime": max(item["mtime"] for item in files),
            })
        game_rows.sort(key=lambda game: game["name"].casefold())
        library.append({"name": name, "games": game_rows})
    library.sort(key=lambda core: (core["name"] == "Other", core["name"].casefold()))
    return library


def _collect(base, grouped, thumbs):
    _take(base, "Other", grouped, thumbs)
    try:
        names = os.listdir(base)
    except OSError:
        return
    for name in names:
        if name.startswith("."):
            continue
        path = os.path.join(base, name)
        if os.path.isdir(path):
            _take(path, name, grouped, thumbs)


def _take(folder, core, grouped, thumbs):
    try:
        names = os.listdir(folder)
    except OSError:
        return
    for name in names:
        if name.startswith("."):
            continue
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        try:
            info = os.stat(path)
        except OSError:
            continue
        state = STATE_RE.match(name)
        if state:
            slot = _slot_id(state.group("slot"))
            game = state.group("game")
            if state.group("thumb"):
                thumbs.append({
                    "core": core,
                    "game": game,
                    "slot": slot,
                    "path": path,
                    "size": info.st_size,
                    "mtime": info.st_mtime,
                })
                continue
            grouped[(core, game, "state", slot)] = {
                "label": _state_label(slot),
                "path": path,
                "thumb": None,
                "image": None,
                "size": info.st_size,
                "mtime": info.st_mtime,
                "rank": 3,
                "slot_sort": _slot_sort(slot),
            }
            continue
        save = SAVE_RE.match(name)
        if save:
            ext = save.group("ext").lower()
            grouped[(core, save.group("game"), "save", ext)] = {
                "label": SAVE_LABELS.get(ext, "Save"),
                "path": path,
                "thumb": None,
                "image": None,
                "size": info.st_size,
                "mtime": info.st_mtime,
                "rank": 2 if ext == "rtc" else 0 if ext == "srm" else 1,
                "slot_sort": 0,
            }
            continue
        grouped[(core, name, "file", name)] = {
            "label": name,
            "path": path,
            "thumb": None,
            "image": None,
            "size": info.st_size,
            "mtime": info.st_mtime,
            "rank": 5,
            "slot_sort": 0,
        }


def _slot_id(raw):
    if not raw:
        return "0"
    if raw.startswith("."):
        raw = raw[1:]
    if raw.lower() == "auto":
        return "auto"
    return str(int(raw))


def _slot_sort(slot):
    if slot == "auto":
        return -1
    try:
        return int(slot)
    except (TypeError, ValueError):
        return 0


def _state_label(slot):
    if slot == "auto":
        return "Auto state"
    return "State slot " + slot


def _size(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%d KB" % round(n / 1024)
    return "%.1f MB" % (n / (1024 * 1024))


SYSTEM_NAMES = {
    "ARCADE": "Arcade",
    "ATARI": "Atari 2600",
    "CPS1": "CPS1",
    "CPS2": "CPS2",
    "CPS3": "CPS3",
    "DC": "Dreamcast",
    "FBNEO": "FinalBurn Neo",
    "FC": "NES",
    "FDS": "Famicom Disk System",
    "GB": "Game Boy",
    "GBA": "Game Boy Advance",
    "GBC": "Game Boy Color",
    "GG": "Game Gear",
    "LYNX": "Atari Lynx",
    "MAME2003PLUS": "MAME 2003 Plus",
    "MD": "Mega Drive",
    "MS": "Master System",
    "N64": "Nintendo 64",
    "NDS": "Nintendo DS",
    "NEOGEO": "Neo Geo",
    "NGP": "Neo Geo Pocket",
    "NGPC": "Neo Geo Pocket Color",
    "PCE": "PC Engine",
    "PCECD": "PC Engine CD",
    "PICO8": "PICO-8",
    "POKE": "Pokemon mini",
    "PS": "PlayStation",
    "PSP": "PSP",
    "SATURN": "Saturn",
    "SEGACD": "Sega CD",
    "SFC": "SNES",
    "SGB": "Super Game Boy",
    "THIRTYTWOX": "32X",
    "VB": "Virtual Boy",
    "WS": "WonderSwan",
    "WSC": "WonderSwan Color",
}
KEEP_STEPS = (0, 1, 3, 5, 10)
AUTO_STEPS = (0, 15, 30, 60, 360, 1440)


class RomIndex:
    """Finds the console and box art for a save from the ROM it belongs to."""

    def __init__(self, roms="/mnt/SDCARD/Roms", emu="/mnt/SDCARD/Emu"):
        self.roms = roms
        self.by_name = {}
        self.core_systems = {}
        self.labels = {}
        self._art = {}
        for system in _list_dirs(emu):
            config = _read_json(os.path.join(emu, system, "config.json"))
            if not isinstance(config, dict):
                continue
            label = config.get("label")
            if isinstance(label, str) and label.strip():
                self.labels[system] = label.strip()
            emulator = (config.get("menuOptions") or {}).get("Emulator") or {}
            for core in emulator.get("options") or []:
                if isinstance(core, str):
                    self.core_systems.setdefault(_norm(core), []).append(system)
        for system in _list_dirs(roms):
            try:
                names = os.listdir(os.path.join(roms, system))
            except OSError:
                continue
            for name in names:
                if name.startswith(".") or "." not in name:
                    continue
                base = os.path.splitext(name)[0]
                self.by_name.setdefault(base.casefold(), []).append(system)

    def system_for(self, core, game):
        found = self.by_name.get(game.casefold(), [])
        known = self.core_systems.get(_norm(core), [])
        for system in found:
            if system in known:
                return system
        if found:
            return found[0]
        if len(known) == 1:
            return known[0]
        return None

    def label(self, system):
        return SYSTEM_NAMES.get(system) or self.labels.get(system) or system

    def art(self, system, game):
        if not system:
            return None
        key = (system, game)
        if key not in self._art:
            self._art[key] = None
            for ext in (".qoi", ".png"):
                path = os.path.join(self.roms, system, "Imgs", game + ext)
                if os.path.isfile(path):
                    self._art[key] = path
                    break
        return self._art[key]


def _list_dirs(path):
    try:
        return sorted(name for name in os.listdir(path)
                      if not name.startswith(".") and os.path.isdir(os.path.join(path, name)))
    except OSError:
        return []


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return None


def _norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def clean_title(name):
    cleaned = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", name).strip()
    return cleaned or name


def group_by_system(library, roms):
    """Consoles, each with its games. A game keeps the core folder its files are in."""
    systems = {}
    for core in library:
        for game in core["games"]:
            system = None if core["name"] == "Other" else roms.system_for(core["name"], game["name"])
            if system is None and core["name"] == "Other":
                system = roms.system_for("", game["name"])
            if system:
                key, label = system, roms.label(system)
            elif core["name"] == "Other":
                key, label = "\0other", "Other"
            else:
                key, label = "\0core:" + core["name"], core["name"]
            entry = systems.setdefault(key, {"key": key, "label": label, "system": system, "games": []})
            entry["games"].append({
                "id": (core["name"], game["name"]),
                "core": core["name"],
                "name": game["name"],
                "title": clean_title(game["name"]),
                "files": game["files"],
                "mtime": game["mtime"],
                "art": roms.art(system, game["name"]),
                "loose": core["name"] == "Other",
            })
    for entry in systems.values():
        titles = {}
        for game in entry["games"]:
            titles.setdefault(game["title"].casefold(), []).append(game)
        for same in titles.values():
            if len(same) > 1:
                by_core = len({g["core"] for g in same}) == len(same)
                for game in same:
                    tag = "loose file" if game["loose"] else game["core"]
                    game["title"] = "%s (%s)" % (game["title"], tag) if by_core else game["name"]
        entry["games"].sort(key=lambda game: game["title"].casefold())
        entry["mtime"] = max(game["mtime"] for game in entry["games"])
    return sorted(systems.values(), key=lambda entry: (entry["key"] == "\0other", entry["label"].casefold()))


class SaveApp:
    def __init__(self, root):
        self.root = root
        self.library = []
        self.systems = []
        self.screen = "home"
        self.system_key = None
        self.game_id = None
        self.index = {}
        self.roms = None

    def loop(self):
        from controller.controller import Controller
        from controller.controller_inputs import ControllerInput
        from views.grid_or_list_entry import GridOrListEntry
        from views.view_creator import ViewCreator
        from views.view_type import ViewType

        self._row_type = GridOrListEntry
        self.roms = RomIndex()
        while True:
            self.library = scan(self.root)
            self.systems = group_by_system(self.library, self.roms)
            self._settle()
            key = self._key()
            options = self._options()
            selected_index = min(self.index.get(key, 0), max(len(options) - 1, 0))
            view_type = ViewType.ICON_AND_DESC if self.screen == "home" else ViewType.TEXT_AND_IMAGE
            view = ViewCreator.create_view(
                view_type=view_type,
                top_bar_text=self._title(),
                options=options,
                selected_index=selected_index,
            )
            Controller.clear_last_input()
            selected = None
            while selected is None or selected.get_input() is None:
                selected = view.get_selection([ControllerInput.A, ControllerInput.B])
            if selected.get_input() == ControllerInput.B:
                if not self._back():
                    return
                continue
            if selected.get_index() is not None:
                self.index[key] = selected.get_index()
            choice = selected.get_selection()
            if choice is not None:
                choice.get_value()()

    def _key(self):
        if self.screen == "system":
            return "system:" + (self.system_key or "")
        if self.screen == "game":
            return "game:%s\0%s" % (self.system_key, self.game_id)
        return "home"

    def _settle(self):
        system, game = self._find()
        if self.screen == "game" and game is None:
            self.screen = "system"
        if self.screen == "system" and system is None:
            self.screen = "home"
            self.system_key = None

    def _find(self):
        for system in self.systems:
            if system["key"] != self.system_key:
                continue
            for game in system["games"]:
                if game["id"] == self.game_id:
                    return system, game
            return system, None
        return None, None

    def _title(self):
        system, game = self._find()
        if self.screen == "game" and game is not None:
            return game["title"]
        if self.screen in ("system", "game") and system is not None:
            return system["label"]
        return "Saves"

    def _back(self):
        if self.screen == "game":
            self.screen = "system"
            return True
        if self.screen == "system":
            self.screen = "home"
            return True
        return False

    def _options(self):
        if self.screen == "system":
            return self._game_rows()
        if self.screen == "game":
            return self._file_rows()
        return self._home_rows()

    def _home_rows(self):
        from themes.theme import Theme

        config = load_backup_config()
        rows = [
            self._row("Back up now", self._backup_status(config), self._backup,
                      icon=_theme_icon(Theme, "backup") or _app_file("cloud.png")),
            self._row("Backup settings", self._settings_summary(config), self._settings,
                      icon=_app_file("settings.png")),
        ]
        if not self.systems:
            rows.append(self._row("No saves yet", "Play a game and save. It shows up here.",
                                  lambda: None, icon=_app_file("saves.png")))
            return rows
        for system in self.systems:
            count = len(system["games"])
            icon = None
            if system["system"]:
                icon = _theme_icon(Theme, system["system"].lower(), system=True)
            rows.append(self._row(
                system["label"],
                "%d %s · %s" % (count, "game" if count == 1 else "games", _day(system["mtime"])),
                lambda key=system["key"]: self._open_system(key),
                icon=icon or _app_file("saves.png"),
            ))
        return rows

    def _game_rows(self):
        system, _game = self._find()
        rows = []
        for game in system["games"] if system else []:
            image = game["art"] or _newest_thumb(game)
            rows.append(self._row(
                game["title"],
                None,
                lambda game_id=game["id"]: self._open_game(game_id),
                image=image,
            ))
        return rows

    def _file_rows(self):
        _system, game = self._find()
        rows = []
        if game is None:
            return rows
        for item in game["files"]:
            if item["rank"] == 4:
                continue
            text = "%s · %s" % (item["label"], _day(item["mtime"]))
            if item["rank"] != 3:
                text = "%s · %s · %s" % (item["label"], _size(item["size"]), _day(item["mtime"]))
            rows.append(self._row(
                text,
                None,
                lambda item=item: self._delete(item),
                image=item.get("image") or game["art"],
            ))
        for item in game["files"]:
            if item["rank"] == 4:
                rows.append(self._row(
                    "Picture without a state · %s" % _day(item["mtime"]),
                    None,
                    lambda item=item: self._delete(item),
                    image=item["path"],
                ))
        rows.append(self._row(
            "Delete everything for this game",
            None,
            self._delete_all,
            image=game["art"] or _newest_thumb(game),
        ))
        return rows

    def _row(self, text, description, action, image=None, icon=None, value_text=None):
        return self._row_type(
            primary_text=text,
            value_text=value_text,
            image_path=image,
            image_path_selected=image,
            description=description,
            icon=icon,
            value=action,
        )

    def _backup_status(self, config):
        if not _drive_ready():
            return "Google Drive is not linked. A links it."
        last = _last_backup()
        parts = ["Last backup " + (_ago(last) if last else "never")]
        if config["autoMinutes"]:
            parts.append("auto " + _auto_text(config["autoMinutes"]).lower())
        return " · ".join(parts)

    def _settings_summary(self, config):
        parts = [
            config["folder"],
            "zip" if config["zip"] else "save files",
            _keep_short(config["keep"]).lower(),
        ]
        return " · ".join(parts)

    def _open_system(self, key):
        self.system_key = key
        self.screen = "system"

    def _open_game(self, game_id):
        self.game_id = game_id
        self.screen = "game"

    def _backup(self):
        from controller.controller import Controller
        from display.display import Display

        if not _drive_ready():
            if not self._offer_link() or not _drive_ready():
                return
        if not self.library:
            _wait_for_button(["There are no saves to back up yet."])
            return

        def progress(number, total, folder):
            lines = ["Backing up to Google Drive"]
            if total > 1:
                lines.append("Folder %d of %d: %s" % (number, total, folder))
            else:
                lines.append(folder)
            lines.append("Keep Wi-Fi on. This can take a minute.")
            Display.display_message_multiline(lines)

        progress(1, 1, load_backup_config()["folder"])
        held = False
        try:
            Controller.hold_screensaver(True)
            held = True
        except Exception:
            held = False
        try:
            _ok, lines = perform_backup(self.root, progress)
            _wait_for_button(lines)
        finally:
            if held:
                Controller.hold_screensaver(False)

    def _settings(self):
        from controller.controller import Controller
        from controller.controller_inputs import ControllerInput
        from views.view_creator import ViewCreator
        from views.view_type import ViewType

        inputs = [ControllerInput.A, ControllerInput.DPAD_LEFT, ControllerInput.DPAD_RIGHT]
        index = 0
        while True:
            config = load_backup_config()
            linked = _drive_ready()
            own = len(config["platforms"])
            rows = [
                self._row("Google Drive", None,
                          lambda button: self._link_row(button),
                          value_text="Linked" if linked else "Link now"),
                self._row("Drive folder", None,
                          lambda button: button == ControllerInput.A and self._edit_default(),
                          value_text=config["folder"]),
                self._row("Platform folders", None,
                          lambda button: button == ControllerInput.A and self._platform_folders(),
                          value_text="%d own" % own if own else "All in one"),
                self._row("Backup as", None,
                          lambda button: self._toggle("zip"),
                          value_text=_arrows("Zip" if config["zip"] else "Save files")),
                self._row("Copies to keep", None,
                          lambda button: self._step(button, "keep", KEEP_STEPS, self._edit_versions),
                          value_text=_arrows(_keep_short(config["keep"]))),
                self._row("Only changed saves", None,
                          lambda button: self._toggle("skipUnchanged"),
                          value_text=_arrows("On" if config["skipUnchanged"] else "Off")),
                self._row("Automatic backup", None,
                          lambda button: self._step(button, "autoMinutes", AUTO_STEPS, self._edit_auto),
                          value_text=_arrows(_auto_text(config["autoMinutes"]))),
            ]
            view = ViewCreator.create_view(
                view_type=ViewType.ICON_AND_DESC,
                top_bar_text="Backup settings",
                options=rows,
                selected_index=index,
            )
            Controller.clear_last_input()
            selected = None
            while selected is None or selected.get_input() is None:
                selected = view.get_selection(inputs + [ControllerInput.B])
            if selected.get_input() == ControllerInput.B:
                return
            if selected.get_index() is not None:
                index = selected.get_index()
            choice = selected.get_selection()
            if choice is not None:
                choice.get_value()(selected.get_input())

    def _link_row(self, button):
        from controller.controller_inputs import ControllerInput

        if button != ControllerInput.A:
            return
        if _drive_ready():
            _wait_for_button(["Google Drive is linked.", "Backups go to the folders set here."])
            return
        self._offer_link()

    def _step(self, button, key, steps, chooser):
        from controller.controller_inputs import ControllerInput

        if button == ControllerInput.A:
            chooser()
            return
        config = load_backup_config()
        values = sorted(set(steps) | {config[key]})
        position = values.index(config[key])
        position += 1 if button == ControllerInput.DPAD_RIGHT else -1
        config[key] = values[position % len(values)]
        save_backup_config(config)

    def _platform_folders(self):
        from controller.controller import Controller
        from controller.controller_inputs import ControllerInput
        from views.view_creator import ViewCreator
        from views.view_type import ViewType

        index = 0
        while True:
            config = load_backup_config()
            names = [core["name"] for core in self.library]
            for name in config["platforms"]:
                if name not in names:
                    names.append(name)
            if not names:
                _wait_for_button(["There are no saves yet.", "Platforms show up after the first save."])
                return
            rows = []
            for name in names:
                rows.append(self._row(
                    self._core_label(name),
                    None,
                    lambda name=name: self._edit_platform(name),
                    value_text=config["platforms"].get(name) or "Drive folder",
                ))
            view = ViewCreator.create_view(
                view_type=ViewType.ICON_AND_DESC,
                top_bar_text="Platform folders",
                options=rows,
                selected_index=min(index, len(rows) - 1),
            )
            Controller.clear_last_input()
            selected = None
            while selected is None or selected.get_input() is None:
                selected = view.get_selection([ControllerInput.A, ControllerInput.B])
            if selected.get_input() == ControllerInput.B:
                return
            if selected.get_index() is not None:
                index = selected.get_index()
            choice = selected.get_selection()
            if choice is not None:
                choice.get_value()()

    def _core_label(self, core):
        if core == "Other":
            return "Other (outside a core folder)"
        systems = []
        for system in self.systems:
            for game in system["games"]:
                if game["core"] == core and system["system"] and system["label"] not in systems:
                    systems.append(system["label"])
        if systems:
            return "%s (%s)" % (core, ", ".join(systems))
        return core

    def _edit_default(self):
        from display.on_screen_keyboard import OnScreenKeyboard

        config = load_backup_config()
        typed = OnScreenKeyboard().get_input("Drive folder", config["folder"])
        if typed is None:
            return
        folder = clean_drive_folder(typed)
        if not folder:
            _wait_for_button(["Type a folder name.", "This one cannot be blank."])
            return
        config["folder"] = folder
        save_backup_config(config)

    def _toggle(self, key):
        config = load_backup_config()
        config[key] = not config[key]
        save_backup_config(config)

    def _edit_versions(self):
        from display.on_screen_keyboard import OnScreenKeyboard
        from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu

        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [
                "All. Add a new copy every time",
                "Latest only. Replace the last copy",
                "Last 3",
                "Last 5",
                "Last 10",
                "Type a number",
            ],
            "Copies to keep",
        )
        if choice is None:
            return
        config = load_backup_config()
        if choice == 5:
            typed = OnScreenKeyboard().get_input("How many to keep", str(config["keep"] or ""))
            if typed is None:
                return
            try:
                number = int(typed.strip())
            except ValueError:
                number = -1
            if number < 0 or number > 50:
                _wait_for_button(["Type a number from 0 to 50.", "0 keeps all. 1 keeps the latest only."])
                return
            config["keep"] = number
        else:
            config["keep"] = KEEP_STEPS[choice]
        save_backup_config(config)

    def _edit_auto(self):
        from display.on_screen_keyboard import OnScreenKeyboard
        from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu

        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [
                "Off",
                "Every 15 minutes",
                "Every 30 minutes",
                "Every hour",
                "Every 6 hours",
                "Every day",
                "Type minutes",
            ],
            "Automatic backup",
        )
        if choice is None:
            return
        config = load_backup_config()
        if choice == 6:
            typed = OnScreenKeyboard().get_input("Minutes between backups", str(config["autoMinutes"] or ""))
            if typed is None:
                return
            try:
                number = int(typed.strip())
            except ValueError:
                number = -1
            if number < 0 or number > 10080:
                _wait_for_button(["Type a number from 0 to 10080.", "0 turns automatic backup off."])
                return
            config["autoMinutes"] = number
        else:
            config["autoMinutes"] = AUTO_STEPS[choice]
        save_backup_config(config)

    def _edit_platform(self, name):
        from display.on_screen_keyboard import OnScreenKeyboard

        config = load_backup_config()
        current = config["platforms"].get(name, "")
        typed = OnScreenKeyboard().get_input("Folder for " + name, current)
        if typed is None:
            return
        folder = clean_drive_folder(typed)
        if folder is None:
            _wait_for_button(["That folder name cannot be used."])
            return
        if not folder:
            config["platforms"].pop(name, None)
        else:
            config["platforms"][name] = folder
        save_backup_config(config)

    def _offer_link(self):
        from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu
        import link_drive

        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            ["Link on this handheld", "Not now"],
            "Link Google Drive",
        )
        if choice != 0:
            return False
        return link_drive.link()

    def _delete(self, item):
        from controller.controller import Controller
        from utils.user_prompt import UserPrompt

        _system, game = self._find()
        title = game["title"] if game else ""
        agreed = UserPrompt.prompt_yes_no("Delete", [
            "Delete %s" % item["label"].lower(),
            "of %s?" % title,
            "This cannot be undone.",
        ])
        Controller.clear_input_queue()
        if not agreed:
            return
        self._remove(item["path"])
        if item.get("thumb"):
            self._remove(item["thumb"])

    def _delete_all(self):
        from controller.controller import Controller
        from utils.user_prompt import UserPrompt

        _system, game = self._find()
        if game is None:
            return
        agreed = UserPrompt.prompt_yes_no("Delete everything", [
            "Delete every save and state of",
            "%s?" % game["title"],
            "This cannot be undone.",
        ])
        Controller.clear_input_queue()
        if not agreed:
            return
        for item in game["files"]:
            self._remove(item["path"])
            if item.get("thumb"):
                self._remove(item["thumb"])

    def _remove(self, path):
        from display.display import Display

        root = os.path.realpath(self.root)
        target = os.path.realpath(path)
        if target != root and not target.startswith(root + os.sep):
            Display.display_message("That file is outside the save folders.", 2000)
            return
        try:
            os.remove(target)
        except OSError:
            Display.display_message("Could not delete that file.", 2000)


def _theme_icon(theme, name, system=False):
    try:
        path = theme.get_system_icon(name) if system else theme.get_app_icon(name)
    except Exception:
        return None
    return path if path and os.path.isfile(path) else None


def _app_file(name):
    path = os.path.join(_app_dir(), name)
    return path if os.path.isfile(path) else None


def _newest_thumb(game):
    best = None
    for item in game["files"]:
        image = item.get("image")
        if image and (best is None or item["mtime"] > best[0]):
            best = (item["mtime"], image)
    return best[1] if best else None


def _arrows(text):
    return "<  %s  >" % text


def _keep_short(keep):
    try:
        keep = int(keep)
    except (TypeError, ValueError):
        keep = 0
    if keep <= 0:
        return "All"
    if keep == 1:
        return "Latest only"
    return "Last %d" % keep


def _day(mtime):
    moment = time.localtime(mtime)
    today = time.localtime()
    clock = time.strftime("%H:%M", moment)
    if moment.tm_year == today.tm_year and moment.tm_yday == today.tm_yday:
        return "Today " + clock
    yesterday = time.localtime(time.time() - 86400)
    if moment.tm_year == yesterday.tm_year and moment.tm_yday == yesterday.tm_yday:
        return "Yesterday " + clock
    if moment.tm_year == today.tm_year:
        return time.strftime("%d %b ", moment).lstrip("0") + clock
    return time.strftime("%d %b %Y", moment).lstrip("0")


def _ago(stamp):
    seconds = max(0, time.time() - stamp)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return "%d min ago" % (seconds // 60)
    if seconds < 86400:
        hours = int(seconds // 3600)
        return "1 hour ago" if hours == 1 else "%d hours ago" % hours
    return _day(stamp)


def _last_backup():
    try:
        with open(os.path.join(_app_dir(), "last-backup.txt"), encoding="utf-8") as handle:
            return float(handle.read().strip())
    except (OSError, ValueError):
        return 0


def _mark_backup():
    try:
        with open(os.path.join(_app_dir(), "last-backup.txt"), "w", encoding="utf-8") as handle:
            handle.write("%d\n" % time.time())
    except OSError:
        pass


def _app_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _drive_ready():
    folder = _app_dir()
    return os.path.isfile(os.path.join(folder, "rclone")) and os.path.isfile(os.path.join(folder, "rclone.conf"))


def load_backup_config():
    path = os.path.join(_app_dir(), "backup.json")
    config = {
        "folder": DEFAULT_DRIVE_FOLDER,
        "platforms": {},
        "zip": True,
        "keep": 0,
        "skipUnchanged": True,
        "autoMinutes": 0,
    }
    try:
        with open(path, encoding="utf-8") as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        return config
    if not isinstance(found, dict):
        return config
    folder = clean_drive_folder(found.get("folder") if isinstance(found.get("folder"), str) else "")
    if folder:
        config["folder"] = folder
    platforms = found.get("platforms")
    if isinstance(platforms, dict):
        for name, dest in platforms.items():
            cleaned = clean_drive_folder(dest if isinstance(dest, str) else "")
            if isinstance(name, str) and cleaned:
                config["platforms"][name] = cleaned
    if "zip" in found:
        config["zip"] = bool(found.get("zip"))
    keep = found.get("keep", 0)
    if isinstance(keep, int) and 0 <= keep <= 50:
        config["keep"] = keep
    if "skipUnchanged" in found:
        config["skipUnchanged"] = bool(found.get("skipUnchanged"))
    minutes = found.get("autoMinutes", 0)
    if isinstance(minutes, int) and 0 <= minutes <= 10080:
        config["autoMinutes"] = minutes
    return config


def save_backup_config(config):
    path = os.path.join(_app_dir(), "backup.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")


def clean_drive_folder(text):
    """A Drive folder path, '' if blank, or None if the text cannot be used."""
    text = (text or "").strip().replace("\\", "/").strip("/")
    if not text:
        return ""
    parts = []
    for part in text.split("/"):
        part = part.strip()
        if not part or part in (".", "..") or any(char in part for char in "\n\r\t"):
            return None
        parts.append(part)
    return "/".join(parts)


def backup_groups(library, config):
    """(Drive folder, core names) pairs. Cores without their own folder share the default."""
    default = config["folder"]
    rest = []
    own = {}
    seen = set()
    for core in library:
        name = core["name"]
        if name in seen:
            continue
        seen.add(name)
        custom = config["platforms"].get(name)
        if custom and custom != default:
            own.setdefault(custom, []).append(name)
        else:
            rest.append(name)
    groups = []
    if rest:
        groups.append((default, rest))
    for folder, names in own.items():
        groups.append((folder, names))
    return groups


def _archive_label(drive_folder, cores):
    default = load_backup_config()["folder"]
    label = cores[0] if len(cores) == 1 and drive_folder != default else "spruce-saves"
    return re.sub(r"[^\w. -]+", "-", label).strip(" .-") or "spruce-saves"


def _file_core(rel):
    parts = rel.split("/")
    if len(parts) >= 3:
        return parts[1]
    if len(parts) == 2:
        return "Other"
    return ""


def write_backup(root, dest, cores=None):
    """Zip battery saves and savestates. cores limits the zip to those platforms."""
    wanted = None if cores is None else set(cores)
    count = 0
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for folder in ("saves", "states"):
            base = os.path.join(root, folder)
            if not os.path.isdir(base):
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [name for name in dirnames if not name.startswith(".")]
                for filename in filenames:
                    if filename.startswith("."):
                        continue
                    full = os.path.join(dirpath, filename)
                    rel = os.path.relpath(full, root).replace("\\", "/")
                    if wanted is not None and _file_core(rel) not in wanted:
                        continue
                    try:
                        archive.write(full, rel)
                    except OSError:
                        continue
                    count += 1
    return count


def load_seen():
    path = os.path.join(_app_dir(), "backup-seen.json")
    try:
        with open(path, encoding="utf-8") as handle:
            found = json.load(handle)
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def save_seen(seen):
    path = os.path.join(_app_dir(), "backup-seen.json")
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(seen, handle, indent=2)
        handle.write("\n")


def _md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(root, cores):
    wanted = set(cores)
    for folder in ("saves", "states"):
        base = os.path.join(root, folder)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]
            for filename in filenames:
                if filename.startswith(".") or ".backup-" in filename:
                    continue
                full = os.path.join(dirpath, filename)
                rel = os.path.relpath(full, root).replace("\\", "/")
                if _file_core(rel) in wanted:
                    yield full, rel


def _group_digest(root, cores):
    digest = hashlib.md5()
    for _full, rel in sorted(_iter_files(root, cores), key=lambda item: item[1]):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_md5(_full).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def _rclone(args):
    folder = _app_dir()
    binary = os.path.join(folder, "rclone")
    conf = os.path.join(folder, "rclone.conf")
    try:
        os.chmod(binary, 0o755)
    except OSError:
        pass
    try:
        proc = subprocess.run(
            [binary, *args, "--config", conf, "--timeout", "2m"],
            capture_output=True, text=True, timeout=180,
        )
    except OSError:
        return 1, "", "The uploader could not start."
    except subprocess.TimeoutExpired:
        return 1, "", "Google Drive took too long to answer."
    detail = ""
    for line in (proc.stderr or "").splitlines():
        if line.strip():
            detail = line.strip()
    if len(detail) > 90:
        detail = detail[:90]
    return proc.returncode, proc.stdout or "", detail


def _upload_path(local, remote_path):
    code, _out, detail = _rclone(["copyto", local, "gdrive:" + remote_path.lstrip("/")])
    if code == 0:
        return None
    return detail or "Google Drive did not accept the backup."


def _remote_names(parent, listed):
    if parent in listed:
        return listed[parent]
    code, out, _detail = _rclone(["lsf", "gdrive:" + parent, "--files-only"])
    names = [line.strip() for line in out.splitlines() if line.strip()] if code == 0 else []
    listed[parent] = names
    return names


def _drop_named(parent, names, matching, keep):
    extra = matching[:max(0, len(matching) - keep)]
    for name in extra:
        _rclone(["deletefile", "gdrive:" + parent + "/" + name])
        if name in names:
            names.remove(name)


def _send_zip(root, drive_folder, cores, config, stamp, seen, tmp):
    digest = _group_digest(root, cores)
    key = "zip\0%s\0%s" % (drive_folder, "\0".join(sorted(cores)))
    if config["skipUnchanged"] and seen.get(key) == digest:
        return 0, 1, None, None
    label = _archive_label(drive_folder, cores)
    keep = int(config["keep"])
    name = label + ".zip" if keep == 1 else "%s-%s.zip" % (label, stamp)
    dest = os.path.join(tmp, name)
    count = write_backup(root, dest, cores)
    if count == 0:
        return 0, 0, None, dest
    result = _upload_path(dest, drive_folder.strip("/") + "/" + name)
    if result is not None:
        return 0, 0, result, dest
    if keep > 1:
        names = _remote_names(drive_folder.strip("/"), {})
        prefix = label + "-"
        old = sorted(item for item in names if item.startswith(prefix) and item.endswith(".zip"))
        _drop_named(drive_folder.strip("/"), names, old, keep)
    seen[key] = digest
    return count, 0, None, dest


def _send_files(root, drive_folder, cores, config, stamp, seen, listed):
    uploaded = 0
    skipped = 0
    keep = int(config["keep"])
    for full, rel in _iter_files(root, cores):
        remote = drive_folder.strip("/") + "/" + rel
        try:
            digest = _md5(full)
        except OSError:
            continue
        if config["skipUnchanged"] and seen.get(remote) == digest:
            skipped += 1
            continue
        parent, base = remote.rsplit("/", 1)
        if keep != 1:
            names = _remote_names(parent, listed)
            if base in names:
                history = "%s.backup-%s" % (base, stamp)
                code, _out, detail = _rclone([
                    "copyto",
                    "gdrive:" + remote,
                    "gdrive:" + parent + "/" + history,
                ])
                if code != 0:
                    return uploaded, skipped, detail or "Could not keep the previous save."
                names.append(history)
                if keep > 1:
                    old = sorted(item for item in names if item.startswith(base + ".backup-"))
                    _drop_named(parent, names, old, keep - 1)
        result = _upload_path(full, remote)
        if result is not None:
            return uploaded, skipped, result
        seen[remote] = digest
        uploaded += 1
        names = listed.get(parent)
        if names is not None and base not in names:
            names.append(base)
    return uploaded, skipped, None


def perform_backup(root, progress=None):
    """Upload saves with the saved settings. Returns (ok, lines)."""
    if not _drive_ready():
        return False, ["Google Drive is not linked yet."]
    if not _acquire_lock():
        return False, ["A backup is already running."]
    made = []
    try:
        config = load_backup_config()
        groups = backup_groups(scan(root), config)
        if not groups:
            return True, ["There are no saves to back up."]
        stamp = time.strftime("%Y%m%d-%H%M%S")
        tmp = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
        seen = load_seen()
        listed = {}
        total = 0
        unchanged = 0
        sent = []
        for number, (drive_folder, cores) in enumerate(groups, 1):
            if progress is not None:
                progress(number, len(groups), drive_folder)
            if config["zip"]:
                uploaded, skipped, result, dest = _send_zip(
                    root, drive_folder, cores, config, stamp, seen, tmp)
                if dest:
                    made.append(dest)
            else:
                uploaded, skipped, result = _send_files(
                    root, drive_folder, cores, config, stamp, seen, listed)
            save_seen(seen)
            unchanged += skipped
            if result is not None:
                return False, ["Backup did not finish.", drive_folder, result]
            total += uploaded
            if uploaded:
                sent.append(drive_folder)
        _mark_backup()
        if total == 0:
            return True, ["Backup is up to date.", "No save has changed since the last one."]
        lines = ["Backed up %d files." % total]
        if unchanged and config["zip"]:
            lines.append("Unchanged folders were left as they are.")
        elif unchanged:
            lines.append("%d had not changed." % unchanged)
        if sent:
            lines.append("Folders: %s" % ", ".join(sent))
        return True, lines
    finally:
        for dest in made:
            if dest and os.path.isfile(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
        _release_lock()


def _acquire_lock():
    if not os.path.isdir("/tmp"):
        return True
    try:
        os.mkdir("/tmp/save-backup.lock")
        return True
    except OSError:
        return False


def _release_lock():
    try:
        os.rmdir("/tmp/save-backup.lock")
    except OSError:
        pass


def _auto_text(minutes):
    try:
        minutes = int(minutes)
    except (TypeError, ValueError):
        minutes = 0
    if minutes <= 0:
        return "Off"
    if minutes % 1440 == 0:
        days = minutes // 1440
        return "Every day" if days == 1 else "Every %d days" % days
    if minutes % 60 == 0:
        hours = minutes // 60
        return "Every hour" if hours == 1 else "Every %d hours" % hours
    return "Every %d minutes" % minutes


def _wait_for_button(lines):
    from controller.controller import Controller
    from display.display import Display

    Display.display_message_multiline(lines)
    Controller.get_input()
    Controller.clear_input_queue()


def main(argv):
    if "--minutes" in argv:
        print(load_backup_config()["autoMinutes"])
        return 0
    if "--backup" in argv:
        ok, lines = perform_backup(ROOT)
        for line in lines:
            print(line)
        return 0 if ok else 1
    run()
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv))
