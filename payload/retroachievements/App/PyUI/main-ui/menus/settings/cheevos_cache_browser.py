import json
import os
import tempfile
import threading
import time

from controller.controller import Controller
from controller.controller_inputs import ControllerInput
from display.display import Display
from menus.games.utils import raproxy_cli
from menus.language.language import Language
from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu
from utils.user_prompt import UserPrompt
from views.grid_or_list_entry import GridOrListEntry
from views.view_creator import ViewCreator
from views.view_type import ViewType


def show_background_cache():
    """Live count of games the service is still caching. A stops that queue.

    The status command runs on its own thread, so the screen keeps reading buttons while it
    works. Asking for the status inside the input loop dropped B presses.
    """
    state = {"status": None, "stop": False}

    def poll():
        while not state["stop"]:
            status = raproxy_cli.run_json("cache-queue-status", "--json", timeout=15)
            if status is not None:
                state["status"] = status
            for _ in range(20):
                if state["stop"]:
                    return
                time.sleep(0.1)

    def lines_for(status):
        if status is None:
            return [Language.label("loadingCheevos", "Loading..."), "",
                    Language.label("cheevosBackgroundBack", "Press B to go back.")], False
        waiting = int(status.get("waiting") or 0)
        cached = int(status.get("cached") or 0)
        label = str(status.get("label") or "")
        active = bool(status.get("active")) or waiting > 0
        lines = [
            Language.label("cheevosBackgroundWaiting", "{count} games still waiting").replace(
                "{count}", str(waiting)),
            Language.label("cheevosBackgroundCached", "{count} games cached").replace(
                "{count}", str(cached)),
        ]
        if waiting and label:
            lines.append(label)
        elif active and not waiting:
            lines.append(Language.label(
                "cheevosBackgroundScanning", "The library watch is checking games."))
        lines.append("")
        if waiting:
            lines.append(Language.label(
                "cheevosBackgroundStopHint", "A stops it. B leaves this screen. Caching continues."))
        elif active:
            lines.append(Language.label(
                "cheevosBackgroundLeave", "B leaves this screen. Caching continues."))
        else:
            lines.append(Language.label(
                "cheevosBackgroundIdle", "Nothing is caching in the background."))
            lines.append(Language.label("cheevosBackgroundBack", "Press B to go back."))
        return lines, waiting > 0

    threading.Thread(target=poll, daemon=True).start()
    Controller.hold_screensaver(True)
    shown = None
    try:
        while True:
            status = state["status"]
            lines, waiting = lines_for(status)
            if lines != shown:
                Display.display_message_multiline(lines)
                shown = lines
            if not Controller.get_input(timeout=0.3):
                continue
            pressed = Controller.last_input()
            Controller.clear_last_input()
            if pressed == ControllerInput.B:
                return
            if pressed == ControllerInput.A and waiting:
                if UserPrompt.prompt_yes_no(
                        Language.label("cheevosBackgroundStop", "Stop background cache"),
                        [Language.label(
                            "cheevosBackgroundStopConfirm",
                            "Leave the games that are still waiting. Cached games stay.")]):
                    raproxy_cli.run("clear-cache-queue", timeout=15)
                    state["status"] = raproxy_cli.run_json("cache-queue-status", "--json", timeout=15)
                shown = None
    finally:
        state["stop"] = True
        Controller.hold_screensaver(False)


def load_platforms(root):
    """Platforms that actually have games, using the same names and icons as the main menu."""
    from devices.device import Device
    from menus.games.game_system_select_menu import GameSystemSelectMenu

    platforms = []
    try:
        systems = Device.get_device().get_game_system_utils().get_active_systems()
    except Exception:
        return platforms
    for system in systems:
        if not system.folder_paths:
            continue
        path = os.path.abspath(system.folder_paths[0])
        if os.path.dirname(path) != root:
            continue
        icon, selected_icon = GameSystemSelectMenu.get_images(system)
        platforms.append({
            "name": system.display_name,
            "path": path,
            "icon": icon or selected_icon,
        })
    return platforms


