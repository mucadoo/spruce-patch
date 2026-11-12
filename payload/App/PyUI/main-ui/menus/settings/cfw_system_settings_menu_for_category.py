
from controller.controller_inputs import ControllerInput
from display.display import Display
from menus.games.utils import raproxy_cli
from menus.games.utils.cheevos_cache_manager import CheevosCacheManager
from menus.language.language import Language
from menus.settings import settings_menu
from menus.settings.cheevos_cache_browser import CheevosCacheBrowser, CheevosWatchMenu
from menus.settings.cheevos_cache_menu import CheevosCacheMenu
from menus.settings.pending_awards_menu import PendingAwardsMenu
from views.grid_or_list_entry import GridOrListEntry


class CfwSystemSettingsMenuForCategory(settings_menu.SettingsMenu):
    RETROACHIEVEMENTS = "RetroAchievements Settings"

    def __init__(self, category):
        self.category = category
        super().__init__()

    def launch_cheevos_cache(self, input_value):
        if ControllerInput.A == input_value:
            Display.display_message(Language.label("loadingCheevos", "Loading..."))
            CheevosCacheManager.refresh()
            CheevosCacheMenu().show_menu()

    def show_cheevos_cache(self):
        return self.category == self.RETROACHIEVEMENTS and raproxy_cli.enabled()

    def launch_pending_awards(self, input_value):
        if ControllerInput.A == input_value:
            PendingAwardsMenu().show_menu()

    def cache_for_offline(self, input_value):
        if ControllerInput.A != input_value:
            return
        CheevosCacheBrowser().show_menu()

    def watch_new_games(self, input_value):
        if ControllerInput.A != input_value:
            return
        CheevosWatchMenu().show_menu()

    def cache_recently_played(self, input_value):
        if ControllerInput.A != input_value:
            return
        message = raproxy_cli.run_smart_cache(
            Language.label("cacheRecentCheevos", "Cache recently played games"))
        if message:
            Display.display_message(message, duration_ms=2500)

    def cheevos_entry(self, text, value, value_text=None, description=None):
        return GridOrListEntry(
            primary_text=text,
            value_text=value_text,
            image_path=None,
            image_path_selected=None,
            description=description,
            icon=None,
            value=value
        )

    def build_options_list(self):
        option_list = self.build_options_list_from_config_menu_options(self.category)

        if self.show_cheevos_cache():
            option_list.append(self.cheevos_entry(
                Language.label("cacheForOffline", "Cache for offline"), self.cache_for_offline,
                description=Language.label(
                    "cacheForOfflineDesc",
                    "Pick a platform or a game. Already cached games are skipped")))
            option_list.append(self.cheevos_entry(
                Language.label("keepLibraryOffline", "Keep library offline"), self.watch_new_games,
                description=Language.label(
                    "keepLibraryOfflineDesc",
                    "Watch the whole library, or only the platforms you choose")))
            option_list.append(self.cheevos_entry(
                Language.label("cachedCheevosGames", "Cached Games"), self.launch_cheevos_cache))
            option_list.append(self.cheevos_entry(
                Language.label("pendingCheevosAwards", "Pending Awards"), self.launch_pending_awards))
            option_list.append(self.cheevos_entry(
                Language.label("cacheRecentCheevos", "Cache recently played games"), self.cache_recently_played))

        return option_list
