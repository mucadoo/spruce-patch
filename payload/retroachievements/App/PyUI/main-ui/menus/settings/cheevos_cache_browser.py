import json
import os
import tempfile
import threading

from controller.controller import Controller
from controller.controller_inputs import ControllerInput
from display.display import Display
from menus.games.utils import raproxy_cli
from menus.language.language import Language
from menus.settings.list_of_options_selection_menu import ListOfOptionsSelectionMenu
from utils.idle_shutdown import pauses_idle_shutdown
from utils.user_prompt import UserPrompt
from views.grid_or_list_entry import GridOrListEntry
from views.view_creator import ViewCreator
from views.view_type import ViewType


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

    def _cache_folder(self, path):
        estimate = raproxy_cli.run_json("estimate-cache", "--path", path, "--json") or {}
        total = int(estimate.get("candidates") or 0)
        already = int(estimate.get("already_known") or 0)
        no_match = int(estimate.get("no_match") or 0)
        remaining = int(
            estimate.get("remaining") if estimate.get("remaining") is not None else max(0, total - already - no_match))
        if total <= 0:
            Display.display_message(
                Language.label("noRomsInCheevosFolder", "No games in this folder"), duration_ms=2000)
            return
        if remaining <= 0:
            if no_match > 0 and already > 0:
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
            return
        lines = [
            Language.label(
                "cheevosFolderRemaining",
                "{remaining} games still need caching.").replace("{remaining}", str(remaining)),
        ]
        if already > 0:
            lines.append(Language.label(
                "cheevosFolderAlreadyCached",
                "{already} already cached — those are skipped.").replace("{already}", str(already)))
        if no_match > 0:
            lines.append(Language.label(
                "cheevosFolderNoAchievements",
                "{count} already checked, no RetroAchievements.",
            ).replace("{count}", str(no_match)))
        lines.append(Language.label("cheevosFolderOnline", "Caching needs WiFi."))
        lines.append(Language.label(
            "cheevosCacheNowHint",
            "The first games cache now. The rest continues in the background."))
        lines.append(Language.label("cheevosPressB", "Press B during the cache to stop."))
        if remaining > 1 and not UserPrompt.prompt_yes_no(self._label(path), lines):
            return
        self._run(["cache-folder-listing", "--path", path], total)

    def _cache_paths(self, paths, title):
        if not paths:
            return False
        if len(paths) > 1 and not UserPrompt.prompt_yes_no(title, [
                Language.label("cheevosFolderGames", "Up to {games} games to cache.").replace(
                    "{games}", str(len(paths))),
                Language.label("cheevosFolderOnline", "Caching needs WiFi."),
                Language.label("cheevosPressB", "Press B during the cache to stop."),
        ]):
            return False
        handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="ra-cache-", suffix=".txt")
        try:
            handle.write("\n".join(paths))
            handle.close()
            self._run(["cache-roms", "--paths-file", handle.name], len(paths))
        finally:
            try:
                os.remove(handle.name)
            except OSError:
                pass
        return True

    @pauses_idle_shutdown
    def _run(self, args, total):
        state = {
            "cached": 0, "failed": 0, "queued": 0, "skipped": 0, "no_match": 0,
            "current": 0, "label": "", "stopped": False,
        }
        abort_file = os.path.join(tempfile.gettempdir(), f"ra-abort-{os.getpid()}")
        try:
            os.remove(abort_file)
        except OSError:
            pass
        monitoring = {"on": True}

        def watch_stop():
            while monitoring["on"]:
                if Controller.get_input() and Controller.last_input() == ControllerInput.B:
                    state["stopped"] = True
                    monitoring["on"] = False
                    try:
                        with open(abort_file, "w", encoding="utf-8") as handle:
                            handle.write("stop")
                    except OSError:
                        pass

        threading.Thread(target=watch_stop, daemon=True).start()

        def on_line(line):
            if not line:
                return
            event = None
            try:
                event = json.loads(line)
            except ValueError:
                event = None
            if isinstance(event, dict) and event.get("type") == "progress":
                state["current"] = int(event.get("scanned") or 0)
                state["cached"] = int(event.get("cached") or 0)
                state["label"] = str(event.get("current_label") or "")
                if event.get("no_match") is not None:
                    state["no_match"] = int(event.get("no_match") or 0)
                phase = str(event.get("phase") or "caching")
                if phase == "skipping":
                    state["skipped"] += 1
                self._show_progress(phase, state["current"], int(event.get("total") or total), state)
                return
            if isinstance(event, dict) and event.get("type") == "result":
                state["cached"] = int(event.get("cached") or state["cached"])
                state["queued"] = int(event.get("queued") or 0)
                state["skipped"] = int(event.get("skipped") or state["skipped"])
                if event.get("no_match") is not None:
                    state["no_match"] = int(event.get("no_match") or 0)
                return
            parts = line.split(" ", 2)
            if parts and parts[0] in {"OK", "QUEUED", "FAIL", "NOMATCH"} and len(parts) > 1 and "/" in parts[1]:
                done, _, of = parts[1].partition("/")
                state["current"] = int(done) if done.isdigit() else state["current"]
                if parts[0] == "OK":
                    state["cached"] += 1
                    phase = "caching"
                elif parts[0] == "QUEUED":
                    state["queued"] += 1
                    phase = "caching"
                elif parts[0] == "NOMATCH":
                    state["no_match"] += 1
                    phase = "no_achievements"
                else:
                    state["failed"] += 1
                    phase = "caching"
                state["label"] = parts[2] if len(parts) > 2 else ""
                self._show_progress(phase, state["current"], int(of) if of.isdigit() else total, state)

        try:
            Display.display_message_multiline([
                Language.label("checkingCheevosFolder", "Checking games..."),
                "",
                Language.label("cheevosPressB", "Press B during the cache to stop."),
            ])
            raproxy_cli.run_streaming(args, on_line, abort_file)
        finally:
            monitoring["on"] = False
            try:
                os.remove(abort_file)
            except OSError:
                pass

        if state["stopped"]:
            stopped = Language.label("cheevosCacheStopped", "Stopped")
        else:
            stopped = Language.label("cheevosCacheFinished", "Finished")
        summary = Language.label("cachedCheevosCount", "Cached {cached}").replace(
            "{cached}", str(state["cached"]))
        if state["skipped"]:
            summary += ", " + Language.label(
                "skippedCheevosCount", "{skipped} already done").replace(
                "{skipped}", str(state["skipped"]))
        if state["no_match"]:
            summary += ", " + Language.label(
                "noAchievementsCheevosCount", "{count} have no achievements").replace(
                "{count}", str(state["no_match"]))
        if state["queued"]:
            summary += ", " + Language.label(
                "queuedCheevosCount", "{queued} queued").replace(
                "{queued}", str(state["queued"]))
            summary += ". " + Language.label(
                "cheevosCacheContinues", "The rest continues in the background.")
        Display.display_message(f"{stopped}. {summary}", duration_ms=4000)

    def _show_progress(self, phase, current, total, state):
        if phase == "skipping":
            phase_text = Language.label("cheevosPhaseSkipping", "Skipping")
        elif phase == "no_achievements":
            phase_text = Language.label("noAchievementsCheevos", "No achievements")
        elif phase == "hashing":
            phase_text = Language.label("cheevosPhaseChecking", "Checking")
        else:
            phase_text = Language.label("cheevosPhaseCaching", "Caching")
        lines = [
            f"{phase_text} {current} of {total}",
            state["label"],
            Language.label("cachedCheevosCount", "Cached {cached}").replace(
                "{cached}", str(state["cached"])),
        ]
        if state["skipped"]:
            lines.append(Language.label(
                "skippedCheevosCount", "{skipped} already done").replace(
                "{skipped}", str(state["skipped"])))
        if state["no_match"]:
            lines.append(Language.label(
                "noAchievementsCheevosCount", "{count} have no achievements").replace(
                "{count}", str(state["no_match"])))
        lines.append("")
        lines.append(Language.label("cheevosPressB", "Press B during the cache to stop."))
        Display.display_message_multiline(lines)


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