class CheevosCacheBrowser:
    """Pick a platform or individual games and cache them, with a live count."""

    def __init__(self):
        from devices.device import Device
        self.root = os.path.abspath(Device.get_device().get_roms_dir())
        self.current = self.root
        self.selected = {}
        self._labels = {}
        self.platforms = load_platforms(self.root)
        for platform in self.platforms:
            self._labels[platform["path"]] = platform["name"]
        raproxy_cli.reload_watched()

    def show_menu(self):
        selected_index = 0
        view = None
        shown_path = None
        while True:
            path_now = os.path.abspath(self.current)
            if view is None or shown_path != path_now:
                if shown_path != path_now and path_now != self.root:
                    Display.display_message(Language.label("loadingCheevos", "Loading..."))
                options = self._options()
                if selected_index >= len(options):
                    selected_index = 0
                view = ViewCreator.create_view(
                    view_type=ViewType.ICON_AND_DESC,
                    top_bar_text=self._title(),
                    options=options,
                    selected_index=selected_index,
                )
                shown_path = path_now
                Controller.clear_last_input()
            selected = view.get_selection([
                ControllerInput.A, ControllerInput.B,
                ControllerInput.DPAD_LEFT, ControllerInput.DPAD_RIGHT,
            ])
            if selected is None or selected.get_input() is None:
                continue
            if selected.get_input() == ControllerInput.B:
                if path_now == self.root:
                    return
                self.current = os.path.dirname(self.current)
                selected_index = 0
                view = None
                continue
            selected_index = selected.get_index()
            if selected.get_input() == ControllerInput.A:
                before = os.path.abspath(self.current)
                selected.get_selection().get_value()()
                if os.path.abspath(self.current) != before:
                    selected_index = 0
                view = None

    def _title(self):
        if os.path.abspath(self.current) == self.root:
            return Language.label("cacheForOffline", "Cache for offline")
        return self._label(self.current)

    def _label(self, path):
        cached = self._labels.get(path)
        if cached:
            return cached
        name = os.path.basename(path.rstrip("/")) or path
        label = name
        if os.path.dirname(os.path.abspath(path)) == self.root:
            cfg = os.path.join(os.path.dirname(self.root), "Emu", name, "config.json")
            try:
                with open(cfg, encoding="utf-8") as handle:
                    found = json.load(handle).get("label")
                if isinstance(found, str) and found.strip():
                    label = found.strip()
            except (OSError, ValueError):
                pass
        self._labels[path] = label
        return label

    def _options(self):
        options = []
        at_root = os.path.abspath(self.current) == self.root
        if at_root:
            options.append(self._row(
                Language.label("cheevosWholeLibrary", "Whole library"),
                Language.label(
                    "cheevosCacheWholeLibrary", "Cache every game that is not cached yet"),
                lambda: self._cache_folder(self.root),
            ))
            for platform in self.platforms:
                options.append(self._row(
                    platform["name"],
                    Language.label(
                        "cheevosPlatformHint", "Open it, or cache every game on this platform"),
                    lambda path=platform["path"]: self._platform_menu(path),
                    icon=platform["icon"],
                ))
            if self.selected:
                options.insert(1, self._row(
                    Language.label("cacheSelectedCheevos", "Cache selected ({count})").replace(
                        "{count}", str(len(self.selected))),
                    Language.label("cacheSelectedCheevosDesc", "Cache the games you picked"),
                    self._cache_selected,
                    "Selected",
                ))
            if len(options) == 1:
                options.append(self._row(
                    Language.label("emptyCheevosFolder", "Nothing to cache here"),
                    None,
                    lambda: None,
                ))
            return options
        if self.selected:
            options.append(self._row(
                Language.label("cacheSelectedCheevos", "Cache selected ({count})").replace(
                    "{count}", str(len(self.selected))),
                Language.label("cacheSelectedCheevosDesc", "Cache the games you picked"),
                self._cache_selected,
                "Selected",
            ))
        entries = raproxy_cli.list_folder(self.current)
        if not entries and not options:
            options.append(self._row(
                Language.label("emptyCheevosFolder", "Nothing to cache here"),
                None,
                lambda: None,
            ))
            return options
        for entry in entries:
            path = entry["path"]
            if entry["is_dir"]:
                options.append(self._row(
                    self._label(path),
                    Language.label("cheevosFolderHint", "Open it, or cache every game inside"),
                    lambda path=path: self._folder_menu(path),
                ))
            else:
                picked = path in self.selected
                if picked:
                    badge = "Selected"
                elif entry.get("cached"):
                    badge = Language.label("cachedCheevosBadge", "Cached")
                elif entry.get("no_achievements"):
                    badge = Language.label("noAchievementsCheevos", "No achievements")
                else:
                    badge = None
                options.append(self._row(
                    entry["name"],
                    Language.label("cheevosRomHint", "Select it for a batch, or cache it now"),
                    lambda path=path, name=entry["name"]: self._rom_menu(path, name),
                    badge,
                ))
        return options

    def _row(self, text, description, action, value_text=None, icon=None):
        return GridOrListEntry(
            primary_text=text,
            value_text=value_text,
            image_path=icon,
            image_path_selected=icon,
            description=description,
            icon=icon,
            value=action,
        )

    def _platform_menu(self, path):
        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [
                Language.label("openCheevosPlatform", "Open"),
                Language.label("cacheCheevosPlatform", "Cache this platform"),
            ],
            self._label(path),
        )
        if choice == 0:
            self.current = path
        elif choice == 1:
            self._cache_folder(path)

    def _folder_menu(self, path):
        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [
                Language.label("openCheevosFolder", "Open"),
                Language.label("cacheCheevosFolder", "Cache this folder"),
            ],
            self._label(path),
        )
        if choice == 0:
            self.current = path
        elif choice == 1:
            self._cache_folder(path)

    def _rom_menu(self, path, name):
        select_label = (
            Language.label("unselectCheevosRom", "Unselect")
            if path in self.selected
            else Language.label("selectCheevosRom", "Select for batch")
        )
        choice = ListOfOptionsSelectionMenu().get_selected_option_index(
            [select_label, Language.label("cacheThisCheevosRom", "Cache this game")],
            name,
        )
        if choice == 0:
            if path in self.selected:
                self.selected.pop(path, None)
            else:
                self.selected[path] = name
        elif choice == 1:
            self._cache_paths([path], name)

    def _cache_selected(self):
        paths = list(self.selected)
        if self._cache_paths(paths, Language.label("cacheSelectedCheevosTitle", "Selected games")):
            self.selected.clear()

    def _yield_to_running_cache(self, add_games):
        """A second on-screen cache fights the one already running. Offer to watch it or add to it."""
        status = raproxy_cli.run_json("cache-queue-status", "--json", timeout=15) or {}
        waiting = int(status.get("waiting") or 0)
        active = bool(status.get("active")) or waiting > 0
        if not active:
            return False
        if waiting > 0:
            title = Language.label(
                "cheevosBackgroundBusy",
                "A cache is already running. {count} games are still waiting.",
            ).replace("{count}", str(waiting))
        else:
            title = Language.label(
                "cheevosBackgroundBusyScan",
                "The library watch is already checking games.",
            )
        choice = ListOfOptionsSelectionMenu().get_selected_option_index([
            Language.label("cheevosBackgroundSee", "See the cache that's running"),
            Language.label("cheevosBackgroundAdd", "Add these games to it"),
        ], title)
        if choice == 0:
            show_background_cache()
        elif choice == 1:
            add_games()
        return True

    def _cache_folder(self, path):
        estimate = raproxy_cli.run_json("estimate-cache", "--path", path, "--json") or {}
        total = int(estimate.get("candidates") or 0)
        already = int(estimate.get("already_known") or 0)
        no_match = int(estimate.get("no_match") or 0)
        queued = int(estimate.get("queued") or 0)
        remaining = int(
            estimate.get("remaining") if estimate.get("remaining") is not None else max(0, total - already - no_match - queued))
        if total <= 0:
            Display.display_message(
                Language.label("noRomsInCheevosFolder", "No games in this folder"), duration_ms=2000)
            return
        if remaining <= 0:
            if queued > 0:
                message = Language.label(
                    "cheevosBackgroundStill",
                    "{cached} cached. {queued} still caching in the background.",
                ).replace("{cached}", str(already)).replace("{queued}", str(queued))
            elif no_match > 0 and already > 0:
                message = Language.label(
                    "cheevosCheckedSummary",
                    "All checked. {already} cached, {count} have no achievements.",
                ).replace("{already}", str(already)).replace("{count}", str(no_match))
            elif no_match > 0:
                message = Language.label(
                    "cheevosNoAchievementsOnly",
                    "Already checked. These games have no RetroAchievements.",
                )
            else:
                message = Language.label("cheevosLibraryUpToDate", "All games already cached")
            Display.display_message(message, duration_ms=2500)
            if queued > 0:
                show_background_cache()
            return
        if self._yield_to_running_cache(
                lambda: self._start_in_background(["cache-folder-listing", "--path", path, "--background"])):
            return
        title = Language.label(
            "cheevosFolderRemaining",
            "{remaining} games still need caching.",
        ).replace("{remaining}", str(remaining))
        if not UserPrompt.prompt_yes_no(self._label(path), [
                title,
                Language.label(
                    "cheevosCacheLeaves",
                    "You can leave the next screen. Caching continues."),
        ]):
            return
        self._start_in_background(["cache-folder-listing", "--path", path, "--background"])

    def _start_in_background(self, args, cleanup=None):
        """Start the cache and show its progress. Leaving the screen does not stop the job."""
        def work():
            try:
                raproxy_cli.run(*args, timeout=None)
            finally:
                if cleanup is not None:
                    cleanup()

        threading.Thread(target=work, daemon=True).start()
        show_background_cache()

    def _queue_paths(self, paths):
        handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="ra-cache-", suffix=".txt")
        handle.write("\n".join(paths))
        handle.close()

        def cleanup():
            try:
                os.remove(handle.name)
            except OSError:
                pass

        self._start_in_background(
            ["cache-roms", "--paths-file", handle.name, "--background"],
            cleanup,
        )

    def _cache_paths(self, paths, title):
        if not paths:
            return False
        if self._yield_to_running_cache(lambda: self._queue_paths(paths)):
            return False
        if len(paths) > 1 and not UserPrompt.prompt_yes_no(title, [
                Language.label("cheevosFolderGames", "Up to {games} games to cache.").replace(
                    "{games}", str(len(paths))),
                Language.label(
                    "cheevosCacheLeaves",
                    "You can leave the next screen. Caching continues."),
        ]):
            return False
        self._queue_paths(paths)
        return True

