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
        config = load_backup_config()
        groups = backup_groups(self.library, config)
        if not groups:
            _wait_for_button(["There are no saves to back up."])
            return
        agreed = UserPrompt.prompt_yes_no("Backup", _confirm_lines(groups, config))
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
            seen = load_seen()
            listed = {}
            total = 0
            unchanged = 0
            sent = []
            failed = None
            for drive_folder, cores in groups:
                if config["zip"]:
                    uploaded, skipped, result, dest = _send_zip(
                        self.root, drive_folder, cores, config, stamp, seen, tmp)
                    if dest:
                        made.append(dest)
                else:
                    uploaded, skipped, result = _send_files(
                        self.root, drive_folder, cores, config, stamp, seen, listed)
                save_seen(seen)
                unchanged += skipped
                if result is not None:
                    failed = (drive_folder, result)
                    break
                total += uploaded
                if uploaded:
                    sent.append(drive_folder)
            if failed:
                _wait_for_button(["Backup did not finish.", failed[0], failed[1]])
            elif total == 0:
                _wait_for_button(["No save has changed."])
            else:
                lines = ["Backed up %d files." % total]
                if unchanged and config["zip"]:
                    lines.append("Unchanged folders were left as they are.")
                elif unchanged:
                    lines.append("%d had not changed." % unchanged)
                if sent:
                    lines.append("Folders: %s" % ", ".join(sent))
                _wait_for_button(lines)
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
            rows = [
                self._row(
                    "Default folder",
                    config["folder"],
                    lambda: self._edit_default(),
                ),
                self._row(
                    "Pack as zip",
                    "Yes" if config["zip"] else "No. Each save is its own file.",
                    lambda: self._toggle("zip"),
                ),
                self._row(
                    "Versions",
                    _keep_text(config["keep"]),
                    lambda: self._edit_versions(),
                ),
                self._row(
                    "Only if a save changed",
                    "Yes" if config["skipUnchanged"] else "No. The same save is copied again.",
                    lambda: self._toggle("skipUnchanged"),
                ),
            ]
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

    def _toggle(self, key):
        config = load_backup_config()
        config[key] = not config[key]
        save_backup_config(config)

    def _edit_versions(self):
        from display.on_screen_keyboard import OnScreenKeyboard
        from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu

        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [
                "Add a new copy every time",
                "Replace the last copy",
                "Keep the last 3",
                "Keep the last 5",
                "Keep the last 10",
                "Type a number",
            ],
            "Versions",
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
                _wait_for_button(["Type a number from 0 to 50.", "0 adds a copy every time. 1 replaces the last."])
                return
            config["keep"] = number
        else:
            config["keep"] = (0, 1, 3, 5, 10)[choice]
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
    config = {
        "folder": DEFAULT_DRIVE_FOLDER,
        "platforms": {},
        "zip": True,
        "keep": 0,
        "skipUnchanged": True,
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


def _confirm_lines(groups, config):
    folders = []
    for folder, _cores in groups:
        if folder not in folders:
            folders.append(folder)
    lines = [
        "Copy the saves to",
        ", ".join(folders),
        "As a zip." if config["zip"] else "As the save files themselves.",
        _keep_text(config["keep"]) + ".",
    ]
    if config["skipUnchanged"]:
        lines.append("Unchanged saves are skipped.")
    return lines


def _keep_text(keep):
    try:
        keep = int(keep)
    except (TypeError, ValueError):
        keep = 0
    if keep <= 0:
        return "Add a new copy every time"
    if keep == 1:
        return "Replace the last copy"
    return "Keep the last %d" % keep


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
