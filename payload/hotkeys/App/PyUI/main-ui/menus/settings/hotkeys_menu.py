from devices.device import Device
from menus.settings import settings_menu
from utils.cfw_system_config import CfwSystemConfig
from views.grid_or_list_entry import GridOrListEntry


class HotkeysMenu(settings_menu.SettingsMenu):
    """A read-only list of the chords spruce is using on this device."""

    def __init__(self):
        super().__init__()

    def do_nothing(self, input_value):
        pass

    def reload_options(self):
        return False

    def _selected(self, category, name, default):
        value = CfwSystemConfig.get_selected_value(category, name)
        if value is None or value == "":
            return default
        return value

    def _for_this_device(self, category, name):
        option = CfwSystemConfig.get_menu_option(category, name) or {}
        if not Device.supports_device(option.get("devices")):
            return None
        return option.get("selected")

    def _row(self, action, chord, where):
        return GridOrListEntry(
            primary_text=action,
            value_text=chord,
            description=where,
            value=self.do_nothing,
        )

    def _retroarch_modifier(self):
        for name in ("raHotkeyMiyoo", "raHotkeyTrimUI"):
            selected = self._for_this_device("Emulator Settings", name)
            if selected:
                return selected
        return "Select"

    def build_options_list(self):
        rows = []
        everywhere = "Works in the menu and in a game"
        in_game = "In a game"

        brightness = self._selected("Button Settings", "brightnessHotkey", "Both")
        if brightness in ("Start + L/R", "Both"):
            rows.append(self._row("Dim the screen", "Start + L", everywhere))
            rows.append(self._row("Brighten the screen", "Start + R", everywhere))
        if brightness in ("Menu + Vol", "Both"):
            rows.append(self._row("Dim the screen", "Menu + Volume down", everywhere))
            rows.append(self._row("Brighten the screen", "Menu + Volume up", everywhere))
        if brightness == "Off":
            rows.append(self._row("Screen brightness", "Off", everywhere))

        screenshot = self._selected("Button Settings", "globalScreenshotShortcut", "L2+R2+Y")
        if screenshot == "Off":
            rows.append(self._row("Screenshot", "Off", everywhere))
        else:
            rows.append(self._row("Screenshot", screenshot.replace("+", " + "), everywhere))

        rows.append(self._row("Volume", "Volume up / Volume down", everywhere))

        power_hold = self._selected("Button Settings", "powerButtonHoldTime", "1")
        rows.append(self._row("Sleep", "Tap Power", everywhere))
        rows.append(self._row("Shut down", "Hold Power for " + str(power_hold) + "s", everywhere))

        tap = self._selected("Button Settings", "tapMenuAction", "Emulator menu")
        hold = self._selected("Button Settings", "holdMenuAction", "Game Switcher")
        hold_time = self._selected("Button Settings", "menuHoldTime", "1")
        rows.append(self._row("Menu button", "Tap: " + tap, in_game))
        rows.append(self._row("Menu button", "Hold " + str(hold_time) + "s: " + hold, in_game))

        modifier = self._retroarch_modifier()
        if modifier == "Custom":
            hotkey = "Hotkey"
            retroarch = "In a game. Hotkey is the button set in RetroArch"
        else:
            hotkey = modifier
            retroarch = "In a game. Hold " + modifier + ", then press the other button"

        for action, button in (
            ("Screenshot", "A"),
            ("Exit game", "B"),
            ("Open the menu", "X"),
            ("Show FPS", "Y"),
            ("Load state", "L"),
            ("Save state", "R"),
            ("Slow motion", "L2"),
            ("Fast-forward", "R2"),
            ("Toggle shader", "Up"),
            ("Previous state slot", "Left"),
            ("Next state slot", "Right"),
        ):
            rows.append(self._row(action, hotkey + " + " + button, retroarch))

        return rows
