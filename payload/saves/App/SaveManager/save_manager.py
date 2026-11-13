"""Apps-menu list of battery saves and savestates on the spruce card."""

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
    if slot == "0":
        return "State"
    return "State " + slot


def _size(n):
    if n < 1024:
        return "%d B" % n
    if n < 1024 * 1024:
        return "%d KB" % round(n / 1024)
    return "%.1f MB" % (n / (1024 * 1024))


def _when(mtime):
    return time.strftime("%d %b %Y %H:%M", time.localtime(mtime))


class SaveApp:
    def __init__(self, root):
        self.root = root
        self.library = []
        self.screen = "cores"
        self.core_name = None
        self.game_name = None
        self.index = {}

    def loop(self):
        from controller.controller import Controller
        from controller.controller_inputs import ControllerInput
        from views.grid_or_list_entry import GridOrListEntry
        from views.view_creator import ViewCreator
        from views.view_type import ViewType

        self._row_type = GridOrListEntry
        self._views = ViewCreator
        self._view_type = ViewType
        self._buttons = Controller
        self._input = ControllerInput
        view = None
        shown = None
        while True:
            self.library = scan(self.root)
            self._settle()
            key = self._key()
            if view is None or shown != key:
                options = self._options()
                selected_index = self.index.get(key, 0)
                if selected_index >= len(options):
                    selected_index = 0
                view = ViewCreator.create_view(
                    view_type=ViewType.ICON_AND_DESC,
                    top_bar_text=self._title(),
                    options=options,
                    selected_index=selected_index,
                    icon_and_desc_use_image_in_place_of_icon=True,
                )
                shown = key
                Controller.clear_last_input()
            selected = view.get_selection([ControllerInput.A, ControllerInput.B])
            if selected is None or selected.get_input() is None:
                continue
            if selected.get_input() == ControllerInput.B:
                if not self._back():
                    return
                view = None
                continue
            if selected.get_index() is not None:
                self.index[key] = selected.get_index()
            choice = selected.get_selection()
            if choice is not None:
                choice.get_value()()
            view = None

    def _key(self):
        if self.screen == "games":
            return "games:" + (self.core_name or "")
        if self.screen == "files":
            return "files:" + (self.core_name or "") + "\0" + (self.game_name or "")
        return "cores"

    def _settle(self):
        core, game = self._find()
        if self.screen == "files" and game is None:
            self.screen = "games"
            core, game = self._find()
        if self.screen == "games" and core is None:
            self.screen = "cores"
            self.core_name = None

    def _find(self):
        core = None
        for item in self.library:
            if item["name"] == self.core_name:
                core = item
                break
        if core is None:
            return None, None
        for game in core["games"]:
            if game["name"] == self.game_name:
                return core, game
        return core, None

    def _title(self):
        if self.screen == "games":
            return self.core_name or "Saves"
        if self.screen == "files":
            return self.game_name or "Saves"
        return "Saves"

    def _back(self):
        if self.screen == "files":
            self.screen = "games"
            self.game_name = None
            return True
        if self.screen == "games":
            self.screen = "cores"
            self.core_name = None
            return True
        return False

    def _options(self):
        if self.screen == "cores":
            rows = [
                self._row(
                    "Backup to Google Drive",
                    self._backup_description(),
                    self._backup,
                ),
                self._row(
                    "Backup folders",
                    "Choose a Drive folder for each platform.",
                    self._configure_folders,
                ),
            ]
            if not self.library:
                rows.append(self._row(
                    "No saves yet",
                    "Battery saves and savestates show up here.",
                    lambda: None,
                ))
                return rows
            for core in self.library:
                count = len(core["games"])
                noun = "game" if count == 1 else "games"
                rows.append(self._row(
                    core["name"],
                    "%d %s" % (count, noun),
                    lambda name=core["name"]: self._open_core(name),
                ))
            return rows
        core, game = self._find()
        if self.screen == "games":
            if core is None:
                return [self._row("No saves yet", "B goes back.", lambda: None)]
            rows = []
            for item in core["games"]:
                description = _game_summary(item)
                if core["name"] == "Other":
                    description += " Outside a core folder."
                rows.append(self._row(
                    item["name"],
                    description,
                    lambda name=item["name"]: self._open_game(name),
                ))
            return rows
        if game is None:
            return [self._row("Nothing left here", "B goes back.", lambda: None)]
        rows = []
        for item in game["files"]:
            rows.append(self._row(
                item["label"],
                "%s · %s. A deletes it." % (_size(item["size"]), _when(item["mtime"])),
                lambda item=item: self._delete(item),
                item.get("image"),
            ))
        if len(game["files"]) > 1:
            rows.append(self._row(
                "Delete all",
                "A deletes every save and state for this game.",
                self._delete_all,
            ))
        return rows

    def _row(self, text, description, action, image=None):
        return self._row_type(
            primary_text=text,
            image_path=image,
            image_path_selected=image,
            description=description,
            icon=image,
            value=action,
        )

    def _backup_description(self):
        config = load_backup_config()
        if _drive_ready():
            return "Copy saves to %s, unless a platform has its own folder." % config["folder"]
        return "Link it on this handheld, or with link-gdrive.bat on a PC."

    def _backup(self):
        from controller.controller import Controller
        from display.display import Display
        from utils.user_prompt import UserPrompt

        if not _drive_ready():
            if not self._offer_link() or not _drive_ready():
                return
        groups = backup_groups(self.library, load_backup_config())
        if not groups:
            _wait_for_button(["There are no saves to back up."])
            return
        agreed = UserPrompt.prompt_yes_no("Backup", _confirm_lines(groups))
        Controller.clear_input_queue()
        if not agreed:
            return
        Display.display_message_multiline([
            "Backing up to Google Drive.",
            "This can take a minute.",
        ])
        held = False
        try:
            Controller.hold_screensaver(True)
            held = True
        except Exception:
            held = False
        made = []
        try:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            tmp = "/tmp" if os.path.isdir("/tmp") else tempfile.gettempdir()
            total = 0
            sent = []
            failed = None
            for drive_folder, cores in groups:
                dest = os.path.join(tmp, _zip_name(drive_folder, cores, stamp))
                made.append(dest)
                count = write_backup(self.root, dest, cores)
                if count == 0:
                    continue
                total += count
                result = _upload_backup(dest, drive_folder)
                if result is not None:
                    failed = (drive_folder, result)
                    break
                sent.append(drive_folder)
            if total == 0:
                _wait_for_button(["There are no saves to back up."])
            elif failed:
                _wait_for_button([
                    "Backup did not finish.",
                    failed[0],
                    failed[1],
                ])
            else:
                _wait_for_button([
                    "Backed up %d files." % total,
                    "Folders: %s" % ", ".join(sent),
                ])
        finally:
            for dest in made:
                if os.path.isfile(dest):
                    try:
                        os.remove(dest)
                    except OSError:
                        pass
            if held:
                Controller.hold_screensaver(False)

    def _configure_folders(self):
        from controller.controller import Controller
        from controller.controller_inputs import ControllerInput
        from views.view_creator import ViewCreator
        from views.view_type import ViewType

        index = 0
        while True:
            config = load_backup_config()
            rows = [self._row(
                "Default folder",
                config["folder"],
                lambda: self._edit_default(),
            )]
            for core in self.library:
                name = core["name"]
                custom = config["platforms"].get(name)
                rows.append(self._row(
                    name,
                    custom if custom else "Uses %s" % config["folder"],
                    lambda name=name: self._edit_platform(name),
                ))
            view = ViewCreator.create_view(
                view_type=ViewType.ICON_AND_DESC,
                top_bar_text="Backup folders",
                options=rows,
                selected_index=index,
            )
            Controller.clear_last_input()
            selected = view.get_selection([ControllerInput.A, ControllerInput.B])
            if selected is None or selected.get_input() is None:
                continue
            if selected.get_input() == ControllerInput.B:
                return
            if selected.get_index() is not None:
                index = selected.get_index()
            choice = selected.get_selection()
            if choice is not None:
                choice.get_value()()

    def _edit_default(self):
        from display.on_screen_keyboard import OnScreenKeyboard

        config = load_backup_config()
        typed = OnScreenKeyboard().get_input("Default Drive folder", config["folder"])
        if typed is None:
            return
        folder = clean_drive_folder(typed)
        if not folder:
            _wait_for_button(["Type a folder name.", "Blank is not allowed for the default."])
            return
        config["folder"] = folder
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
            "Google Drive",
        )
        if choice != 0:
            return False
        return link_drive.link()

    def _open_core(self, name):
        self.core_name = name
        self.screen = "games"

    def _open_game(self, name):
        self.game_name = name
        self.screen = "files"

    def _delete(self, item):
        from controller.controller import Controller
        from utils.user_prompt import UserPrompt

        agreed = UserPrompt.prompt_yes_no("Delete", [
            item["label"],
            (self.game_name or "") + "?",
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

        _core, game = self._find()
        if game is None:
            return
        agreed = UserPrompt.prompt_yes_no("Delete all", [
            "Delete every save and state for",
            (self.game_name or "") + "?",
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


def _app_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _drive_ready():
    folder = _app_dir()
    return os.path.isfile(os.path.join(folder, "rclone")) and os.path.isfile(os.path.join(folder, "rclone.conf"))


def load_backup_config():
    path = os.path.join(_app_dir(), "backup.json")
    config = {"folder": DEFAULT_DRIVE_FOLDER, "platforms": {}}
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


def _confirm_lines(groups):
    folders = []
    for folder, _cores in groups:
        if folder not in folders:
            folders.append(folder)
    return [
        "Copy the saves to",
        ", ".join(folders),
    ]


def _zip_name(drive_folder, cores, stamp):
    default = load_backup_config()["folder"]
    if len(cores) == 1 and drive_folder != default:
        label = cores[0]
    else:
        label = "spruce-saves"
    safe = re.sub(r"[^\w. -]+", "-", label).strip(" .-") or "spruce-saves"
    return "%s-%s.zip" % (safe, stamp)


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


def _upload_backup(dest, drive_folder):
    """Upload one zip. None on success, otherwise a short reason."""
    folder = _app_dir()
    binary = os.path.join(folder, "rclone")
    conf = os.path.join(folder, "rclone.conf")
    try:
        os.chmod(binary, 0o755)
    except OSError:
        pass
    remote = "gdrive:" + drive_folder.strip("/") + "/" + os.path.basename(dest)
    try:
        proc = subprocess.run(
            [binary, "copyto", dest, remote, "--config", conf, "--timeout", "5m"],
            capture_output=True, text=True, timeout=360,
        )
    except OSError:
        return "The uploader could not start."
    except subprocess.TimeoutExpired:
        return "Google Drive took too long to answer."
    if proc.returncode == 0:
        return None
    detail = ""
    for line in (proc.stderr or "").splitlines():
        line = line.strip()
        if line:
            detail = line
    if not detail:
        return "Google Drive did not accept the backup."
    if len(detail) > 90:
        detail = detail[:90]
    return detail


def _wait_for_button(lines):
    from controller.controller import Controller
    from display.display import Display

    Display.display_message_multiline(lines)
    Controller.get_input()
    Controller.clear_input_queue()


def _game_summary(game):
    labels = [item["label"] for item in game["files"] if item["rank"] < 4]
    if not labels:
        labels = ["thumbnail"]
    shown = ", ".join(labels[:3])
    extra = len(labels) - 3
    if extra > 0:
        shown += " +%d" % extra
    return "%s · %s" % (shown, _when(game["mtime"]))