class CheevosWatchMenu:
    """Choose the whole library or individual platforms to cache when new games are added."""

    def __init__(self):
        from devices.device import Device
        self.root = os.path.abspath(Device.get_device().get_roms_dir())
        self.platforms = load_platforms(self.root)
        raproxy_cli.reload_watched()

    def show_menu(self):
        selected_index = 0
        while True:
            options = self._options()
            if selected_index >= len(options):
                selected_index = 0
            view = ViewCreator.create_view(
                view_type=ViewType.ICON_AND_DESC,
                top_bar_text=Language.label("keepLibraryOffline", "Keep library offline"),
                options=options,
                selected_index=selected_index,
            )
            selected = view.get_selection([
                ControllerInput.A, ControllerInput.B,
                ControllerInput.DPAD_LEFT, ControllerInput.DPAD_RIGHT,
            ])
            if selected is None or selected.get_input() == ControllerInput.B:
                return
            selected_index = selected.get_index()
            if selected.get_input() in (
                ControllerInput.A, ControllerInput.DPAD_LEFT, ControllerInput.DPAD_RIGHT,
            ):
                selected.get_selection().get_value()()

    def _options(self):
        options = [self._row(
            Language.label("cheevosWholeLibrary", "Whole library"),
            Language.label(
                "cheevosWatchWholeLibrary", "New games on every platform are cached later"),
            self._toggle_library,
            self._flag(raproxy_cli.is_watched(self.root)),
        )]
        library_on = raproxy_cli.is_watched(self.root)
        for platform in self.platforms:
            watched = library_on or raproxy_cli.is_watched(platform["path"])
            options.append(self._row(
                platform["name"],
                Language.label(
                    "cheevosWatchPlatform", "New games on this platform are cached later"),
                lambda path=platform["path"]: self._toggle_platform(path),
                self._flag(watched),
                platform["icon"],
            ))
        return options

    def _flag(self, on):
        return "<    " + Language.menu_option_value("True" if on else "False") + "    >"

    def _row(self, text, description, action, value_text=None, icon=None):
        return GridOrListEntry(
            primary_text=text,
            value_text=value_text,
            image_path=icon,
            image_path_selected=icon,
            description=description,
            icon=icon,
            value=action,
        )

    def _toggle_library(self):
        if raproxy_cli.is_watched(self.root):
            raproxy_cli.unwatch_folder(self.root)
            return
        Display.display_message(Language.label("savingCheevosWatch", "Saving..."))
        for platform in self.platforms:
            if raproxy_cli.is_watched(platform["path"]):
                raproxy_cli.unwatch_folder(platform["path"])
        if not raproxy_cli.watch_folder(
                self.root, Language.label("cheevosWholeLibrary", "Whole library"), confirm=False):
            Display.display_message(
                Language.label("cheevosWatchFailed", "Could not watch the library"),
                duration_ms=2000)

    def _toggle_platform(self, path):
        if raproxy_cli.is_watched(self.root):
            Display.display_message(Language.label("savingCheevosWatch", "Saving..."))
            raproxy_cli.unwatch_folder(self.root)
            for platform in self.platforms:
                if os.path.abspath(platform["path"]) == os.path.abspath(path):
                    continue
                if not raproxy_cli.watch_folder(platform["path"], platform["name"], confirm=False):
                    Display.display_message(
                        Language.label("cheevosWatchFailed", "Could not watch the library"),
                        duration_ms=2000)
                    return
            return
        if raproxy_cli.is_watched(path):
            raproxy_cli.unwatch_folder(path)
            return
        name = next(
            (platform["name"] for platform in self.platforms if platform["path"] == path), path)
        if not raproxy_cli.watch_folder(path, name, confirm=False):
            Display.display_message(
                Language.label("cheevosWatchFailed", "Could not watch the library"),
                duration_ms=2000)
